"""
This module contains Helper constructs

This module is a part of the program Kupfer, see the main program file for
more information.
"""

from gi.repository import Gio, GLib

from kupfer import pretty

class PicklingHelperMixin (object):
    """ This pickling helper will define __getstate__/__setstate__
    acting simply on the class dictionary; it is up to the inheriting
    class to set up:
    pickle_prepare:
        Modify the instance dict to remove any unpickleable attributes,
        the resulting dict will be pickled
    unpickle_finish:
        Finish unpickling by restoring nonpickled attributes from the
        saved class dict, or setting up change callbacks or similar
    """
    def pickle_prepare(self):
        pass
    def unpickle_finish(self):
        pass
    def __getstate__(self):
        """On pickle, getstate will call self.pickle_prepare(),
        then it will return the class' current __dict__
        """
        self.pickle_prepare()
        return self.__dict__

    def __setstate__(self, state):
        """On unpickle, setstate will restore the class' __dict__,
        then call self.unpickle_finish()
        """
        self.__dict__.update(state)
        self.unpickle_finish()

class NonpersistentToken (PicklingHelperMixin):
    """A token will keep a reference until pickling, when it is deleted"""
    def __init__(self, data):
        self.data = data
    def __bool__(self):
        return self.data
    def pickle_prepare(self):
        self.data = None

class FilesystemWatchMixin (object):
    """A mixin for Sources watching directories"""

    def monitor_directories(self, *directories, **kwargs):
        """Register @directories for monitoring;

        On changes, the Source will be marked for update.
        This method returns a monitor token that has to be
        stored for the monitor to be active.

        The token will be a false value if nothing could be monitored.

        Nonexisting directories are skipped, if not passing
        the kwarg @force
        """
        tokens = []
        force = kwargs.get('force', False)
        for directory in directories:
            gfile = Gio.File.new_for_path(directory)
            if not force and not gfile.query_exists():
                continue
            try:
                monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
            except GLib.GError as exc:
                pretty.print_debug(__name__, "FilesystemWatchMixin", exc)
                continue
            if monitor:
                monitor.connect("changed", self.__directory_changed)
                tokens.append(monitor)
        return NonpersistentToken(tokens)

    def monitor_include_file(self, gfile):
        """Return whether @gfile should trigger an update event
        by default, files beginning with "." are ignored
        """
        return not (gfile and gfile.get_basename().startswith("."))

    def __directory_changed(self, monitor, file1, file2, evt_type):
        if (evt_type in (Gio.FileMonitorEvent.CREATED,
                Gio.FileMonitorEvent.DELETED) and
                self.monitor_include_file(file1)):
            self.mark_for_update()

def reverse_action(action, rank=0):
    """Return a reversed version a three-part action

    @action: the action class
    @rank: the rank_adjust to give the reversed action

    A three-part action requires a direct object (item) and an indirect
    object (iobj).

    In general, the item must be from the Catalog, while the iobj can be
    from one, specified special Source. If this is used, and the action
    will be reversed, the base action must be the one specifying a
    source for the iobj. The reversed action will always take both item
    and iobj from the Catalog, filtered by type.

    If valid_object(iobj, for_leaf=None) is used, it will always be
    called with only the new item as the first parameter when reversed.
    """
    class ReverseAction (action):
        rank_adjust = rank
        def activate(self, leaf, iobj):
            return action.activate(self, iobj, leaf)
        def item_types(self):
            return action.object_types(self)
        def valid_for_item(self, leaf):
            try:
                return action.valid_object(self, leaf)
            except AttributeError:
                return True
        def object_types(self):
            return action.item_types(self)
        def valid_object(self, obj, for_item=None):
            return action.valid_for_item(self, obj)
        def object_source(self, for_item=None):
            return None
    ReverseAction.__name__ = "Reverse" + action.__name__
    return ReverseAction

