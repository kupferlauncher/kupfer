import itertools
import os
from os import path

from gi.repository import GLib

from kupfer import datatools
from kupfer import icons
from kupfer import utils

from kupfer.obj.base import Source
from kupfer.obj.helplib import PicklingHelperMixin, FilesystemWatchMixin
from kupfer.obj.objects import FileLeaf, SourceLeaf
from kupfer.obj.objects import ConstructFileLeaf, ConstructFileLeafTypes

def _representable_fname(fname):
    "Return False if fname contains surrogate escapes"
    try:
        fname.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False

class FileSource (Source):
    def __init__(self, dirlist, depth=0):
        """
        @dirlist: Directories as byte strings
        """
        name = GLib.filename_display_basename(dirlist[0])
        if len(dirlist) > 1:
            name = _("%s et. al.") % name
        super(FileSource, self).__init__(name)
        self.dirlist = dirlist
        self.depth = depth

    def __repr__(self):
        return "%s.%s((%s, ), depth=%d)" % (self.__class__.__module__,
            self.__class__.__name__,
            ', '.join('"%s"' % d for d in sorted(self.dirlist)), self.depth)

    def get_items(self):
        iters = []
        
        def mkleaves(directory):
            files = utils.get_dirlist(directory, depth=self.depth,
                    exclude=self._exclude_file)
            return (ConstructFileLeaf(f) for f in files)

        for d in self.dirlist:
            iters.append(mkleaves(d))

        return itertools.chain(*iters)

    def should_sort_lexically(self):
        return True

    def _exclude_file(self, filename):
        return filename.startswith(".") 

    def get_description(self):
        return (_("Recursive source of %(dir)s, (%(levels)d levels)") %
                {"dir": self.name, "levels": self.depth})

    def get_icon_name(self):
        return "folder-saved-search"

    def provides(self):
        return ConstructFileLeafTypes()

class DirectorySource (Source, PicklingHelperMixin, FilesystemWatchMixin):
    def __init__(self, dir, show_hidden=False):
        # Use glib filename reading to make display name out of filenames
        # this function returns a `unicode` object
        name = GLib.filename_display_basename(dir)
        super(DirectorySource, self).__init__(name)
        self.directory = dir
        self.show_hidden = show_hidden

    def __repr__(self):
        return "%s.%s(\"%s\", show_hidden=%s)" % (self.__class__.__module__,
                self.__class__.__name__, str(self.directory), self.show_hidden)

    def initialize(self):
        self.monitor = self.monitor_directories(self.directory)

    def finalize(self):
        self.monitor = None

    def monitor_include_file(self, gfile):
        return self.show_hidden or not gfile.get_basename().startswith('.')

    def get_items(self):
        try:
            for fname in os.listdir(self.directory):
                if not _representable_fname(fname):
                    continue
                if self.show_hidden or not fname.startswith("."):
                    yield ConstructFileLeaf(path.join(self.directory, fname))
        except OSError as exc:
            self.output_error(exc)

    def should_sort_lexically(self):
        return True

    def _parent_path(self):
        return path.normpath(path.join(self.directory, path.pardir))

    def has_parent(self):
        return not path.samefile(self.directory , self._parent_path())

    def get_parent(self):
        if not self.has_parent():
            return super(DirectorySource, self).has_parent(self)
        return DirectorySource(self._parent_path())

    def get_description(self):
        return _("Directory source %s") % self.directory

    def get_gicon(self):
        return icons.get_gicon_for_file(self.directory)

    def get_icon_name(self):
        return "folder"

    def get_leaf_repr(self):
        if os.path.isdir(self.directory) and \
             os.path.samefile(self.directory, os.path.expanduser("~")):
            alias = _("Home Folder")
        else:
            alias = None
        return FileLeaf(self.directory, alias=alias)

    def provides(self):
        return ConstructFileLeafTypes()

class SourcesSource (Source):
    """ A source whose items are SourceLeaves for @source """
    def __init__(self, sources, name=None, use_reprs=True):
        if not name: name = _("Catalog Index")
        super(SourcesSource, self).__init__(name)
        self.sources = sources
        self.use_reprs = use_reprs

    def get_items(self):
        """Ask each Source for a Leaf substitute, else
        yield a SourceLeaf """
        for s in self.sources:
            yield (self.use_reprs and s.get_leaf_repr()) or SourceLeaf(s)

    def should_sort_lexically(self):
        return True

    def get_description(self):
        return _("An index of all available sources")

    def get_icon_name(self):
        return "kupfer-catalog"

class MultiSource (Source):
    """
    A source whose items are the combined items
    of all @sources
    """
    fallback_icon_name = "kupfer-catalog"
    def __init__(self, sources):
        super(MultiSource, self).__init__(_("Catalog"))
        self.sources = sources
    
    def is_dynamic(self):
        """
        MultiSource should be dynamic so some of its content
        also can be
        """
        return True

    def get_items(self):
        iterators = []
        ui = datatools.UniqueIterator(S.toplevel_source() for S in self.sources)
        for S in ui:
            it = S.get_leaves()
            iterators.append(it)

        return itertools.chain(*iterators)

    def get_description(self):
        return _("Root catalog")

