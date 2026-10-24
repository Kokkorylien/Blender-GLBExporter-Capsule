
"""
Capsule - translation layer.

Capsule ships a small translation system of its own instead of relying on
Blender's built-in, dictionary based UI translation.  The built-in translation
is what turns short English words into mechanical translations (for example the
add-on name "Capsule" becoming "胶囊") and leaves the interface as an awkward
mixture of languages.

How it works
------------
* Every user facing string is written in English and passed through ``tr()``.
* ``tr()`` looks the string up in ``translations/<language>.json`` and returns
  the translated text.
* If there is no translation file for the active language, or the file has no
  entry for that string, the original English text is returned.  A zero width
  space is appended in that case so Blender's built-in translation dictionary
  does not mechanically translate the English text afterwards.
* Property names, descriptions and enum labels are declared with ``bpy.props``.
  They are translated in bulk by ``localize_classes()`` right before the
  classes are registered, so no per-property boilerplate is needed.

Language selection
------------------
The active language is taken from ``CAP_AddonPreferences.ui_language``:
``AUTO`` follows Blender's own UI language, while an explicit language code
forces that language.  Explicit choices are also cached in the Blender user
configuration folder, because add-on preferences are not readable yet at the
moment the add-on is registered (i.e. before its preference class exists).
"""

import json
import os

import bpy

ENGLISH = "en_US"
AUTO = "AUTO"

# Appended to strings that must stay exactly as written.  Lookups in Blender's
# built-in translation dictionary are exact comparisons, so the string no
# longer matches and the text is drawn as-is.  The character has zero width.
NO_TRANSLATE_MARK = "\u200b"

LANGUAGE_ITEMS = (
    (AUTO, "Auto (Blender Language)", "Follow the language that is set in Blender's preferences"),
    (ENGLISH, "English", "Always display Capsule in English"),
    ("zh_HANS", "简体中文", "Always display Capsule in Simplified Chinese"),
)

_LANGUAGE_CODES = {item[0] for item in LANGUAGE_ITEMS}

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_TRANSLATIONS_DIR = os.path.join(_PACKAGE_DIR, "translations")
_LANGUAGE_CACHE_FILE = "capsule_ui_language.txt"

# language code -> {english source string: translated string}
_translation_cache = {}
_load_errors = {}
_override_cache = None
_override_cache_loaded = False


# -----------------------------------------------------------------------------
# language resolution
# -----------------------------------------------------------------------------

def translations_directory():
    """Returns the folder that holds the translation files."""
    return _TRANSLATIONS_DIR


def normalize_language(language):
    """Maps a Blender language code to one of the codes Capsule understands."""
    if not language:
        return ENGLISH

    language = str(language).strip()
    if not language or language.upper() in {"DEFAULT", "AUTO"}:
        return ENGLISH

    language = language.replace("-", "_")
    if language.lower().startswith("zh"):
        # Capsule only ships Simplified Chinese for now.  Any other Chinese
        # variant falls back to English rather than showing the wrong script.
        if language.lower() in {"zh_hans", "zh_cn", "zh_sg"}:
            return "zh_HANS"
        return language
    if language.lower() in {"en_us", "en_gb", "en"}:
        return ENGLISH
    return language


def blender_language():
    """Returns the language currently selected in Blender's preferences."""
    try:
        language = bpy.context.preferences.view.language
    except (AttributeError, RuntimeError):
        return ENGLISH
    return normalize_language(language)


def _configuration_directory():
    try:
        return bpy.utils.user_resource('CONFIG', create=True)
    except (AttributeError, RuntimeError, TypeError):
        return None


def _language_cache_path():
    directory = _configuration_directory()
    if not directory:
        return None
    return os.path.join(directory, _LANGUAGE_CACHE_FILE)


def read_language_override():
    """Reads the cached explicit language choice (survives restarts)."""
    global _override_cache, _override_cache_loaded

    if _override_cache_loaded:
        return _override_cache
    _override_cache_loaded = True
    _override_cache = None

    path = _language_cache_path()
    if not path or not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = handle.read().strip()
    except OSError:
        return None

    if value in _LANGUAGE_CODES:
        _override_cache = value
    return _override_cache


def write_language_override(language):
    """Caches an explicit language choice so it applies on the next start."""
    global _override_cache, _override_cache_loaded

    language = language or AUTO
    _override_cache = language
    _override_cache_loaded = True

    path = _language_cache_path()
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(language)
    except OSError:
        pass


def _preference_language():
    """Returns the language set in the add-on preferences, if it is readable.

    The preference class does not exist before the add-on is registered, which
    is exactly when :func:`localize_classes` runs, so this can legitimately
    return ``None``.
    """
    try:
        preferences = bpy.context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError, RuntimeError):
        return None
    if preferences is None:
        return None
    try:
        return preferences.ui_language
    except (AttributeError, RuntimeError):
        return None


def get_language():
    """Returns the language code Capsule should currently display."""
    preference = _preference_language()

    if preference is None:
        cached = read_language_override()
        if cached and cached != AUTO:
            return normalize_language(cached)
        return blender_language()

    preference = normalize_language(preference) if preference != AUTO else AUTO
    if preference == AUTO:
        return blender_language()
    return preference


