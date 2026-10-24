![](img_readme/capsule_banner.png)

**English** | [简体中文](README_zh_HANS.md)

Capsule makes the process of exporting quick and seamless, letting you export hundreds of assets into multiple formats with a single click.

This repository is a community fork of [Takanu/Capsule](https://github.com/Takanu/Capsule), maintained by [Kokkorylien](https://github.com/Kokkorylien). It is not an official Takanu release.

> **Blender compatibility**
>
> This build is intended for **Blender 4.0.2**. It has **not been tested on any other Blender version**. Other versions may work in theory, but they are not supported; please back up your scene and use them at your own risk.

> **Performance**
>
> In scenes with many enabled **Decimate** and **Data Transfer** modifiers, this fork exports **much faster than the upstream version it was forked from**. See [Why this fork?](#why-this-fork).

## Why this fork?

The main difference from the upstream project is export performance when a scene contains a large number of **Decimate** and **Data Transfer** modifiers.

The upstream add-on leaves those modifiers enabled for the whole scene while it exports one target after another. Every export can therefore make Blender evaluate heavy modifier stacks on objects that are not part of the target currently being written.

This fork adds **Smart Modifier Export**:

- It records the original viewport/render visibility of every Decimate and Data Transfer modifier before the export starts.
- It temporarily disables those modifiers across the scene, so building the export list and writing the first target do not evaluate the whole scene.
- It re-enables only the modifiers belonging to the target currently being written, including the source objects of Data Transfer modifiers.
- It restores every modifier to its original visibility when the export finishes.

As a result, scenes with many enabled Decimate/Data Transfer modifiers export **substantially faster** than with the upstream version. The exact speedup depends on the scene, the number of modifiers and Blender's dependency graph; it is not a fixed multiplier. The exported result is not changed: modifiers that were disabled before the export stay disabled, and the original state is restored afterwards.

## Features

* **Smart Modifier Export (major performance improvement)** - Only the Decimate and Data Transfer modifiers of the export target currently being written stay live. Every other collection's modifiers are temporarily disabled, which keeps large scenes fast without changing the exported result.

* **Batch Exports** - Choose export settings for hundreds of Objects and Collections with one click and export with one click.

* **Export Lists** - Browse and search through all objects and collections marked for export and quickly adjust their settings.

* **Batch Collection Add** - Add whole collection hierarchies to the Export List in one action, pick collections from a searchable list, and copy one list entry's export settings to every newly added collection.

* **Origin Point Export** - Decide where the origin point is in your exports, no need to manually move around your objects before exporting.

* **Export Presets** - Create detailed and reusable export presets for different Export Formats, supporting Alembic, Collada, FBX, GLTF, OBJ, STL and USD/USDZ export formats.

* **Automated Folder Structures** - Automatically generate folders with certain criteria to help keep complex export setups organised.

* **Simplified Chinese UI** - Ships with its own translation layer and a complete Simplified Chinese translation.

## Batch adding collections

The collection side of the Export List can be filled in bulk instead of ticking one collection at a time:

1. In **Properties > Scene > Capsule > Export List**, switch to **Collections**.
2. Select an existing list entry and configure its Origin, Export Location and Export Preset. New collections copy these settings by default.
3. Use the **+** button next to the list:
   * **Active Collection** / **Active Collection and Children** - add the collection selected in the Outliner, optionally with its whole hierarchy.
   * **Collections of Selected Objects** - add every collection used by the selected objects.
   * **All Collections With Objects** / **All Collections** - add everything in the current View Layer.
   * **Choose Collections...** - open the batch picker, search by name (substring or `*`/`?` wildcards), tick the collections and press **Add Selected**.

Adding is one undo step. Collections that are already in the list are skipped, so the same action can be repeated safely. Added collections are enabled for export automatically.

To reuse the settings later, select a configured entry and use the copy-settings button next to the list to apply them to the filtered entries or to every other entry.

If no list entry is selected, or **Copy Settings From Selected Entry** is turned off in the picker, the batch settings below it are used instead. **Skip Child Collections of Added Parents** avoids adding a collection whose listed parent already exports all of its children.

The search fields above the list filter Objects and Collections by name; the **X** next to them clears the filter.

## Installation

- Download a release from this fork's [Releases page](https://github.com/Kokkorylien/Blender-GLBExporter-Capsule/releases).
- Make sure the ZIP is packaged as `Capsule.zip` and contains a `Capsule/` folder at its root.
- In Blender, open **Edit > Preferences > Add-ons > Install...**, select `Capsule.zip`, then enable **Capsule**.

## FAQ

**What version of Blender does the plugin work with?**

This build is intended for **Blender 4.0.2**. It has not been tested on any other Blender version, older or newer. Other versions may work in theory, but they are not supported; back up your scene first.

**Why is export faster than the upstream version?**

Because it does not keep every Decimate and Data Transfer modifier in the scene live while exporting. See [Why this fork?](#why-this-fork) for the full explanation.

**Does Smart Modifier Export change my scene or my export result?**

No. It records the original visibility, temporarily disables expensive modifiers, enables only the ones needed by the current target, and restores the original state afterwards. A modifier that was deliberately disabled before the export stays disabled.

**How do I use this plugin?**

Check the upstream GitHub Wiki for getting-started instructions: https://github.com/Takanu/Capsule/wiki

**Where do I report a bug with this fork?**

Open an issue on this repository: https://github.com/Kokkorylien/Blender-GLBExporter-Capsule/issues

**Are there things that Capsule can't currently export?**

There are a few use cases where Capsule may have trouble exporting assets from your scene:

* Animations that aren't attached to Armature Bones using an Object Origin Point - If you try to do this it will likely fail, keep these to using Scene origin points.

* Bone Constraints - The "Preserve Armature Constraints" button under the Armature tab in the Export Presets menu can help if you need to export an armature with bone constraints, as it is unlikely to export properly when left. This is currently an experimental feature, so results may vary.

## Stored Export Presets as files

Stored Export Presets (Add-on Preferences > Capsule > Stored Export Presets) are saved inside Blender's `userpref.blend`, which makes them hard to inspect, back up or share between machines. The preferences panel now shows that path and adds:

* **Export** - write every stored preset (or only the selected one) to a readable `capsule_export_presets.json` file.
* **Import** - read such a file back. Use the `Import Mode` option on the operator (press F9 after importing) to append to the existing list or replace it.
* **Show Settings Preview** - a read-only summary of the selected preset that lists only the options it changes, so a preset like `NekoMdl_Shape` can be understood without activating it. The info button next to the list opens the same summary as a popup, the console button prints every option.

Preset files are versioned (`"schema": 1`), keyed by the English UI text and are written as UTF-8 JSON, so they can be diffed and versioned in a repository. Unknown or unsupported entries are skipped instead of failing the whole import.

## Language support

Capsule no longer relies on Blender's built-in, dictionary based UI translation, which used to turn short English words (including the add-on name) into mechanical translations and leave the interface half translated. Instead it ships its own translation files:

* `translations/zh_HANS.json` - Simplified Chinese.
* Any language without a file, or any string without an entry, falls back to English and is explicitly excluded from Blender's built-in translation.

The language is picked automatically from Blender's own language, and can be forced in the add-on preferences (Extra Settings > Language). Because property labels are registered with Blender, changing the language requires reloading the add-on - the **Reload Add-On** button does that.

To add a language, copy `zh_HANS.json` to `<language code>.json`, translate the values (keys stay English) and reload the add-on. Option lists of file formats that have no entries yet stay in English on purpose rather than being mechanically translated.

## Credits

Original add-on by Takanu Kyriako: https://github.com/Takanu/Capsule

This fork is maintained by Kokkorylien and is distributed under the same GPL license; see `LICENSE.txt`.
