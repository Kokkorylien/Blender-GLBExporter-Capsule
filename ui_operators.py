
from gc import collect
from re import search
import bpy, bmesh, random, platform

from mathutils import Vector
from bpy.types import Operator
from bpy.props import IntProperty, BoolProperty, FloatProperty, EnumProperty, PointerProperty, StringProperty, CollectionProperty

from .tk_utils import search as search_utils
from .tk_utils import select as select_utils
from .tk_utils import object_ops
from .update.update_list import (
    ApplyCollectionTemplateToEntries,
    BulkAddCollections,
    GetCollectionSettingsTemplate,
    GetCollectionsForMode,
    RebuildCollectionCandidates,
    ResolveBatchCollectionTemplate,
)
from .export_formats import CAP_ExportFormat
from . import export_presets
from .i18n import tr

#///////////////// - LOCATION DEFAULTS - ///////////////////////////////////////////

class CAPSULE_OT_Add_Path(Operator):
    """Create a new Export Location"""

    bl_idname = "scene.cap_addpath"
    bl_label = "Add"

    def execute(self, context):
        #print(self)

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        newPath = cap_file.location_presets.add()
        newPath.name = "Location " + str(len(cap_file.location_presets))
        newPath.path = ""

        return {'FINISHED'}

class CAPSULE_OT_Delete_Path(Operator):
    "Delete the selected export location from the list.  This will also set the export location of all objects and collections that used this to 'None'"

    bl_idname = "scene.cap_deletepath"
    bl_label = "Remove"

    def execute(self, context):
        #print(self)

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        preset_index = cap_file.location_presets_listindex

        # Ensure that any objects with a matching preset are set to None.
        # The index needs increasing by one as it doesnt include 'None'
        objects = bpy.data.objects
        for obj in objects:
            cap_obj = obj.CAPObj
            if cap_obj.location_preset == str(preset_index + 1):
                cap_obj.location_preset = '0'

        collections = search_utils.GetSceneCollections(context.scene, False)
        for collection in collections:
            cap_col = collection.CAPCol
            if cap_col.location_preset == str(preset_index + 1):
                cap_col.location_preset = '0'
        
        # TODO: Ensure the selection interface is updated so it gets the new value!
        # TODO: Ensure this is as efficient as it can be for large scenes
        
        # Once everything has been set, remove it.
        cap_file.location_presets.remove(preset_index)

        # ensure the selected list index is within the list bounds
        if len(cap_file.location_presets) > 0:
            cap_file.location_presets_listindex -= 1
        

        return {'FINISHED'}

class CAPSULE_OT_Add_File_Location_Tag(Operator):
    """Add a new export location tag to the currently selected location.  These are used to auto-name file structures with information about the export like file name, time, etc"""

    bl_idname = "scene.cap_add_file_location_tag"
    bl_label = "Add Export Location Tag"

    path_tags: EnumProperty(
        name = "Add Path Tag",
        description = "",
        items =  (
        ('export_name', 'Export Name', 'Adds a folder with the name of the Object or Collection being exported.'),
        # ('object_type', 'Object Type', 'Adds a folder with the object type.'),
        # ('collection', 'Collection Name', 'Adds a folder with the collection name.'),
        ('blend_file_name', 'Blend File Name', 'Adds a folder with the blend file name.'),
        # ('location_preset_name', 'Location Preset Name', 'Adds a folder with the Location Preset name used on export.'),
        ('export_preset_name', 'Export Preset Name', 'Adds a folder with the Export Preset name used on export.'),
        ('export_date_ymd', 'Export Date (Year-Month-Day)', 'Adds a folder with the date of the export.'),
        ('export_date_dmy', 'Export Date (Day-Month-Year)', 'Adds a folder with the date of the export.'),
        ('export_date_mdy', 'Export Date (Month-Year-Day)', 'Adds a folder with the date of the export.'),
        ('export_time_hm', 'Export Time (Hour-Minute)', 'Adds a folder with the time of the export.'),
        ('export_time_hms', 'Export Time (Hour-Minute-Second)', 'Adds a folder with the time of the export.'),
        ),
    )

    def execute(self, context):
        #print(self)

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile
        
        # get the selected path
        path_index = cap_file.location_presets_listindex
        new_path = cap_file.location_presets[path_index].path
        end_path = ""

        # directory failsafe
        if platform.system() == 'Windows':
            if new_path.endswith("\\") == False and new_path.endswith("//") == False:
                new_path += "\\"
            end_path = "\\"
        else:
            if new_path.endswith("/") == False:
                new_path += "/"
            end_path = "\\"

        # insert the selected option into the currently selected path
        new_path += "^"
        new_path += self.path_tags
        new_path += "^" + end_path
        
        cap_file.location_presets[path_index].path = new_path

        return {'FINISHED'}