def cache_language_preference(self, context):
    """``update`` callback used by the ``ui_language`` add-on preference."""
    write_language_override(getattr(self, "ui_language", AUTO))


# -----------------------------------------------------------------------------
# translation tables
# -----------------------------------------------------------------------------

def translation_file(language):
    """Returns the path of the translation file for a language code."""
    return os.path.join(_TRANSLATIONS_DIR, language + ".json")


def has_translation_file(language):
    return language == ENGLISH or os.path.exists(translation_file(language))


def load_translations(language):
    """Loads (and caches) the translation table of a language."""
    if language in _translation_cache:
        return _translation_cache[language]

    table = {}
    if language and language != ENGLISH:
        path = translation_file(language)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    raw = json.load(handle)
                if isinstance(raw, dict):
                    for key, value in raw.items():
                        if isinstance(key, str) and isinstance(value, str) and key and value:
                            table[key] = value
            except (OSError, ValueError) as error:
                _load_errors[language] = str(error)

    _translation_cache[language] = table
    return table


def load_error(language):
    """Returns the error raised while loading a translation file, if any."""
    load_translations(language)
    return _load_errors.get(language)


def reload_translations():
    """Clears the translation cache so files can be edited while Blender runs."""
    _translation_cache.clear()
    _load_errors.clear()


def tr(text, **values):
    """Translates a single string to the active language.

    ``values`` are applied with ``str.format`` after translation, so both the
    English source string and its translation may contain placeholders such as
    ``{count}``.
    """
    if not text:
        return text

    language = get_language()
    if language == ENGLISH:
        result = text
        # When English is forced while Blender itself runs in another
        # language, mark the text as well so Blender's own dictionary does not
        # translate it back into the interface language.
        if blender_language() != ENGLISH and not text.endswith(NO_TRANSLATE_MARK):
            result = text + NO_TRANSLATE_MARK
    else:
        result = load_translations(language).get(text)
        # A translation that is identical to the English source (brand names
        # such as "Capsule") still has to be marked, otherwise Blender's
        # built-in dictionary would translate it mechanically.
        if not result or result == text:
            if text.endswith(NO_TRANSLATE_MARK):
                result = text
            else:
                result = text + NO_TRANSLATE_MARK

    if values:
        try:
            result = result.format(**values)
        except (KeyError, IndexError, ValueError):
            pass
    return result


def tr_with(prefix, count):
    """Convenience helper for pluralised counts (English form fallback)."""
    return tr(prefix) + " " + str(count)


# -----------------------------------------------------------------------------
# bulk localisation of bpy classes
# -----------------------------------------------------------------------------

def _localize_enum_item(item):
    if not isinstance(item, (list, tuple)) or len(item) < 2:
        return item

    values = list(item)
    label = values[1]
    if isinstance(label, str) and label:
        values[1] = tr(label)
    if len(values) > 2 and isinstance(values[2], str) and values[2]:
        values[2] = tr(values[2])
    return tuple(values)


def _localize_annotations(cls):
    """Translates the ``name``/``description``/``items`` of bpy.props.

    Declarations such as ``name: StringProperty(name="...")`` become
    ``_PropertyDeferred`` objects in ``__annotations__`` before the class is
    registered.  Their keyword arguments can be rewritten in place, which is
    what allows the whole add-on to be localised without touching every
    property definition.
    """
    annotations = cls.__dict__.get("__annotations__")
    if not isinstance(annotations, dict):
        return

    for deferred in annotations.values():
        keywords = getattr(deferred, "keywords", None)
        if not isinstance(keywords, dict):
            continue

        name = keywords.get("name")
        if isinstance(name, str) and name:
            keywords["name"] = tr(name)

        description = keywords.get("description")
        if isinstance(description, str) and description:
            keywords["description"] = tr(description)

        items = keywords.get("items")
        if isinstance(items, (list, tuple)):
            keywords["items"] = tuple(_localize_enum_item(item) for item in items)


def _localize_class_labels(cls):
    """Translates the static labels of panels, menus and operators."""
    for attribute in ("bl_label", "bl_description", "bl_category"):
        value = cls.__dict__.get(attribute)
        if isinstance(value, str) and value:
            setattr(cls, attribute, tr(value))

    # Operators without an explicit bl_description use their docstring, which
    # Blender would hand to the built-in translation as-is.  Turn it into an
    # explicit description so it goes through Capsule's translation files.
    if "bl_description" not in cls.__dict__:
        docstring = cls.__dict__.get("__doc__")
        if isinstance(docstring, str) and docstring.strip():
            collapsed = " ".join(line.strip() for line in docstring.strip().splitlines())
            if collapsed:
                cls.bl_description = tr(collapsed)


def localize_classes(classes):
    """Translates the labels and property metadata of every class in ``classes``.

    Must be called right before the classes are registered by Blender.
    """
    for cls in classes:
        try:
            _localize_annotations(cls)
            _localize_class_labels(cls)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            # A single class that cannot be localised must never prevent the
            # add-on from registering - it simply stays in English.
            continue
