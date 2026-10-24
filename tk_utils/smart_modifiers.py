# ///////////////////////////////////////////////////////////////////
# Temporarily disables expensive modifiers while Capsule exports.
# ///////////////////////////////////////////////////////////////////

# Modifiers that become expensive when every object in a large scene keeps
# them live.  Their evaluated result is only needed for the objects that are
# part of the export task that is currently being written.
SMART_MODIFIER_TYPES = frozenset(('DECIMATE', 'DATA_TRANSFER'))


class SmartModifierState:
    """
    Records the viewport/render visibility of expensive modifiers, turns all
    of them off, and re-enables only the ones that belong to the current
    export task.

    Every modifier is switched off when the state is created, so building the
    export task list and exporting the first task do not evaluate modifiers for
    the rest of the scene.  ``enable_for_objects`` restores the recorded
    visibility for one task, ``disable_all`` switches that task's modifiers off
    again, and ``restore_all`` puts the scene back exactly as it was.

    The original values are preserved instead of forcing every modifier on, so
    an object whose modifier was deliberately disabled before the export is
    exported exactly as it would be without this feature.
    """

    def __init__(self, scene):
        self._records = []
        self._records_by_object = {}
        self._live_records = []
        self._scan(scene)
        self._disable_initial()

    # ------------------------------------------------------------------
    # recording
    # ------------------------------------------------------------------

    def _scan(self, scene):
        for obj in scene.objects:
            try:
                if obj.type != 'MESH':
                    continue
            except ReferenceError:
                continue

            object_pointer = self._object_pointer(obj)
            if object_pointer is None:
                continue

            try:
                modifiers = obj.modifiers
            except ReferenceError:
                continue

            for modifier in modifiers:
                try:
                    modifier_type = modifier.type
                except ReferenceError:
                    continue

                if modifier_type not in SMART_MODIFIER_TYPES:
                    continue

                try:
                    show_viewport = bool(modifier.show_viewport)
                    show_render = bool(modifier.show_render)
                except (AttributeError, ReferenceError, TypeError):
                    continue

                record = {
                    'modifier': modifier,
                    'show_viewport': show_viewport,
                    'show_render': show_render,
                    'object_pointer': object_pointer,
                    'source_pointer': None,
                    'live': False,
                }

                # A Data Transfer modifier reads the evaluated mesh of its
                # source object.  Remember that link so the source object can
                # be made live for the task as well, keeping its own heavy
                # modifiers from silently changing the exported result.
                if modifier_type == 'DATA_TRANSFER':
                    try:
                        source = modifier.source_object
                    except (AttributeError, ReferenceError):
                        source = None
                    record['source_pointer'] = self._object_pointer(source)

                self._records.append(record)
                self._records_by_object.setdefault(object_pointer, []).append(record)

    @staticmethod
    def _object_pointer(obj):
        if obj is None:
            return None
        try:
            return obj.as_pointer()
        except (AttributeError, ReferenceError):
            return None

    # ------------------------------------------------------------------
    # applying state
    # ------------------------------------------------------------------

    def _disable_initial(self):
        """Turns every recorded modifier off before the first task starts."""
        for record in self._records:
            # The modifier was already off before the export started.  Leave
            # it alone: writing RNA properties tags the depsgraph for no gain.
            if record['show_viewport'] or record['show_render']:
                self._set(record, False, False)

    def disable_all(self):
        """Turns off the modifiers that the last task made live."""
        for record in self._live_records:
            self._set(record, False, False)
            record['live'] = False
        self._live_records.clear()

    def enable_for_objects(self, objects):
        """
        Restores the recorded modifier visibility for ``objects``.

        Heavy modifiers on a Data Transfer source object are restored too,
        recursively, because the source mesh is evaluated as part of the
        target modifier.
        """
        pending = list(self._object_pointers(objects))
        visited = set()

        while pending:
            object_pointer = pending.pop()
            if object_pointer in visited:
                continue
            visited.add(object_pointer)

            for record in self._records_by_object.get(object_pointer, ()):
                self._set(record,
                    record['show_viewport'],
                    record['show_render'])

                if (record['show_viewport'] or record['show_render']) and not record['live']:
                    record['live'] = True
                    self._live_records.append(record)

                # Only follow the source link when the transfer is actually
                # live; otherwise its source mesh is not evaluated at all.
                source_pointer = record['source_pointer']
                if source_pointer is None:
                    continue
                if not (record['show_viewport'] or record['show_render']):
                    continue
                if source_pointer not in visited:
                    pending.append(source_pointer)

    def restore_all(self):
        """Restores the modifier visibility recorded when the export started."""
        for record in self._records:
            record['live'] = False
            self._set(record,
                record['show_viewport'],
                record['show_render'])
        self._live_records.clear()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _object_pointers(self, objects):
        pointers = set()
        for obj in objects:
            pointer = self._object_pointer(obj)
            if pointer is not None:
                pointers.add(pointer)
        return pointers

    @staticmethod
    def _set(record, show_viewport, show_render):
        modifier = record.get('modifier')
        if modifier is None:
            return

        try:
            if modifier.show_viewport != show_viewport:
                modifier.show_viewport = show_viewport
        except ReferenceError:
            # The modifier was removed, for example by a Pack Script.
            record['modifier'] = None
            return
        except (AttributeError, TypeError, RuntimeError):
            pass

        try:
            if modifier.show_render != show_render:
                modifier.show_render = show_render
        except ReferenceError:
            record['modifier'] = None
        except (AttributeError, TypeError, RuntimeError):
            pass