class CAPSULE_OT_Add_Export(Operator):
    """Create a new Export Preset"""

    bl_idname = "scene.cap_addexport"
    bl_label = "Add"

    def get_unique_id(self, context, cap_file):
        newID = random.randrange(0, 1000000)

        for preset in cap_file.export_presets:
            if preset.instance_id == newID:
                newID = self.get_unique_id(context, cap_file)

        return newID

    def execute(self, context):
        #print(self)

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile


        # make the new file preset
        newDefault = cap_file.export_presets.add()
        newDefault.name = "Export " + str(len(cap_file.export_presets))
        newDefault.path = ""

        # Ensure the tag index keeps within a window
        cap_file.export_presets_listindex = len(cap_file.export_presets) - 1

        return {'FINISHED'}



class CAPSULE_OT_Delete_Export(Operator):
    """
    Delete the selected export preset from the list.  This will also set the Export Preset of all
    objects and collections that used this to 'None'
    """

    bl_idname = "scene.cap_deleteexport"
    bl_label = "Delete Export Preset"

    #StringProperty(default = "Are you sure you wish to delete the selected preset?")

    @classmethod
    def poll(cls, context):
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        if len(cap_file.export_presets) > 0:
            return True

        return False

    def execute(self, context):
        #print(self)

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        preset_index = cap_file.export_presets_listindex

        # Ensure that any objects with a matching preset are set to None.
        # The index needs increasing by one as it doesnt include 'None'
        objects = bpy.data.objects
        for obj in objects:
            cap_obj = obj.CAPObj
            if cap_obj.export_preset == str(preset_index + 1):
                cap_obj.export_preset = '0'

        collections = search_utils.GetSceneCollections(context.scene, False)
        for collection in collections:
            cap_col = collection.CAPCol
            if cap_col.export_preset == str(preset_index + 1):
                cap_col.export_preset = '0'
        
        # TODO: Ensure the selection interface is updated so it gets the new value!
        # TODO: Ensure this is as efficient as it can be for large scenes
        
        # Once everything has been set, remove it.
        cap_file.export_presets.remove(preset_index)

        # ensure the selected list index is within the list bounds
        if cap_file.export_presets_listindex > 0:
            cap_file.export_presets_listindex -= 1

        return {'FINISHED'}


class CAPSULE_OT_Clear_List(Operator):
    """Delete all objects or collection from the export list, unmarking them for export"""

    bl_idname = "scene.cap_clearlist"
    bl_label = "Delete All"

    def execute(self, context):
        #print(self)

        scn = context.scene.CAPScn
        objectTab = int(str(scn.list_switch))

        if objectTab == 1:
            for object in context.scene.objects:
                obj = object.CAPObj
                obj.enable_export = False
                obj.in_export_list = False
            scn.object_list.clear()
            scn.object_list_index = 0
            scn.object_list_filter = ""

        elif objectTab == 2:
            for collection in search_utils.GetSceneCollections(context.scene, False):
                col = collection.CAPCol
                col.enable_export = False
                col.in_export_list = False
            scn.collection_list.clear()
            scn.collection_list_index = 0
            scn.collection_list_filter = ""

        return {'FINISHED'}

