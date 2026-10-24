
![](img_readme/capsule_banner.png)

Capsule makes the process of exporting quick and seamless, letting you export hundreds of assets into multiple formats with a single click.


## Features

* **Batch Exports** - Choose export settings for hundreds of Objects and Collections with one click and export with one click.

* **Smart Modifier Export** - Every export (all active targets, selected targets, or a list selection) only keeps the Decimate and Data Transfer modifiers of the target currently being written live.  Every other collection's modifiers stay temporarily disabled, which keeps large scenes fast without changing the exported result.

* **Export Lists** - Browse and search through all objects and collections marked for export and quickly adjust their settings.

* **Origin Point Export** - Decide where the origin point is in your exports, no need to manually move around your objects before exporting.

* **Export Presets** - Create detailed and reusable export presets for different Export Formats, supporting Alembic, Collada, FBX, GLTF, OBJ, STL and USD/USDZ export formats.

* **Automated Folder Structures** - Automatically generate folders with certain criteria to help keep complex export setups organised.


## Installation

- Download the latest release from the releases page.
- MAKE SURE the downloaded ZIP file is renamed to "Capsule.zip"
- Under Preferences > Addons > Install, select Capsule.zip.


## FAQ
**How do I use this plugin?**

Check out the Github Wiki for quick instructions on getting started - https://github.com/Takanu/Capsule/wiki.


**What version of Blender does the plugin work with?**

The current version supports Blender 3.5, if you need support for older Blender versions then browse the Releases page and find the right one for your version - https://github.com/Takanu/Capsule/releases.


**Are there things that Capsule can't currently export?**

Theres a few use cases where Capsule may have trouble exporting assets from your scene:

* Animations that aren't attached to Armature Bones using an Object Origin Point - If you try to do this it will likely fail, keep these to using Scene origin points.

* Bone Constraints - The "Preserve Armature Constraints" button under the Armature tab in the Export Presets menu can help if you need to export an armature with bone constraints, as it is unlikely to export properly when left. This however is currently an experimental feature, so results may vary.


**What if i have a problem or bug with the add-on?**

* You can post an issue on the GitHub page (https://github.com/Takanu/Capsule/issues), this is the best place to post an issue as I can categorize and keep track of them in one place.


**Do you have any other cool add-ons?**

Yep, and they're all completely free - check out my GitHub account for other Blender goodies (https://github.com/Takanu).


## Stored Export Presets as files

Stored Export Presets (Add-on Preferences > Capsule > Stored Export Presets) are saved
inside Blender's `userpref.blend`, which makes them hard to inspect, back up or share
between machines.  The preferences panel now shows that path and adds:

* **Export** - write every stored preset (or only the selected one) to a readable
  `capsule_export_presets.json` file.
* **Import** - read such a file back.  Use the `Import Mode` option on the operator
  (press F9 after importing) to append to the existing list or replace it.
* **Show Settings Preview** - a read-only summary of the selected preset that lists
  only the options it changes, so a preset like `NekoMdl_Shape` can be understood
  without activating it.  The info button next to the list opens the same summary
  as a popup, the console button prints every option.

Preset files are versioned (`"schema": 1`), keyed by the English UI text and are
written as UTF-8 JSON, so they can be diffed and versioned in a repository.
Unknown or unsupported entries are skipped instead of failing the whole import.


## Language support

Capsule no longer relies on Blender's built-in, dictionary based UI translation,
which used to turn short English words (including the add-on name) into mechanical
translations and leave the interface half translated.  Instead it ships its own
translation files:

* `translations/zh_HANS.json` - Simplified Chinese.
* Any language without a file, or any string without an entry, falls back to English
  and is explicitly excluded from Blender's built-in translation.

The language is picked automatically from Blender's own language, and can be forced
in the add-on preferences (Extra Settings > Language).  Because property labels are
registered with Blender, changing the language requires reloading the add-on - the
**Reload Add-On** button does that.

To add a language, copy `zh_HANS.json` to `<language code>.json`, translate the
values (keys stay English) and reload the add-on.  Option lists of file formats that
have no entries yet stay in English on purpose rather than being mechanically
translated.


