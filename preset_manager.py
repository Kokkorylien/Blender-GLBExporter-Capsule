
"""
Capsule - stored export preset management.

This module adds two things that the original add-on was missing:

1. **Portable preset files** - Stored Export Presets can be written to and read
   from a plain JSON file, so they can be versioned, shared and inspected
   outside of Blender (``userpref.blend`` was previously the only home for
   them, which made the settings all but invisible).

2. **Readable previews** - A generic, RNA driven description of a preset that
   lists what it actually changes.  The preview walks ``bl_rna.properties``, so
   it automatically covers every file format and every option without a second
   implementation that could drift out of sync.

The file format is intentionally simple and forgiving::

    {
      "capsule_presets": {
        "schema": 1,
        "presets": [
          {
            "name": "NekoMdl_Shape",
            "format_type": "GLTF",
            "settings": {...general preset options...},
            "format_settings": {...options of the chosen file format...}
          }
        ]
      }
    }

Unknown or invalid keys are skipped on import instead of failing the whole
file, and a bare list of preset dictionaries is accepted as well.
"""

import json
import os
import random

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper, ImportHelper

from .i18n import tr

SCHEMA_VERSION = 1

# Properties that are internal bookkeeping and never worth serialising.
_SKIP_PROPERTIES = {"rna_type", "instance_id"}

# Maps a preset's ``format_type`` to the property that holds its settings.
_FORMAT_DATA_ATTRIBUTE = {
    "Alembic": "data_abc",
    "Collada": "data_dae",
    "FBX": "data_fbx",
    "GLTF": "data_gltf",
    "OBJ": "data_obj",
    "STL": "data_stl",
    "USD": "data_usd",
}


# -----------------------------------------------------------------------------
# access helpers
# -----------------------------------------------------------------------------

def stored_presets(context=None):
    """Returns the Stored Export Presets collection, or ``None``."""
    context = context or bpy.context
    try:
        preferences = context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError, RuntimeError):
        return None
    if preferences is None:
        return None
    return preferences.saved_export_presets


def stored_preset_index(context=None):
    """Returns the index of the selected Stored Export Preset."""
    context = context or bpy.context
    try:
        preferences = context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError, RuntimeError):
        return -1
    if preferences is None:
        return -1
    return preferences.saved_export_presets_index


def selected_stored_preset(context=None):
    """Returns the selected Stored Export Preset, or ``None``."""
    presets = stored_presets(context)
    if not presets or len(presets) == 0:
        return None
    index = stored_preset_index(context)
    if index < 0 or index >= len(presets):
        return None
    return presets[index]


def preferences_file_path():
    """Returns the path of ``userpref.blend``, where presets are persisted."""
    try:
        return bpy.utils.user_resource('CONFIG', path="userpref.blend")
    except (AttributeError, RuntimeError, TypeError):
        return ""


# -----------------------------------------------------------------------------
# generic RNA serialisation
# -----------------------------------------------------------------------------

def _exposed_properties(owner):
    """Yields the RNA properties of ``owner`` that can be stored in a file."""
    try:
        properties = owner.bl_rna.properties
    except AttributeError:
        return

    for prop in properties:
        if prop.identifier in _SKIP_PROPERTIES:
            continue
        if prop.type in {"POINTER", "COLLECTION"}:
            continue
        yield prop


def _dump_properties(owner):
    """Stores every readable property of ``owner`` in a plain dictionary."""
    data = {}
    for prop in _exposed_properties(owner):
        if prop.is_readonly:
            continue
        try:
            value = getattr(owner, prop.identifier)
        except (AttributeError, TypeError, RuntimeError):
            continue

        if prop.type == "ENUM":
            data[prop.identifier] = str(value)
        elif prop.type == "STRING":
            data[prop.identifier] = str(value)
        elif prop.type in {"BOOLEAN", "INT", "FLOAT"}:
            data[prop.identifier] = value
    return data


