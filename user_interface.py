
import bpy
from bpy.props import IntProperty, BoolProperty, FloatProperty, EnumProperty, PointerProperty
from bpy.types import Menu, Panel, AddonPreferences, PropertyGroup, UIList
from rna_prop_ui import PropertyPanel

from .tk_utils import select
from .tk_utils import search as collection_utils
from .update.update_list import (
    CountSelectedCollectionCandidates,
    GetSelectedCollectionListEntry,
)
from .i18n import tr

class CAPSULE_UL_Name(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

            layout.prop(item, "name", text= "", emboss= False)

class CAPSULE_UL_Object(UIList):
    """Populates an export list based on properties that are representations of an object 
        rather than the actual object itself"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        scn = context.scene.CAPScn

        # ////////////////
        # DELETED OBJECT LIST ITEM
        no_object = (item.object == None)
        if item.object != None:
            no_object = (bpy.context.scene.objects.get(item.object.name) == None)

        if no_object:
            # spaces are here to cheat on the layout spacing
            layout.label(text = "  " + tr("Deleted Object"))
            # layout.prop(item, "deleted_name", text = "", emboss = False)
            layout.prop(item, "remove", text = "", icon = "X", emboss= False)
            layout.active = False
            return


        # ////////////////
        # NORMAL OBJECT LIST ITEM
        cap_obj = item.object.CAPObj
        missing_data = (cap_obj.export_preset == '0' or cap_obj.location_preset == '0')

        layout.prop(item.object, "name", text = "", emboss = False)
        
        if missing_data:
            layout.prop(item, "missing_data", text = "", icon = "ERROR", emboss = False)
            layout.separator()
            
        layout.prop(item, "enable_export", text = "")

        # A switch to change the extra tool on the Object list entries.
        if addon_prefs.list_feature != 'none':
            layout.prop(item, addon_prefs.list_feature, text= "", emboss= False, icon= 'FULLSCREEN_EXIT')

        layout.prop(item, "remove", text= "", icon = "X", emboss= False)
        
    
    def filter_items(self, context, data, property):
        attributes = getattr(data, property)
        indices = [i for i in range(len(attributes))]
        objects = [item.object for item in attributes]

        # The panel search field takes priority over the built-in UI List
        # filter, so entries can be found without opening the list header.
        pattern = context.scene.CAPScn.object_list_filter
        if not pattern:
            pattern = self.filter_name

        flags = [
            self.bitflag_filter_item
            if collection_utils.NameMatches(objects[i].name if objects[i] is not None else "", pattern)
            else 0
            for i in indices
        ]

        if self.use_filter_sort_alpha:
            indices = sorted(
                indices,
                key = lambda i: (objects[i].name.lower() if objects[i] is not None else ""),
                reverse = self.use_filter_sort_reverse)

        return flags, indices


class CAPSULE_UL_Collection(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        scn = context.scene.CAPScn
        
        # ////////////////
        # DELETED COLLECTION LIST ITEM
        if item.collection == None:
            # spaces are here to cheat on the layout spacing
            layout.label(text = "  " + tr("Deleted Collection"))
            # layout.prop(item, "deleted_name", text = "", emboss = False)
            layout.prop(item, "remove", text = "", icon = "X", emboss= False)
            layout.active = False
            return


        # ////////////////
        # NORMAL COLLECTION LIST ITEM
        cap_col = item.collection.CAPCol
        missing_data = (cap_col.export_preset == '0' 
            or cap_col.location_preset == '0'
            or (cap_col.origin_point == 'Object' and cap_col.root_object == None))

        layout.prop(item.collection, "name", text= "", emboss= False)

        if missing_data:
            layout.prop(item, "missing_data", text = "", icon = "ERROR", emboss = False)
            layout.separator()

        layout.prop(item, "enable_export", text= "")

        # A switch to change the extra tool on the Collection list entries.
        if addon_prefs.list_feature != 'none':
            layout.prop(item, addon_prefs.list_feature, text= "", emboss= False, icon= 'FULLSCREEN_EXIT')

        layout.prop(item, "remove", text= "", icon = "X", emboss= False)

    def filter_items(self, context, data, property):
        attributes = getattr(data, property)
        indices = [i for i in range(len(attributes))]
        collections = [item.collection for item in attributes]

        pattern = context.scene.CAPScn.collection_list_filter
        if not pattern:
            pattern = self.filter_name

        flags = [
            self.bitflag_filter_item
            if collection_utils.NameMatches(collections[i].name if collections[i] is not None else "", pattern)
            else 0
            for i in indices
        ]

        if self.use_filter_sort_alpha:
            indices = sorted(
                indices,
                key = lambda i: (collections[i].name.lower() if collections[i] is not None else ""),
                reverse = self.use_filter_sort_reverse)

        return flags, indices


class CAPSULE_UL_CollectionPicker(UIList):
    """
    The checkbox list used by the batch collection picker.  Entries are
    indented by their nesting depth so the scene hierarchy stays readable.
    """

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        row = layout.row(align = True)
        indent = "    " * item.depth

        if item.collection is None:
            row.active = False
            row.label(text = indent + tr("Missing Collection"))
            return

        row.active = not item.already_added
        row.prop(item, "add", text = "")
        row.label(text = indent + item.collection.name, icon = 'NONE')

        if item.already_added:
            row.label(text = tr("In list"), icon = 'CHECKMARK')

    def filter_items(self, context, data, property):
        attributes = getattr(data, property)
        scn = context.scene.CAPScn
        indices = [i for i in range(len(attributes))]

        flags = [
            self.bitflag_filter_item
            if collection_utils.NameMatches(
                attributes[i].collection.name if attributes[i].collection is not None else "",
                scn.bulk_filter, scn.bulk_filter_wildcard)
            else 0
            for i in indices
        ]

        return flags, indices


class CAPSULE_MT_Add_Collections(Menu):
    bl_label = "Add Collections"

    def draw(self, context):
        layout = self.layout

        operation = layout.operator("scene.cap_addcollections",
            text = tr("Active Collection"), icon = 'COLLECTION_NEW')
        operation.mode = 'ACTIVE'

        operation = layout.operator("scene.cap_addcollections",
            text = tr("Active Collection and Children"), icon = 'COLLECTION_NEW')
        operation.mode = 'ACTIVE_RECURSIVE'

        operation = layout.operator("scene.cap_addcollections",
            text = tr("Collections of Selected Objects"), icon = 'RESTRICT_SELECT_OFF')
        operation.mode = 'SELECTED_OBJECTS'

        layout.separator()

        operation = layout.operator("scene.cap_addcollections",
            text = tr("All Collections With Objects"), icon = 'OUTLINER_COLLECTION')
        operation.mode = 'ALL_WITH_OBJECTS'

        operation = layout.operator("scene.cap_addcollections",
            text = tr("All Collections"), icon = 'OUTLINER_COLLECTION')
        operation.mode = 'ALL'

        layout.separator()

        layout.operator("scene.cap_addcollections_picker",
            text = tr("Choose Collections..."), icon = 'VIEWZOOM')


class CAPSULE_MT_Copy_Collection_Settings(Menu):
    bl_label = "Copy Settings"

    def draw(self, context):
        layout = self.layout

        operation = layout.operator("scene.cap_copy_collection_settings",
            text = tr("Apply to Filtered Entries"), icon = 'COPYDOWN')
        operation.filtered_only = True

        operation = layout.operator("scene.cap_copy_collection_settings",
            text = tr("Apply to All Other Entries"), icon = 'COPYDOWN')
        operation.filtered_only = False


class CAPSULE_UL_Path_Default(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        scn = context.scene.CAPScn
        layout.prop(item, "name", text= "", emboss= False)

class CAPSULE_UL_Saved_Default(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        scn = context.scene.CAPScn
        layout.prop(item, "name", text= "", emboss= False)

class CAPSULE_UL_Export_Default(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        scn = context.scene.CAPScn
        layout.prop(item, "name", text= "", emboss= False)

class CAPSULE_UL_Action(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        scn = context.scene.CAPScn
        active = context.active_object

        icon = "OBJECT_DATA"

        if item.anim_type == '2':
            icon = "OBJECT_DATA"
        elif item.anim_type == '4':
            icon = "OUTLINER_OB_ARMATURE"

        layout.prop(item, "name", text= "", icon=icon, emboss= False)
        layout.separator()

#//////////////////////// - USER INTERFACE - ////////////////////////

def Draw_CollectionBatchAdd(context, layout):
    """
    Draws the batch collection picker below the Export List.
    """

    scn = context.scene.CAPScn
    box = layout.box()

    header = box.row(align = True)
    header.label(text = tr("Add Collections"), icon = 'ADD')
    header.operator("scene.cap_bulk_close", text = "", icon = 'X')

    search = box.row(align = True)
    search.prop(scn, "bulk_filter", text = "", icon = 'VIEWZOOM')
    search.prop(scn, "bulk_filter_wildcard", text = "", toggle = True, icon = 'SORTALPHA')

    buttons = box.row(align = True)
    buttons.operator("scene.cap_bulk_select", text = tr("Select All")).select = True
    operation = buttons.operator("scene.cap_bulk_select", text = tr("Select None"))
    operation.select = False
    operation = buttons.operator("scene.cap_bulk_select", text = tr("Select Filtered"))
    operation.select = True
    operation.filtered_only = True
    buttons.operator("scene.cap_bulk_refresh", text = "", icon = 'FILE_REFRESH')

    list_row = box.row()
    list_row.template_list("CAPSULE_UL_CollectionPicker", "collection_picker",
        scn, "bulk_candidates",
        scn, "bulk_candidates_index", rows = 8, maxrows = 14)

    selected = CountSelectedCollectionCandidates(scn)
    box.label(text = tr("Selected: {selected} / {total}",
        selected = selected, total = len(scn.bulk_candidates)), icon = 'INFO')

    settings = box.column(align = True)
    settings.prop(scn, "bulk_apply_settings")

    if scn.bulk_apply_settings:
        selected_entry = GetSelectedCollectionListEntry(context)
        settings.prop(scn, "bulk_copy_from_selected")

        if scn.bulk_copy_from_selected and selected_entry is not None:
            settings.label(text = tr("Copying settings from: {name}",
                name = selected_entry.collection.name), icon = 'COPYDOWN')
        else:
            options = settings.column(align = True)
            options.use_property_split = True
            options.use_property_decorate = False
            options.prop(scn, "bulk_origin_point")

            if scn.bulk_origin_point == 'Object':
                options.prop(scn, "bulk_root_object")

            options.prop(scn, "bulk_collection_children")
            options.prop(scn, "bulk_location_preset")
            options.prop(scn, "bulk_export_preset")

            if scn.bulk_copy_from_selected:
                settings.label(text = tr("No Export List entry selected, using the settings above."), icon = 'INFO')

    settings.prop(scn, "bulk_skip_covered")

    actions = box.row(align = True)
    actions.operator("scene.cap_addcollections_apply",
        text = tr("Add Selected ({count})", count = selected), icon = 'ADD')
    actions.operator("scene.cap_bulk_close", text = tr("Cancel"))


class CAPSULE_PT_Header(Panel):
    bl_space_type = "PROPERTIES"
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_label = "Capsule"

    def draw(self, context):
        pass


class CAPSULE_PT_Selection(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Capsule"
    bl_context = "objectmode"
    bl_label = "Export Options"
    

    # bl_space_type = "PROPERTIES"
    # bl_region_type = "WINDOW"
    # bl_context = "render"
    # bl_label = "Selection"
    # bl_parent_id = "CAPSULE_PT_Header"

    def draw(self, context):

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        scn = context.scene.CAPScn
        
        layout = self.layout
        
        # UI Prompt for when the .blend Capsule data can no longer be found.
        try:
            cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile
        except KeyError:
            Draw_CreateCapsuleData(layout)
            return

        if scn.is_pack_script_scene == True:
            self.draw_pack_script(context, layout)
        else:
            self.draw_selection(context, layout)


    def draw_selection(self, context, layout):

        gr = None
        
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        scn = context.scene.CAPScn

        proxy = context.scene.CAPProxy
        selectTab = int(str(scn.selection_switch))
        col_selection_title_tab = layout.row(align= True)
        col_selection_title_tab.prop(scn, "selection_switch", expand= True)

        if selectTab == 1:
            # Get the currently active object, whatever that might be.
            obj = None
            ob = None

            if context.active_object is not None:
                obj = context.active_object.CAPObj
                ob = context.active_object

            elif len(context.selected_objects) > 0:
                obj = context.selected_objects[0].CAPObj
                ob = context.selected_objects[0]

            # Now we can build the UI
            if ob != None:
                
                selection_label = ""
                edit_enable_list = False

                # LABEL - If we only have one object
                if len(context.selected_objects) == 1 or (context.active_object is not None and len(context.selected_objects) == 0):
                    selection_label = ob.name

                # LABEL - If we have MORE THAN ONE OBJECT
                elif len(context.selected_objects) > 1:
                    object_count = 0
                    selected = []

                    for sel in context.selected_objects:
                        object_count += 1
                        selected.append(sel)

                    edit_enable_list = True
                    selection_label = tr("{count} objects selected", count = object_count)
                
                # No dropdown, indicate objects to be edited
                if addon_prefs.edit_enable_dropdown is False:
                    col_selection_item_box = layout.box()
                    col_edit_indicator = col_selection_item_box.row(align= True)

                    col_edit_indicator.prop(addon_prefs, "edit_enable_dropdown", text= "", icon= 'TRIA_RIGHT', emboss= False)
                    col_edit_indicator.alignment = 'EXPAND'
                    col_edit_indicator.label(text=selection_label, icon = "OBJECT_DATA")

                # Dropdown active, multiple objects selected.
                elif edit_enable_list is True:
                    col_selection_item_box = layout.box()
                    col_edit_indicator = col_selection_item_box.row(align= True)

                    col_edit_indicator.prop(addon_prefs, "edit_enable_dropdown", text= "", icon= 'TRIA_DOWN', emboss= False)
                    col_edit_indicator.alignment = 'EXPAND'
                    col_edit_indicator.label(text=selection_label, icon = "OBJECT_DATA")
                    col_edit_list = col_selection_item_box.column(align= True)

                    for item in context.selected_objects:
                        item_label = tr("Edit {name}", name = item.name)
                        col_edit_list.prop(item.CAPObj, 'enable_edit', text=item_label)

                # Only one object selected, no need to show the list.
                else:
                    col_selection_item_box = layout.box()
                    col_edit_indicator = col_selection_item_box.row(align= True)

                    col_edit_indicator.prop(addon_prefs, "edit_enable_dropdown", text= "", icon= 'TRIA_DOWN', emboss= False)
                    col_edit_indicator.alignment = 'EXPAND'
                    col_edit_indicator.label(text=selection_label, icon = "OBJECT_DATA")
                    

            if ob != None:

                # now build the UI with that proxy
                obj_settings = layout.column(align= False)
                obj_settings.use_property_split = True
                obj_settings.use_property_decorate = False
                obj_settings.separator()

                obj_settings.prop(proxy, "obj_enable_export")
                obj_settings.separator()
                obj_settings.prop(proxy, "obj_origin_point")
                obj_settings.separator()
                obj_settings.prop(proxy, "obj_object_children")
                obj_settings.separator()
                obj_settings.prop(proxy, "obj_location_preset")
                obj_settings.separator()
                obj_settings.prop(proxy, "obj_export_preset")
                obj_settings.separator()

                if addon_prefs.use_pack_scripts:
                    obj_settings.prop(proxy, "obj_pack_script")
                    obj_settings.separator()

                export_options = layout.column(align = True)
                smart_export = export_options.operator("scene.cap_export",
                    text = tr("Modifier Smart Apply Export"), icon = "MODIFIER")
                smart_export.set_mode = 'ALL'
                smart_export.smart_modifiers = True
                export_options.operator("scene.cap_export", text = tr("Export Selected"), icon = "EXPORT").set_mode = 'SELECTED_OBJECTS'

                if addon_prefs.use_pack_scripts:
                    export_options.separator()
                    export_options.operator("cap.packscript_create_test", icon = "RIGHTARROW_THIN").set_mode = 'ACTIVE_OBJECT'
                
                export_options.separator()
                export_options.operator("scene.cap_show_preferences", icon = "PREFERENCES")

            # If no object was eventually found, bring up warning labels.
            else:
                object_info = layout.column(align= True)
                object_info.separator()
                object_info.label(text= tr("No objects selected."))

            layout.separator()


        #/////////////////////////////////////////////////////////////////
        #////////////////////////// COLLECTION UI /////////////////////////////
        #/////////////////////////////////////////////////////////////////
        elif selectTab == 2:
            
            # TODO : Rename these awful variable names
            # Get the first collection pointer we need
            grp = None


            collections = collection_utils.GetSelectedCollections()
            if len(collections) != 0:
                grp = collections[0]

            if len(collections) > 0:
                selection_label = ""
                edit_enable_list = False

                # LABEL - If we only have one collection
                if len(collections) == 1:
                    selection_label = collections[0].name

                elif len(collections) > 1:
                    edit_enable_list = True
                    selection_label = tr("{count} collections selected", count = len(collections))

                if context.active_object is not None:
                    if len(context.active_object.users_collection) > 0:
                        for collection in context.active_object.users_collection:
                            gr = collection
                            grp = collection.CAPCol
                            break
                
                # Failsafe if we didn't find a collection label by now.
                if gr is not None and len(collections) == 0:
                    selection_label = gr.name + " collection selected."

                # If we have one, we can continue onwards!
                if selection_label != "":
                    
                    # No dropdown, indicate objects to be edited
                    if addon_prefs.edit_enable_dropdown is False:
                        col_selection_item_box = layout.box()
                        col_edit_indicator = col_selection_item_box.row(align= True)

                        col_edit_indicator.prop(addon_prefs, "edit_enable_dropdown", text= "", icon= 'TRIA_RIGHT', emboss= False)
                        col_edit_indicator.alignment = 'EXPAND'
                        col_edit_indicator.label(text=selection_label, icon = "MOD_ARRAY")
                    
                    # Dropdown active, multiple objects selected.
                    elif edit_enable_list is True:
                        col_selection_item_box = layout.box()
                        col_edit_indicator = col_selection_item_box.row(align= True)

                        col_edit_indicator.prop(addon_prefs, "edit_enable_dropdown", text= "", icon= 'TRIA_DOWN', emboss= False)
                        col_edit_indicator.alignment = 'EXPAND'
                        col_edit_indicator.label(text=selection_label, icon = "MOD_ARRAY")
                        col_edit_list = col_selection_item_box.column(align= True)

                        for item in collections:
                            item_label = tr("Edit {name}", name = item.name)
                            col_edit_list.prop(item.CAPCol, 'enable_edit', text=item_label)

                    # Only one object selected, no need to show the list.
                    else:
                        col_selection_item_box = layout.box()
                        col_edit_indicator = col_selection_item_box.row(align= True)

                        col_edit_indicator.prop(addon_prefs, "edit_enable_dropdown", text= "", icon= 'TRIA_DOWN', emboss= False)
                        col_edit_indicator.alignment = 'EXPAND'
                        col_edit_indicator.label(text=selection_label, icon = "MOD_ARRAY")



            #Get the collection so we can obtain preference data from it
            #With Multi-Edit, we have to find a flexible approach to obtaining collection data
            if grp != None:

                # now build the UI with that proxy
                group_layout = layout.column(align= False)
                group_layout.use_property_split = True
                group_layout.use_property_decorate = False
                group_layout.separator()

                group_layout.prop(proxy, "col_enable_export")
                group_layout.separator()

                root_object_ui = group_layout.column(align= True)
                root_object_ui.prop(proxy, "col_origin_point")

                if proxy.col_origin_point == 'Object':
                    root_object_ui.prop(proxy, "col_root_object", text= " ")
                
                root_object_ui.separator()

                # group_layout.prop(proxy, "col_object_children")
                # group_layout.separator()
                group_layout.prop(proxy, "col_collection_children")
                group_layout.separator()
                group_layout.prop(proxy, "col_location_preset") 
                group_layout.separator()
                group_layout.prop(proxy, "col_export_preset")
                group_layout.separator()

                if addon_prefs.use_pack_scripts:
                    group_layout.prop(proxy, "col_pack_script")
                    group_layout.separator()

                export_options = layout.column(align = True)
                smart_export = export_options.operator("scene.cap_export",
                    text = tr("Modifier Smart Apply Export"), icon = "MODIFIER")
                smart_export.set_mode = 'ALL'
                smart_export.smart_modifiers = True
                export_options.operator("scene.cap_export", text = tr("Export Selected"), icon = "EXPORT").set_mode = 'SELECTED_COLLECTIONS'

                if addon_prefs.use_pack_scripts:
                    export_options.separator()
                    export_options.operator("cap.packscript_create_test", icon = "RIGHTARROW_THIN").set_mode = 'ACTIVE_COLLECTION'
                
                export_options.separator()
                export_options.operator("scene.cap_show_preferences", icon = "PREFERENCES")

            # If no collection was eventually found, bring up warning labels.
            else:
                collection_info = layout.column(align= True)
                collection_info.separator()
                collection_info.label(text= tr("No collections selected."))

            layout.separator()
        
    def draw_pack_script(self, context, layout):
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        scn = context.scene.CAPScn

        proxy = context.scene.CAPProxy
        selectTab = int(str(scn.selection_switch))

        pack_ui = layout.column(align = True)
        pack_ui.use_property_split = True
        pack_ui.use_property_decorate = False
        pack_ui.separator()

        pack_status = pack_ui.box()
        if scn.is_pack_script_successful is True:
            pack_status.label(text = tr("Pack Script executed successfully!"))
            pack_status.label(text = tr("Check the results in the Result Collection."))
            pack_ui.separator()
            pack_ui.separator()

        else:
            pack_status.label(text = tr("Pack Script FAILED."))
            pack_status.label(text = tr("Retry the test to see the error message again."))
            pack_ui.separator()
            pack_ui.separator()

        pack_ui.prop(scn, "test_pack_script")
        pack_ui.separator()
        pack_ui.separator()
        pack_ui.operator("cap.packscript_retry_test", icon = "FILE_REFRESH")
        pack_ui.operator("cap.packscript_destroy_test", icon = "TRASH")
        
        


class CAPSULE_PT_List(Panel):
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_label = "Export List"
    bl_parent_id = "CAPSULE_PT_Header"

    # @classmethod
    # def poll(cls, context):
    #     preferences = context.preferences
    #     addon_prefs = preferences.addons[__package__].preferences
    #     try:
    #         cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile
    #     except KeyError:
    #         return False
    #     return True

    def draw(self, context):
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        scn = context.scene.CAPScn

        layout = self.layout

        try:
            cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile
        except KeyError:
            Draw_CreateCapsuleData(layout)
            return

        list_tab = int(str(scn.list_switch))

        list_switch = layout.row(align= True)
        list_switch.prop(scn, "list_switch", expand= True)

        col_location = layout.column(align= True)

        if list_tab == 1:
            col_location.template_list("CAPSULE_UL_Object", "rawr", 
                                       scn, "object_list", 
                                       scn, "object_list_index", rows=3, maxrows=10)
        elif list_tab == 2:
            col_location.template_list("CAPSULE_UL_Collection", "rawr", 
                                       scn, "collection_list", 
                                       scn, "collection_list_index", rows=3, maxrows=10)

        search_row = layout.row(align = True)

        if list_tab == 1:
            search_row.prop(scn, "object_list_filter", text = "", icon = 'VIEWZOOM')
            if scn.object_list_filter:
                search_row.operator("scene.cap_clear_list_filter",
                    text = "", icon = 'X').filter_type = 'OBJECT'
        else:
            search_row.prop(scn, "collection_list_filter", text = "", icon = 'VIEWZOOM')
            if scn.collection_list_filter:
                search_row.operator("scene.cap_clear_list_filter",
                    text = "", icon = 'X').filter_type = 'COLLECTION'

        col_location_options = layout.row(align = True)

        if list_tab == 2:
            col_location_options.menu("CAPSULE_MT_Add_Collections", text = "", icon = 'ADD')
            col_location_options.menu("CAPSULE_MT_Copy_Collection_Settings", text = "", icon = 'COPYDOWN')

        col_location_options.operator("scene.cap_clearlist", icon = "X")
        col_location_options.operator("scene.cap_refreshlist", icon = "FILE_REFRESH")

        if list_tab == 2 and scn.bulk_add_active:
            Draw_CollectionBatchAdd(context, layout)

        export_options = layout.column(align = True)
        
        smart_export = export_options.operator("scene.cap_export",
            text = tr("Modifier Smart Apply Export"), icon = "MODIFIER")
        smart_export.set_mode = 'ALL'
        smart_export.smart_modifiers = True
        export_options.operator("scene.cap_export", text = tr("Export Selected In List"), icon = "EXPORT").set_mode = 'ACTIVE_LIST'
        export_options.separator()
        export_options.operator("scene.cap_show_preferences", icon = "PREFERENCES")
        
        export_options.separator()


        # TODO REALLY IMPORTANT: List selections can no longer rely on the object being available.

        if list_tab == 1:
            obj = None
            ob = None

            if len(scn.object_list) != 0:
                index = min(max(scn.object_list_index, 0), len(scn.object_list) - 1)
                entry = scn.object_list[index]
                ob = entry.object if entry.object is not None else None
            
            if ob != None:
                obj = entry.object.CAPObj
                object_options_list = layout.column(align= False)
                object_options_list.use_property_split = True
                object_options_list.use_property_decorate = False
                object_options_list.separator()

                object_options_list.prop(obj, "origin_point")
                object_options_list.separator()
                object_options_list.prop(obj, "object_children")
                object_options_list.separator()
                object_options_list.prop(obj, "location_preset")
                object_options_list.separator()
                object_options_list.prop(obj, "export_preset")

                if addon_prefs.use_pack_scripts:
                    object_options_list.separator()
                    object_options_list.prop(obj, "pack_script")
        
        # Group selection
        elif list_tab == 2:
            grp = None 
            gr = None

            if len(scn.collection_list) > 0:
                index = min(max(scn.collection_list_index, 0), len(scn.collection_list) - 1)
                entry = scn.collection_list[index]

                if entry.collection is not None:
                    grp = entry.collection.CAPCol
                    gr = entry.collection
                        
            
            if gr is not None:
                group_options_list = layout.column(align= False)
                group_options_list.use_property_split = True
                group_options_list.use_property_decorate = False
                group_options_list.separator()
                
                root_object_ui = group_options_list.column(align= True)
                root_object_ui.prop(grp, "origin_point")

                if grp.origin_point == 'Object':
                    root_object_ui.prop(grp, "root_object", text= " ")
                
                root_object_ui.separator()

                # group_options_list.prop(grp, "object_children")
                # group_options_list.separator()
                group_options_list.prop(grp, "collection_children")
                group_options_list.separator()
                group_options_list.prop(grp, "location_preset")
                group_options_list.separator()
                group_options_list.prop(grp, "export_preset")

                if addon_prefs.use_pack_scripts:
                    group_options_list.separator()
                    group_options_list.prop(grp, "pack_script")
                    

        layout.separator()


class CAPSULE_PT_Location(Panel):
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_label = "Export Locations"
    bl_parent_id = "CAPSULE_PT_Header"

    # @classmethod
    # def poll(cls, context):
    #     preferences = context.preferences
    #     addon_prefs = preferences.addons[__package__].preferences

    #     try:
    #         cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile
    #     except KeyError:
    #         return False
    #     return True

    def draw(self, context):

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        layout = self.layout

        # UI Prompt for when the .blend Capsule data can no longer be found.
        try:
            cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile
        except KeyError:
            Draw_CreateCapsuleData(layout)
            return

        
        cap_file = bpy.data.objects[addon_prefs.default_datablock].CAPFile
        scn = context.scene.CAPScn
        ob = context.object

        col_location = layout.row(align= True)
        col_location.template_list("CAPSULE_UL_Path_Default", "default", cap_file, "location_presets", cap_file, "location_presets_listindex", rows=3, maxrows=6)

        col_location.separator()

        row_location = col_location.column(align= True)
        row_location.operator("scene.cap_addpath", text= "", icon = "ADD")
        row_location.operator("scene.cap_deletepath", text= "", icon = "REMOVE")

        location_options = layout.column(align= False)
        location_options.use_property_split = True
        location_options.use_property_decorate = False
        location_options.separator()

        count = 0
        for i, item in enumerate(cap_file.location_presets, 1):
            count += 1

        if cap_file.location_presets_listindex > -1 and cap_file.location_presets_listindex < count:
            location_options.prop(cap_file.location_presets[cap_file.location_presets_listindex], "path")
            location_options.operator_menu_enum("scene.cap_add_file_location_tag", "path_tags")



def Draw_CreateCapsuleData(layout):

    # UI Prompt for when the .blend Capsule data can no longer be found.
    col_export = layout.column(align= True)
    col_export.label(text= tr("No Capsule for this .blend file has been found,"))
    col_export.label(text= tr("Please press the button below to generate new data."))
    col_export.separator()
    col_export.separator()
    col_export.operator("cap.exportdata_create")
    col_export.separator()
    return
