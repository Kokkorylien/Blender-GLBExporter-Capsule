import bpy
from math import *

from ..tk_utils import select as select_utils
from ..tk_utils import object_ops
from ..tk_utils import search as search_utils

# OBJECT LIST PROPERTIES
# /////////////////////////////////////////////////
# /////////////////////////////////////////////////


def UpdateObjectList(scene, object, enableExport):
    """
    Used when properties are updated outside the scope of the Export List
    to ensure that all UI elements are kept in sync.
    """
    scn = scene.CAPScn
    #print("Hey, this object is %s" % object)

    if object is None:
        return

    # Check a list entry for the object doesn't already exist.
    for item in scene.CAPScn.object_list:
        if item.object.name == object.name:
            #print("Changing", object.name, "'s export from list.'")
            item.enable_export = enableExport
            return

    # If an entry couldn't be found in the list, add it.
    if enableExport is True:
        #print("Adding", object.name, "to list.")
        entry = scn.object_list.add()
        entry.object = object
        entry.enable_export = enableExport

        object.CAPObj.in_export_list = True

    return None

def CAP_Update_FocusObject(self, context):
    """
    Focuses the camera to a particular object, ensuring the object is clearly within the camera frame.  
    """

    preferences = context.preferences
    addon_prefs = preferences.addons['Capsule'].preferences
            
    bpy.ops.object.select_all(action= 'DESELECT')
    select_utils.SelectObject(self.object)

    override = object_ops.Find3DViewContext()
    
    with context.temp_override(window = override['window'], area = override['area'], 
            region = override['region']):

            bpy.ops.view3d.view_selected()

    return None


def CAP_Update_SelectObject(self, context):
    """
    Selects (but doesn't focus) the given object.
    """

    bpy.ops.object.select_all(action= 'DESELECT')
    select_utils.ActivateObject(self.object)
    select_utils.SelectObject(self.object)

    return None



def CAP_Update_ObjectListExport(self, context):
    """
    Updates the "Enable Export" object status once changed from the list menu.
    Note - Do not use this in any other place apart from when an object is represented in a list.
    """

    self.object.CAPObj.enable_export = self.enable_export
    
    # TODO / WARNING
    # If the object is the active selection we should really change the proxy so it fits right?
    proxy = context.scene.CAPProxy



    return None


def CAP_Update_ObjectListRemove(self, context):
    """
    Used in a list to remove an object from both the export list, while disabling it's "Enable Export" status.
    """
    
    scn = context.scene.CAPScn
    object_list = context.scene.CAPScn.object_list

    # To avoid issues within the list, the selected list item needs to be preserved.
    backupListIndex = scn.object_list_index
    backupListLength = len(object_list)

    # TODO: Ensure it can handle deleted objects!

    # Remove it as an export candidate
    if self.object != None:
        self.object.CAPObj.enable_export = False
        self.object.CAPObj.in_export_list = False
    
    # Find the index and remove it from the list
    # TODO: There's probably a more efficient way right?
    i = None
    try:
        i = object_list.values().index(self)
        object_list.remove(i)

    except ValueError:
        return
    
    # If the index is more than the list, bring it down one
    if scn.object_list_index > i:
        scn.object_list_index -= 1

    return
                

            


# COLLECTION LIST PROPERTIES
# /////////////////////////////////////////////////
# /////////////////////////////////////////////////

def UpdateCollectionList(scene, collection, enableExport):
    """
    Used when properties are updated outside the scope of the Export List
    to ensure that all UI elements are kept in sync.
    """
    scn = scene.CAPScn

    if collection is None:
        return

    # Check a list entry for the collection doesn't already exist.
    # Collection pointers are used instead of names so renamed collections
    # cannot create duplicate entries.
    for item in scene.CAPScn.collection_list:
        if item.collection == collection:
            item.enable_export = enableExport
            return

    if enableExport is True:
        entry = scn.collection_list.add()
        entry.collection = collection
        entry.enable_export = enableExport
        collection.CAPCol.in_export_list = True


def CAP_Update_FocusCollection(self, context):

    """
    Focuses the camera to a particular collection, moving it to ensure all objects are in the frame and can be seen clearly.
    TODO 2.0: The camera movement interpolation no longer works.
    """

    if self.collection is None:
        return None

    bpy.ops.object.select_all(action= 'DESELECT')

    for object in self.collection.objects:
        object.select_set(True)
        bpy.context.view_layer.objects.active = object

    override = object_ops.Find3DViewContext()
    
    with context.temp_override(window = override['window'], area = override['area'], 
            region = override['region']):

            bpy.ops.view3d.view_selected()

    return None