class CAPSULE_OT_Refresh_List(Operator):
    """Refresh the list of objects or collections marked for export in the scene.  In most cases Capsule can keep track of changes in the scene automatically"""

    bl_idname = "scene.cap_refreshlist"
    bl_label = "Refresh"

    def execute(self, context):
        #print(self)

        scn = context.scene.CAPScn
        objectTab = int(str(scn.list_switch))

        if objectTab == 1:
            scn.object_list.clear()
            for obj in context.scene.objects:
                if obj.CAPObj.in_export_list is True:
                    entry = scn.object_list.add()
                    entry.object = obj
                    entry.enable_export = obj.CAPObj.enable_export

            if scn.object_list_index >= len(scn.object_list):
                scn.object_list_index = max(0, len(scn.object_list) - 1)

        elif objectTab == 2:
            scn.collection_list.clear()
            for collection in search_utils.GetSceneCollections(context.scene, False):
                if collection.CAPCol.in_export_list is True:
                        entry = scn.collection_list.add()
                        entry.collection = collection
                        entry.enable_export = collection.CAPCol.enable_export

            if scn.collection_list_index >= len(scn.collection_list):
                scn.collection_list_index = max(0, len(scn.collection_list) - 1)

        return {'FINISHED'}


class CAPSULE_OT_Add_Collections(Operator):
    """Add collections from the current View Layer to the Export List.  The settings of the selected Export List entry are copied to the new collections by default"""

    bl_idname = "scene.cap_addcollections"
    bl_label = "Add Collections"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(
        name = "Add Mode",
        description = "Which collections to add to the Export List",
        items = (
            ('ACTIVE', 'Active Collection', 'Add the active collection'),
            ('ACTIVE_RECURSIVE', 'Active Collection and Children', 'Add the active collection and every child collection'),
            ('SELECTED_OBJECTS', 'Collections of Selected Objects', 'Add every collection used by the selected objects'),
            ('ALL_WITH_OBJECTS', 'All Collections With Objects', 'Add every collection in the scene that contains objects'),
            ('ALL', 'All Collections', 'Add every collection in the scene'),
        ),
        default = 'ACTIVE',
    )

    def execute(self, context):
        collections = GetCollectionsForMode(context, self.mode)
        template = GetCollectionSettingsTemplate(context)

        added, skipped = BulkAddCollections(context, collections, template = template)

        if added == 0:
            self.report({'INFO'}, tr(
                "No new collections were added ({skipped} skipped).",
                skipped = skipped))
        else:
            self.report({'INFO'}, tr(
                "Added {added} collections to the Export List ({skipped} skipped).",
                added = added, skipped = skipped))

        return {'FINISHED'}


class CAPSULE_OT_Show_Collection_Picker(Operator):
    """Open the batch collection picker below the Export List, where collections can be searched and picked before they are added"""

    bl_idname = "scene.cap_addcollections_picker"
    bl_label = "Choose Collections"

    def execute(self, context):
        scn = context.scene.CAPScn
        scn.bulk_add_active = True
        RebuildCollectionCandidates(context)
        return {'FINISHED'}


class CAPSULE_OT_Close_Collection_Picker(Operator):
    """Close the batch collection picker without adding any collections"""

    bl_idname = "scene.cap_bulk_close"
    bl_label = "Close Batch Add"

    def execute(self, context):
        scn = context.scene.CAPScn
        scn.bulk_add_active = False
        scn.bulk_candidates.clear()
        return {'FINISHED'}


class CAPSULE_OT_Refresh_Collection_Picker(Operator):
    """Rebuild the batch collection picker from the current scene"""

    bl_idname = "scene.cap_bulk_refresh"
    bl_label = "Refresh Collection Picker"

    def execute(self, context):
        RebuildCollectionCandidates(context)
        return {'FINISHED'}