def preset_to_dict(preset):
    """Converts a single ``CAPSULE_ExportPreset`` into a JSON friendly dict."""
    entry = {
        "name": preset.name,
        "format_type": preset.format_type,
        "settings": _dump_properties(preset),
        "format_settings": {},
    }

    attribute = _FORMAT_DATA_ATTRIBUTE.get(preset.format_type)
    if attribute:
        entry["format_settings"] = _dump_properties(getattr(preset, attribute))

    return entry


def _coerce_property(owner, identifier, value):
    """Assigns ``value`` to ``owner.identifier`` when it is a valid value."""
    try:
        prop = owner.bl_rna.properties[identifier]
    except (KeyError, AttributeError, TypeError, RuntimeError):
        return False

    if prop is None or prop.is_readonly:
        return False
    if prop.type in {"POINTER", "COLLECTION"}:
        return False

    try:
        if prop.type == "ENUM":
            if not isinstance(value, str):
                return False
            identifiers = [item.identifier for item in prop.enum_items]
            if value not in identifiers:
                return False
            setattr(owner, identifier, value)

        elif prop.type == "BOOLEAN":
            if not isinstance(value, bool):
                return False
            setattr(owner, identifier, value)

        elif prop.type == "INT":
            setattr(owner, identifier, int(value))

        elif prop.type == "FLOAT":
            setattr(owner, identifier, float(value))

        elif prop.type == "STRING":
            if not isinstance(value, str):
                return False
            setattr(owner, identifier, value)

        else:
            return False

    except (TypeError, ValueError, AttributeError, RuntimeError):
        return False

    return True


def _apply_settings(owner, settings):
    applied = 0
    if not isinstance(settings, dict):
        return applied
    for identifier, value in settings.items():
        if not isinstance(identifier, str):
            continue
        if _coerce_property(owner, identifier, value):
            applied += 1
    return applied


def apply_preset_dict(preset, entry):
    """Applies a dictionary created by :func:`preset_to_dict` to a preset."""
    if not isinstance(entry, dict):
        return 0

    applied = _apply_settings(preset, entry.get("settings"))

    format_type = entry.get("format_type")
    if isinstance(format_type, str):
        _coerce_property(preset, "format_type", format_type)

    attribute = _FORMAT_DATA_ATTRIBUTE.get(preset.format_type)
    if attribute:
        applied += _apply_settings(getattr(preset, attribute), entry.get("format_settings"))

    return applied


def import_presets(presets, entries):
    """Appends the given entries to a preset collection.  Returns the count."""
    if presets is None:
        return 0

    imported = 0
    existing_names = {preset.name for preset in presets}

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        preset = presets.add()
        apply_preset_dict(preset, entry)

        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            name = preset.name or tr("Imported Preset")
        preset.name = _unique_name(existing_names, name.strip())
        existing_names.add(preset.name)

        preset.instance_id = random.randrange(1, 1000000)
        imported += 1

    return imported


def _unique_name(existing_names, wanted):
    if wanted not in existing_names:
        return wanted

    index = 2
    while "{} ({})".format(wanted, index) in existing_names:
        index += 1
    return "{} ({})".format(wanted, index)


# -----------------------------------------------------------------------------
# file format
# -----------------------------------------------------------------------------

def build_payload(presets):
    """Builds the JSON structure written by the export operator."""
    return {
        "capsule_presets": {
            "schema": SCHEMA_VERSION,
            "generator": "Capsule",
            "blender_version": bpy.app.version_string,
            "presets": [preset_to_dict(preset) for preset in presets],
        }
    }


def extract_entries(payload):
    """Pulls a list of preset dictionaries out of a parsed JSON payload."""
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]

    if isinstance(payload, dict):
        block = payload.get("capsule_presets")
        if isinstance(block, dict) and isinstance(block.get("presets"), list):
            return [entry for entry in block["presets"] if isinstance(entry, dict)]

        if isinstance(payload.get("presets"), list):
            return [entry for entry in payload["presets"] if isinstance(entry, dict)]

    return []