def CAP_Update_SelectCollection(self, context):

    """
    Selects (but doesn't focus) the given collection.
    """

    if self.collection is None:
        return None

    bpy.ops.object.select_all(action= 'DESELECT')

    for object in self.collection.objects:
        object.select_set(True)
        bpy.context.view_layer.objects.active = object

    return None


def CAP_Update_CollectionListExport(self, context):
    """
    Updates the "Enable Export" collection status once changed from the list menu.
    Note - Do not use this in any other place apart from when an object is represented in a list.
    """

    if self.collection is None:
        return None

    self.collection.CAPCol.enable_export = self.enable_export
    return None


def CAP_Update_CollectionListRemove(self, context):
    """
    Used in a list to remove a collection from both the export list, while disabling it's "Enable Export" status.
    """

    scn = context.scene.CAPScn
    collection_list = scn.collection_list

    # Disable the collection before the list entry disappears.
    if self.collection is not None:
        self.collection.CAPCol.enable_export = False
        self.collection.CAPCol.in_export_list = False

    # Find the entry that triggered the update.  Identity is used because the
    # collection pointer can be None for deleted collections.
    index = -1
    for i, item in enumerate(collection_list):
        if item == self:
            index = i
            break
        if item.collection is not None and item.collection == self.collection:
            index = i
            break

    if index == -1:
        return

    collection_list.remove(index)

    # Keep the selected index within the list bounds.
    if scn.collection_list_index > index:
        scn.collection_list_index -= 1

    if scn.collection_list_index >= len(collection_list):
        scn.collection_list_index = max(0, len(collection_list) - 1)


# BATCH COLLECTION ADD
# /////////////////////////////////////////////////
# /////////////////////////////////////////////////

def GetSelectedCollectionListEntry(context):
    """
    Returns the currently selected Export List collection entry, or None when
    the list is empty or the entry points to a deleted collection.
    """

    scn = context.scene.CAPScn

    if len(scn.collection_list) == 0:
        return None

    index = min(max(scn.collection_list_index, 0), len(scn.collection_list) - 1)
    entry = scn.collection_list[index]

    if entry.collection is None:
        return None

    return entry


def GetCollectionSettingsTemplate(context):
    """
    Returns the export settings of the currently selected Export List entry as
    a dictionary, so batch-added collections can copy them in one go.
    """

    entry = GetSelectedCollectionListEntry(context)
    if entry is None:
        return None

    collection = entry.collection.CAPCol

    return {
        'origin_point': collection.origin_point,
        'root_object': collection.root_object,
        'object_children': collection.object_children,
        'collection_children': collection.collection_children,
        'location_preset': collection.location_preset,
        'export_preset': collection.export_preset,
        'pack_script': collection.pack_script,
    }


def _SetCollectionEnum(collection, attribute, value, fallback):
    """
    Sets an enum property, falling back when the stored identifier no longer
    exists (for example after an export preset was deleted).
    """

    try:
        setattr(collection, attribute, value)
    except (TypeError, ValueError):
        setattr(collection, attribute, fallback)


def ApplyCollectionSettingsTemplate(collection, template):
    """
    Copies a settings template (see GetCollectionSettingsTemplate) onto the
    given collection.
    """

    if collection is None or template is None:
        return

    target = collection.CAPCol

    _SetCollectionEnum(target, 'origin_point', template.get('origin_point', 'Scene'), 'Scene')
    target.root_object = template.get('root_object')
    _SetCollectionEnum(target, 'object_children', template.get('object_children', 'All'), 'All')
    _SetCollectionEnum(target, 'collection_children', template.get('collection_children', 'All'), 'All')
    _SetCollectionEnum(target, 'location_preset', template.get('location_preset', '0'), '0')
    _SetCollectionEnum(target, 'export_preset', template.get('export_preset', '0'), '0')
    target.pack_script = template.get('pack_script')


def ApplyCollectionTemplateToEntries(context, filtered_only = False):
    """
    Copies the settings of the currently selected Export List entry onto the
    other entries in the collection list.  When filtered_only is True, only
    entries matching the collection list search are updated.

    Returns the number of entries that were updated.
    """

    scn = context.scene.CAPScn
    source = GetSelectedCollectionListEntry(context)

    if source is None:
        return 0

    template = GetCollectionSettingsTemplate(context)

    if template is None:
        return 0

    pattern = scn.collection_list_filter if filtered_only else ""
    updated = 0

    for item in scn.collection_list:
        if item.collection is None or item.collection == source.collection:
            continue

        if filtered_only and not search_utils.NameMatches(item.collection.name, pattern):
            continue

        ApplyCollectionSettingsTemplate(item.collection, template)
        updated += 1

    return updated