class CAPSULE_OT_Bulk_Select_Collections(Operator):
    """Check or uncheck the collections shown in the batch collection picker"""

    bl_idname = "scene.cap_bulk_select"
    bl_label = "Select Collections"

    select: BoolProperty(
        name = "Select",
        description = "Check the matching collections instead of unchecking them",
        default = True,
    )

    filtered_only: BoolProperty(
        name = "Filtered Only",
        description = "Only change collections that match the picker search",
        default = False,
    )

    def execute(self, context):
        scn = context.scene.CAPScn

        for item in scn.bulk_candidates:
            if item.collection is None or item.already_added:
                continue

            if self.filtered_only and not search_utils.NameMatches(
                    item.collection.name, scn.bulk_filter, scn.bulk_filter_wildcard):
                continue

            item.add = self.select

        return {'FINISHED'}


class CAPSULE_OT_Apply_Collection_Selection(Operator):
    """Add the checked collections from the batch collection picker to the Export List"""

    bl_idname = "scene.cap_addcollections_apply"
    bl_label = "Add Selected Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene.CAPScn

        collections = []
        for item in scn.bulk_candidates:
            if item.add and item.collection is not None and not item.already_added:
                collections.append(item.collection)

        if len(collections) == 0:
            self.report({'WARNING'}, tr("Select at least one collection to add."))
            return {'CANCELLED'}

        template = ResolveBatchCollectionTemplate(context)

        added, skipped = BulkAddCollections(
            context, collections,
            template = template,
            skip_covered_children = scn.bulk_skip_covered)

        scn.bulk_add_active = False
        scn.bulk_candidates.clear()

        if added == 0:
            self.report({'INFO'}, tr(
                "No new collections were added ({skipped} skipped).",
                skipped = skipped))
        else:
            self.report({'INFO'}, tr(
                "Added {added} collections to the Export List ({skipped} skipped).",
                added = added, skipped = skipped))

        return {'FINISHED'}


class CAPSULE_OT_Copy_Collection_Settings(Operator):
    """Copy the export settings of the selected Export List entry to the other entries in the collection list"""

    bl_idname = "scene.cap_copy_collection_settings"
    bl_label = "Copy Collection Settings"
    bl_options = {'REGISTER', 'UNDO'}

    filtered_only: BoolProperty(
        name = "Filtered Only",
        description = "Only update collection list entries that match the current search.  When the search is empty, every other entry is updated",
        default = False,
    )

    def execute(self, context):
        updated = ApplyCollectionTemplateToEntries(context, self.filtered_only)

        if updated == 0:
            self.report({'WARNING'}, tr("No other collection list entries to update."))
        else:
            self.report({'INFO'}, tr("Copied settings to {count} entries.", count = updated))

        return {'FINISHED'}


class CAPSULE_OT_Clear_List_Filter(Operator):
    """Clear the search filter of the current Export List"""

    bl_idname = "scene.cap_clear_list_filter"
    bl_label = "Clear Search"

    filter_type: EnumProperty(
        name = "Filter Type",
        description = "Which Export List search filter to clear",
        items = (
            ('OBJECT', 'Objects', 'Clear the object Export List search'),
            ('COLLECTION', 'Collections', 'Clear the collection Export List search'),
        ),
        default = 'COLLECTION',
    )

    def execute(self, context):
        scn = context.scene.CAPScn

        if self.filter_type == 'OBJECT':
            scn.object_list_filter = ""
        else:
            scn.collection_list_filter = ""

        return {'FINISHED'}