def read_preset_file(filepath):
    """Reads a preset file and returns the list of preset dictionaries."""
    with open(filepath, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return extract_entries(payload)


def write_preset_file(filepath, presets):
    """Writes the given presets to a JSON file."""
    directory = os.path.dirname(filepath)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(build_payload(presets), handle, indent=2, ensure_ascii=False)
        handle.write("\n")


# -----------------------------------------------------------------------------
# preview
# -----------------------------------------------------------------------------

def _enum_label(prop, identifier):
    try:
        for item in prop.enum_items:
            if item.identifier == identifier:
                return item.name
    except (TypeError, AttributeError, RuntimeError):
        pass
    return identifier


def _default_value(prop):
    try:
        default = prop.default
    except (AttributeError, RuntimeError):
        return None

    if prop.type == "ENUM":
        if isinstance(default, int):
            try:
                return prop.enum_items[default].identifier
            except (TypeError, IndexError, AttributeError):
                return None
        return default

    return default


def _format_value(prop, value):
    if prop.type == "BOOLEAN":
        return tr("On") if value else tr("Off")

    if prop.type == "ENUM":
        return _enum_label(prop, value)

    if prop.type == "STRING":
        return value if value else tr("(empty)")

    if prop.type == "FLOAT":
        text = "{:.4f}".format(float(value)).rstrip("0").rstrip(".")
        return text or "0"

    return str(value)


def _changed_rows(owner, include_defaults, skip=()):
    rows = []
    for prop in _exposed_properties(owner):
        if prop.identifier in skip:
            continue

        try:
            value = getattr(owner, prop.identifier)
        except (AttributeError, TypeError, RuntimeError):
            continue

        if not include_defaults:
            default = _default_value(prop)
            if prop.type == "FLOAT" and isinstance(default, float):
                if abs(float(value) - default) < 1e-6:
                    continue
            elif value == default:
                continue

        label = prop.name or prop.identifier
        rows.append((label, _format_value(prop, value)))

    return rows


def describe_preset(preset, include_defaults=False):
    """Returns ``[(section title, [(option label, value text), ...]), ...]``."""
    if preset is None:
        return []

    sections = []

    general = _changed_rows(preset, include_defaults, skip=("name", "format_type"))
    if general:
        sections.append((tr("General Options"), general))

    attribute = _FORMAT_DATA_ATTRIBUTE.get(preset.format_type)
    if attribute:
        rows = _changed_rows(getattr(preset, attribute), include_defaults)
        if rows:
            sections.append((tr("Format Settings ({format})", format=preset.format_type), rows))

    return sections


def draw_preset_details(layout, preset, include_defaults=False, show_header=True):
    """Draws a read-only preview of a preset."""
    column = layout.column(align=True)

    if preset is None:
        column.label(text=tr("No export preset selected."), icon="INFO")
        return

    if show_header:
        header = column.box()
        title = header.row(align=True)
        title.label(text=preset.name or tr("Untitled Preset"), icon="PRESET")
        meta = header.row(align=True)
        meta.label(text=tr("File Format: {format}", format=preset.format_type), icon="FILE")
        if preset.description:
            description = header.row(align=True)
            description.label(text=preset.description, icon="TEXT")

    sections = describe_preset(preset, include_defaults)
    if not sections:
        column.label(
            text=tr("This preset does not override any default settings."),
            icon="INFO",
        )
        return

    for section_title, rows in sections:
        column.separator()
        column.label(text=section_title, icon="DOT")
        for label, value in rows:
            split = column.split(factor=0.55, align=True)
            split.label(text=label)
            split.label(text=value)


# -----------------------------------------------------------------------------
# operators
# -----------------------------------------------------------------------------

class CAPSULE_OT_Import_Stored_Presets(Operator, ImportHelper):
    """Load stored export presets from a JSON file"""

    bl_idname = "cap.import_stored_presets"
    bl_label = "Import Presets"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    mode: EnumProperty(
        name="Import Mode",
        description="Choose whether the imported presets are added to the current list or replace it",
        items=(
            ('APPEND', "Append", "Keep the existing stored presets and add the imported ones"),
            ('REPLACE', "Replace", "Delete all existing stored presets before importing"),
        ),
        default='APPEND',
    )

    def execute(self, context):
        presets = stored_presets(context)
        if presets is None:
            self.report({'ERROR'}, tr("Capsule preferences are not available."))
            return {'CANCELLED'}

        if not self.filepath or not os.path.exists(self.filepath):
            self.report({'ERROR'}, tr("File not found: {path}", path=self.filepath))
            return {'CANCELLED'}

        try:
            entries = read_preset_file(self.filepath)
        except (OSError, ValueError) as error:
            self.report({'ERROR'}, tr("Could not read preset file: {error}", error=error))
            return {'CANCELLED'}

        if not entries:
            self.report({'WARNING'}, tr("No export presets were found in this file."))
            return {'CANCELLED'}

        if self.mode == 'REPLACE':
            presets.clear()

        count = import_presets(presets, entries)
        self.report({'INFO'}, tr("Imported {count} export presets.", count=count))
        return {'FINISHED'}


class CAPSULE_OT_Export_Stored_Presets(Operator, ExportHelper):
    """Save stored export presets to a JSON file"""

    bl_idname = "cap.export_stored_presets"
    bl_label = "Export Presets"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    scope: EnumProperty(
        name="Presets to Export",
        description="Choose which stored export presets are written to the file",
        items=(
            ('ALL', "All Presets", "Export every stored export preset"),
            ('SELECTED', "Selected Preset", "Export only the currently selected stored export preset"),
        ),
        default='ALL',
    )

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = os.path.join(os.path.expanduser("~"), "capsule_export_presets.json")
        return super().invoke(context, event)

    def execute(self, context):
        presets = stored_presets(context)

        if presets is None or len(presets) == 0:
            self.report({'WARNING'}, tr("There are no stored export presets to export."))
            return {'CANCELLED'}

        if self.scope == 'SELECTED':
            preset = selected_stored_preset(context)
            if preset is None:
                self.report({'WARNING'}, tr("Select a stored export preset first."))
                return {'CANCELLED'}
            presets = [preset]

        try:
            write_preset_file(self.filepath, presets)
        except (OSError, ValueError) as error:
            self.report({'ERROR'}, tr("Could not write preset file: {error}", error=error))
            return {'CANCELLED'}

        self.report({'INFO'}, tr("Exported {count} export presets.", count=len(presets)))
        return {'FINISHED'}


class CAPSULE_OT_Preview_Stored_Preset(Operator):
    """Show every setting of the selected stored export preset"""

    bl_idname = "cap.preview_stored_preset"
    bl_label = "Preview Preset Settings"

    # A full format can expose dozens of options, which does not fit into a
    # popup.  Only the settings that differ from the defaults are shown first.
    show_all: BoolProperty(
        name="Show All Settings",
        description="Show every option instead of only the ones that differ from the defaults",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return selected_stored_preset(context) is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=520)

    def draw(self, context):
        layout = self.layout

        preset = selected_stored_preset(context)
        if preset is None:
            layout.label(text=tr("No export preset selected."), icon="INFO")
            return

        header = layout.row(align=True)
        header.label(text=preset.name or tr("Untitled Preset"), icon="PRESET")
        header.prop(self, "show_all", text=tr("Show All Settings"), toggle=True)

        draw_preset_details(layout, preset, include_defaults=self.show_all, show_header=False)


class CAPSULE_OT_Export_Preset_Details_To_Console(Operator):
    """Print every setting of the selected stored export preset to the console"""

    bl_idname = "cap.print_stored_preset"
    bl_label = "Print Preset Settings"

    @classmethod
    def poll(cls, context):
        return selected_stored_preset(context) is not None

    def execute(self, context):
        preset = selected_stored_preset(context)
        if preset is None:
            return {'CANCELLED'}

        print("Capsule preset:", preset.name, "({})".format(preset.format_type))
        for section_title, rows in describe_preset(preset, include_defaults=True):
            print("  [{}]".format(section_title))
            for label, value in rows:
                print("    {}: {}".format(label, value))

        self.report({'INFO'}, tr("Preset settings were printed to the system console."))
        return {'FINISHED'}