def BulkAddCollections(context, collections, template = None, skip_covered_children = False):
    """
    Adds a batch of collections to the Export List in a single pass.

    Existing entries are never duplicated and are counted as skipped.  The
    selected list index is moved to the first newly added entry.

    Returns (added, skipped).
    """

    scn = context.scene.CAPScn
    master_collection = context.scene.collection

    existing = {}
    for item in scn.collection_list:
        if item.collection is not None:
            existing[item.collection] = item

    parents = search_utils.GetCollectionParentMap(master_collection) if skip_covered_children else {}

    def IsCoveredByListedParent(collection):
        parent = parents.get(collection)

        while parent is not None:
            if parent in existing and parent.CAPCol.collection_children == 'All':
                return True
            parent = parents.get(parent)

        return False

    added = 0
    skipped = 0
    seen = set()
    first_new_index = None

    for collection in collections:
        if collection is None or collection in seen:
            continue

        seen.add(collection)

        # The master collection, linked collections and library overrides
        # cannot be exported or edited by Capsule.
        if (collection == master_collection
                or collection.library is not None
                or collection.override_library is not None):
            skipped += 1
            continue

        if collection in existing:
            skipped += 1
            continue

        if skip_covered_children and IsCoveredByListedParent(collection):
            skipped += 1
            continue

        entry = scn.collection_list.add()
        entry.collection = collection
        entry.enable_export = True

        collection.CAPCol.in_export_list = True

        if template is not None:
            ApplyCollectionSettingsTemplate(collection, template)

        existing[collection] = entry

        if first_new_index is None:
            first_new_index = len(scn.collection_list) - 1

        added += 1

    if first_new_index is not None:
        scn.collection_list_index = first_new_index

    return added, skipped


def GetCollectionsForMode(context, mode):
    """
    Returns the collections addressed by one of the batch add modes.
    """

    scene = context.scene
    master_collection = scene.collection

    layer_collection = getattr(context, 'layer_collection', None)
    active_collection = layer_collection.collection if layer_collection is not None else None

    if mode == 'ACTIVE':
        if active_collection is None or active_collection == master_collection:
            return []
        return [active_collection]

    if mode == 'ACTIVE_RECURSIVE':
        if active_collection is None or active_collection == master_collection:
            return []
        children = [collection for collection, depth in search_utils.GetCollectionTree(active_collection)]
        return [active_collection] + children

    if mode == 'SELECTED_OBJECTS':
        # GetSelectedCollections falls back to the active collection when no
        # objects are selected, which is not what this menu entry promises.
        if len(context.selected_objects) == 0:
            return []

        return [collection for collection in search_utils.GetSelectedCollections()
                if collection != master_collection]

    tree = [collection for collection, depth in search_utils.GetCollectionTree(master_collection)]

    if mode == 'ALL_WITH_OBJECTS':
        return [collection for collection in tree if len(collection.all_objects) > 0]

    return tree


def ResolveBatchCollectionTemplate(context):
    """
    Returns the settings template used by the batch picker.  The selected list
    entry wins over the explicit batch settings, matching the picker's
    "Copy Settings From Selected Entry" default.
    """

    scn = context.scene.CAPScn

    if not scn.bulk_apply_settings:
        return None

    if scn.bulk_copy_from_selected:
        template = GetCollectionSettingsTemplate(context)
        if template is not None:
            return template

    return {
        'origin_point': scn.bulk_origin_point,
        'root_object': scn.bulk_root_object,
        'object_children': 'All',
        'collection_children': scn.bulk_collection_children,
        'location_preset': scn.bulk_location_preset,
        'export_preset': scn.bulk_export_preset,
        'pack_script': None,
    }


def RebuildCollectionCandidates(context):
    """
    Rebuilds the collection picker from the current scene's collection tree.
    """

    scn = context.scene.CAPScn
    scn.bulk_candidates.clear()
    scn.bulk_candidates_index = 0

    existing = set()
    for item in scn.collection_list:
        if item.collection is not None:
            existing.add(item.collection)

    for collection, depth in search_utils.GetCollectionTree(context.scene.collection):
        if collection.library is not None or collection.override_library is not None:
            continue

        item = scn.bulk_candidates.add()
        item.collection = collection
        item.depth = depth
        item.already_added = collection in existing
        item.add = not item.already_added

    return len(scn.bulk_candidates)


def CountSelectedCollectionCandidates(scn):
    """
    Returns how many picker entries would actually be added.
    """

    count = 0

    for item in scn.bulk_candidates:
        if item.add and item.collection is not None and not item.already_added:
            count += 1

    return count