class CAPSULE_OT_Reset_Properties(Operator):
    """Reset all assigned export properties to every Object and Collection in every scene, and clear both Export Lists"""

    bl_idname = "scene.cap_resetsceneprops"
    bl_label = "Reset Scene"

    def execute(self, context):
        #print(self)

        #self.export_stats['object_export_count'] = 0

        # Keep a record of the selected and active objects to restore later
        active = None
        selected = []

        for collection in bpy.data.collections:
            col = collection.CAPCol
            col.enable_export = False
            col.origin_point = 'Object'
            col.location_preset = '0'
            col.export_preset = '0'
            col.pack_script = None

        for object in bpy.data.objects:
            obj = object.CAPObj
            obj.enable_export = False
            obj.origin_export = "Scene"
            obj.root_object = None
            obj.location_preset = '0'
            obj.export_preset = '0'
            col.pack_script = None
        
        scn = context.scene.CAPScn
        list_tab = str(scn.list_switch)

        scn.list_switch = '1'
        bpy.ops.scene.cap_clearlist()

        scn.list_switch = '2'
        bpy.ops.scene.cap_clearlist()

        scn.list_switch = list_tab

        return {'FINISHED'}


class CAPSULE_OT_Create_ExportData(Operator):
    """Create a new empty object for which Capsule data is stored and where both Active Export Presets and other scene data is stored"""

    bl_idname = "cap.exportdata_create"
    bl_label = "Create Capsule Data"

    def execute(self, context):
        #print(self)

        preferences = bpy.context.preferences
        addon_prefs = preferences.addons[__package__].preferences

        # Ensure we're in the right context before creating the datablock.
        override = object_ops.Find3DViewContext()
        prev_mode = context.mode
        prev_active_object = context.active_object
        prev_selected_objects = context.selected_objects

        with context.temp_override(
            screen = override['screen'],
            window = context.window_manager.windows[0], 
            area = override['area'], 
            region = override['region']
            ):

            print("honk")

            if prev_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)  

            # TODO: Why can't I just use data.objects?
            
            # Figure out if an object already exists, if yes do nothing
            for object in bpy.data.objects:
                #print(object)
                if object.name == addon_prefs.default_datablock:
                    self.report({'WARNING'}, "Capsule data for the blend file has been found, a new one will not be created.")
                    return {'CANCELLED'}

            # Otherwise create the object using the addon preference data
            bpy.ops.object.select_all(action ='DESELECT')
            bpy.ops.object.empty_add(type = 'CIRCLE') # apparently using plain axes causes a crash.

            default_datablock = bpy.context.view_layer.objects.active
            default_datablock.name = addon_prefs.default_datablock
            default_datablock.hide_viewport = True
            default_datablock.hide_render = True
            default_datablock.hide_select = True
            default_datablock.CAPFile.is_storage_object = True
            addon_prefs.data_missing = False

            context.view_layer.objects.active = prev_active_object
            for obj in prev_selected_objects:
                obj.select_set(state=True)

            # # Restore the context
            if prev_mode != 'OBJECT':

                # We need this because the context returns separate definitions.
                if prev_mode.find('EDIT') != -1:
                    prev_mode = 'EDIT'
                
                bpy.ops.object.mode_set(mode=prev_mode, toggle=False)

        self.report({'INFO'}, "Capsule data created.")
        return {'FINISHED'}


class CAPSULE_OT_Add_Stored_Presets(Operator):
    """Add the currently selected Stored Export Preset into the Active Export Presets list, enabling it's use for exports in this .blend file"""
    bl_idname = "cap.create_current_preset"
    bl_label = "Activate Selected"

    @classmethod
    def poll(cls, context):
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        if len(addon_prefs.saved_export_presets) > 0:
            return True

        else:
            return False

    def execute(self, context):

        # Get the current export data
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        # Obtain the selected preset
        new_preset = cap_file.export_presets.add()
        export_presets.CopyPreset(addon_prefs.saved_export_presets[addon_prefs.saved_export_presets_index], new_preset)

        return {'FINISHED'}

class CAPSULE_OT_Delete_Presets(Operator):
    """Delete the currently selected Export Preset"""
    bl_idname = "cap.delete_stored_export_preset"
    bl_label = "Delete Stored Preset"

    def execute(self, context):

        # Get the current export data
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        # Obtain the selected preset
        addon_prefs.saved_export_presets.remove(addon_prefs.saved_export_presets_index)

        # Decrement the list selection
        if addon_prefs.saved_export_presets_index > 0:
            addon_prefs.saved_export_presets_index -= 1

        return {'FINISHED'}

class CAPSULE_OT_Store_Presets(Operator):
    """Save the currently selected export preset to your Stored Export Presets list, to enable it's use in across .blend files"""
    bl_idname = "cap.store_active_export_preset"
    bl_label = "Store Preset"

    @classmethod
    def poll(cls, context):
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        if len(cap_file.export_presets) > 0:
            return True

        else:
            return False


    def execute(self, context):

        # Get the current export data
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        # Obtain the selected preset
        new_preset = addon_prefs.saved_export_presets.add()
        export_presets.CopyPreset(cap_file.export_presets[cap_file.export_presets_listindex], new_preset)

        return {'FINISHED'}

class CAPSULE_OT_Show_Preferences(Operator):
    """Open a window to the Capsule Addon Preferences Menu"""
    bl_idname = "scene.cap_show_preferences"
    bl_label = "Show Addon Preferences"

    def execute(self, context):

        # Get the current export data
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile

        bpy.ops.screen.userpref_show()
        context.preferences.active_section = 'ADDONS'
        bpy.data.window_managers["WinMan"].addon_search = "Capsule"


        return {'FINISHED'}

class CAPSULE_OT_Tutorial_StoredPresets(Operator):
    """Open a message describing how Stored Export Presets work"""
    bl_idname = "scene.cap_tut_storedpresets"
    bl_label = ""

    def execute(self, context):

        def tutorial_layout(self, context):
            self.layout.label(text = tr("Stored Export Presets are export settings you want to use to store"))
            self.layout.label(text = tr("and use in different .blend files."))
            self.layout.label(text = "")
            self.layout.label(text = tr("If Auto-Save Preferences is enabled, the presets you store will be"))
            self.layout.label(text = tr("saved when you close the Blender Preferences window.  Otherwise you"))
            self.layout.label(text = tr("will need to use the 'Save Preferences' button in the bottom-left."))
            self.layout.label(text = tr("Stored Export Presets are stored in the add-on preferences, and can be imported and exported as a .json file."))

        # Get the current export data
        bpy.context.window_manager.popup_menu(tutorial_layout, title=tr("Stored Export Presets"), icon='HELP')


        return {'FINISHED'}

class CAPSULE_OT_Tutorial_ActivePresets(Operator):
    """Open a message describing how Active Export Presets work"""
    bl_idname = "scene.cap_tut_activepresets"
    bl_label = ""

    def execute(self, context):

        def tutorial_layout(self, context):
            self.layout.label(text = tr("Active Export Presets are export settings that can be assigned to"))
            self.layout.label(text = tr("different Objects and Collections in the current Blend file."))
            self.layout.label(text = "")
            self.layout.label(text = tr("They are saved with your .blend file in a special hidden object."))
            self.layout.label(text = "")
            self.layout.label(text = tr("(The object is called '>Capsule Blend File Data<', don't delete it!)."))

        # Get the current export data
        bpy.context.window_manager.popup_menu(tutorial_layout, title=tr("Active Export Presets"), icon='HELP')


        return {'FINISHED'}


class CAPSULE_OT_Reload_Addon(Operator):
    """Reload Capsule so language and interface changes are applied immediately"""

    bl_idname = "cap.reload_addon"
    bl_label = "Reload Add-On"

    def execute(self, context):
        module = __package__

        # The add-on cannot unregister itself while one of its own operators is
        # still executing, so the reload is deferred to a timer.
        def _reload():
            try:
                bpy.ops.preferences.addon_disable(module = module)
                bpy.ops.preferences.addon_enable(module = module)
            except (RuntimeError, AttributeError) as error:
                print("Capsule:", tr(
                    "Could not reload Capsule automatically, please restart Blender. ({error})",
                    error = error))
            return None

        bpy.app.timers.register(_reload, first_interval = 0.2)
        self.report({'INFO'}, tr("Capsule is reloading..."))
        return {'FINISHED'}


