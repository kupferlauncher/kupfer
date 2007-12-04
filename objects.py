# -*- coding: UTF-8 -*-

"""
Actions, Leaves, Sources for
kupfer
ɹǝɟdnʞ

Copyright 2007 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
Released under GNU General Public License v2 (or any later version)
"""

import gobject
import gnomevfs
import itertools
from os import path

import utils

class Error (Exception):
	pass

class NoParent (Error):
	pass

class NoContent (Error):
	pass

class InvalidData (Error):
	"""The data is wrong for the given Leaf"""
	pass

class InvalidLeaf (Error):
	"""The Leaf passed to an Action is invalid"""
	pass

class KupferObject (object):
	"""
	Base class for Actions and Leaves
	"""
	icon_size = 96
	def __init__(self, name):
		self.name = name
	
	def __repr__(self):
		return "<%s %s at %x>" % (self.__class__.__name__, str(self), id(self))
	
	def __str__(self):
		return self.name

	def get_pixbuf(self):
		"""
		Return pixbuf icon representing object
		"""
		name = self.get_icon_name()
		if name:
			return utils.get_icon_for_name(name, self.icon_size)
		return None
	
	def get_icon_name(self):
		"""
		As an alternative to get_pixbuf, subclasses can simply
		define get_pixbuf_name to use the named icon
		"""
		return None


def aslist(seq):
	"""
	Make lists from sequences that are not lists or tuples

	For iterators, sets etc.
	"""
	if not isinstance(seq, type([])) and not isinstance(seq, type(())):
		seq = list(seq)
	return seq

class Leaf (KupferObject):
	def __init__(self, obj, value):
		super(Leaf, self).__init__(value)
		self.object = obj
		self.value = value
	
	def has_content(self):
		return False
	
	def content_source(self):
		raise NoContent

	def get_actions(self):
		return ()

class FileLeaf (Leaf):
	"""
	Represents one file
	"""
	def __new__(cls, obj, value):
		# check if it is a desktop file
		# shortcut for subclasses
		if cls is not FileLeaf:
			return super(FileLeaf, cls).__new__(cls, obj, value)
		root, ext = path.splitext(obj)
		if ext == ".desktop":
			try:
				return DesktopLeaf(obj, value)
			except InvalidData:
				pass
		return super(FileLeaf, cls).__new__(cls, obj, value)

	def _desktop_item(self, basename):
		from gnomedesktop import item_new_from_basename, LOAD_ONLY_IF_EXISTS
		return item_new_from_basename(basename, LOAD_ONLY_IF_EXISTS)

	def get_actions(self):
		acts = [Echo(), Dragbox()]
		default = None
		if path.isdir(self.object):
			acts.extend([OpenTerminal(), SearchInside()])
			default = OpenDirectory()
		else:
			type = gnomevfs.get_mime_type(self.object)
			def_app = gnomevfs.mime_get_default_application(type)
			types = gnomevfs.mime_get_all_applications(type)
			apps = set()
			if def_app:
				default = OpenWith(self._desktop_item(def_app[0]), def_app[1])
				apps.add(def_app[1])
			for info in types:
				id = info[1]
				if id not in apps:
					acts.append(OpenWith(self._desktop_item(info[0]), info[1]))
					apps.add(id)
		if not default:
			default = Show()
		acts.insert(0, default)
		return acts

	def has_content(self):
		return path.isdir(self.object)

	def content_source(self):
		if self.has_content():
			return DirectorySource(self.object)
		else:
			return Leaf.content_source(self)

	def get_pixbuf(self):
		uri = gnomevfs.get_uri_from_local_path(self.object)
		icon = utils.get_icon_for_uri(uri, self.icon_size)
		return icon

class DesktopLeaf (FileLeaf):
	"""
	A "loose" desktop file
	"""

	def __init__(self, obj, value):
		super(DesktopLeaf, self).__init__(obj, value)
		from gnomedesktop import item_new_from_file, LOAD_ONLY_IF_EXISTS
		self.desktop_item = item_new_from_file(self.object, LOAD_ONLY_IF_EXISTS)
		if not self.desktop_item:
			raise InvalidData

	def get_actions(self):
		acts = super(DesktopLeaf, self).get_actions()
		acts.insert(0, DesktopLaunch())
		return acts

	def has_content(self):
		return False

	def get_pixbuf(self):
		icon = utils.get_icon_for_desktop_item(self.desktop_item, self.icon_size)
		if not icon:
			return super(DesktopLeaf, self).get_pixbuf()
		return icon

class SourceLeaf (Leaf):
	def has_content(self):
		return True

	def get_actions(self):
		return (SearchInside(),)

	def content_source(self):
		return self.object

	def get_pixbuf(self):
		return self.object.get_pixbuf()

class AppLeaf (Leaf):
	def __init__(self, item):
		from gnomedesktop import KEY_NAME, KEY_EXEC
		loc_name = item.get_localestring(KEY_NAME)
		name = item.get_string(KEY_NAME)
		if name != loc_name or not loc_name:
			value = "%s (%s)" % (loc_name, name)
		else:
			value = name

		Leaf.__init__(self, item, value)
	
	def get_actions(self):
		return (Launch(), Launch(name="Launch in Terminal", in_terminal=True),
			Echo())

	def get_pixbuf(self):
		from gtk import icon_theme_get_default
		icon_file = self.object.get_icon(icon_theme_get_default())
		#icon_file = gnomevfs.get_local_path_from_uri(icon_uri)
		if not icon_file:
			return utils.get_default_application_icon(self.icon_size)
		return utils.get_icon_from_file(icon_file, self.icon_size)


class Action (KupferObject):
	"""
	Base class for all actions
	"""
	def activate(self, leaf):
		"""
		Use this action with leaf

		leaf: a Leaf object
		"""
		pass

	def is_factory(self):
		"""
		If this action returns a new source in activate
		return True
		"""
		return False
	
	def get_icon_name(self):
		"""
		Return a default icon for actions
		"""
		return "emblem-system"

class Echo (Action):
	"""
	Simply echo information about the object
	to the terminal
	"""
	def __init__(self):
		super(Echo, self).__init__("Echo (debug)")
	
	def activate(self, leaf):
		print "Echo"
		print "\n".join("%s: %s" % (k, v) for k,v in
			zip(("Leaf", "Name", "Object", "Value",
				"Id", "Actions", "Content"),
				(repr(leaf), leaf.name, leaf.object, leaf.value, id(leaf),
				leaf.get_actions(), leaf.has_content())))

class OpenWith (Action):
	"""
	Open a FileLeaf with a specified application
	"""

	def __init__(self, desktop_item, name):
		Action.__init__(self, "Open with %s" % name)
		self.desktop_item = desktop_item
	
	def preprocess_item(self):
		from gnomedesktop import KEY_EXEC
		exc = self.desktop_item.get_string(KEY_EXEC)
		if not exc:
			return
		parts = exc.split()
		if len(parts) > 1:
			return
		print "Desktop item", exc, "seems to take no files in exec"
		newexc = exc + " %F"
		print "Setting KEY_EXEC to", newexc
		self.desktop_item.set_string(KEY_EXEC, newexc)
	
	def activate(self, leaf):
		self.preprocess_item()
		filepath = leaf.object
		self.desktop_item.launch([filepath], 0)
	
	def get_pixbuf(self):
		app_icon = utils.get_icon_for_desktop_item(self.desktop_item, self.icon_size)
		if not app_icon:
			app_icon = utils.get_default_application_icon(self.icon_size)
		return app_icon

class OpenUrl (Action):
	def __init__(self, name=None):
		"""
		open url
		"""
		if not name:
			name = "Open URL"
		super(OpenUrl, self).__init__(name)
	
	def activate(self, leaf):
		url = leaf.object
		print "Open url:", url
		self.open_url(url)
	
	def open_url(self, url):
		gnomevfs.url_show(url)

	
	def get_icon_name(self):
		return "forward"

class Show (OpenUrl):
	def __init__(self, name=None):
		"""
		Open file with default viewer
		"""
		if not name:
			name = "Open"
		super(Show, self).__init__(name)
	
	def activate(self, leaf):
		print "Show: %s" % (leaf.object,)
		uri = gnomevfs.get_uri_from_local_path(leaf.object)
		self.open_url(uri)
	
	def get_icon_name(self):
		return "exec"

class OpenDirectory (Show):
	def __init__(self):
		super(OpenDirectory, self).__init__("Open")

	def get_icon_name(self):
		return "folder-open"

class OpenTerminal (Action):
	def __init__(self):
		super(OpenTerminal, self).__init__("Open Terminal here")
	
	def activate(self, leaf):
		argv = ["gnome-terminal"]
		print argv
		utils.spawn_async(argv, in_dir=leaf.object)
	
	def get_icon_name(self):
		return "terminal"

class Dragbox (Action):
	def __init__(self):
		super(Dragbox, self).__init__("Put on dragbox")
	
	def activate(self, leaf):
		path = leaf.object
		argv = ["dragbox", "--file", path]
		gobject.spawn_async(argv, flags=gobject.SPAWN_SEARCH_PATH)
	
	def get_icon_name(self):
		from gtk import STOCK_COPY
		return STOCK_COPY

class Launch (Action):
	"""
	Launch operation base class

	Launches an application
	"""
	def __init__(self, name=None, in_terminal=False):
		if not name:
			name = "Launch"
		Action.__init__(self, name)
		self.in_terminal = in_terminal
	
	def launch_item(self, item):
		if self.in_terminal:
			from gnomedesktop import KEY_TERMINAL
			item = item.copy()
			item.set_boolean(KEY_TERMINAL, True)
		args = []
		item.launch(args, 0)
	
	def activate(self, leaf):
		desktop_item = leaf.object
		self.launch_item(desktop_item)
	
	def get_pixbuf(self):
		return utils.get_default_application_icon(self.icon_size)

class DesktopLaunch (Launch):
	"""
	Launches a "loose" desktop file
	"""
	
	def __init__(self):
		super(DesktopLaunch, self).__init__("Launch (desktop file)")
	
	def activate(self, leaf):
		self.launch_item(leaf.desktop_item)

class SearchInside (Action):
	"""
	A factory action: works on a Leaf object with content
	
	Return a new source with the contents of the Leaf
	"""
	def __init__(self):
		super(SearchInside, self).__init__("Search content...")
	
	def is_factory(self):
		return True
	
	def activate(self, leaf):
		if not leaf.has_content():
			raise InvalidLeaf("Must have content")
		return leaf.content_source()

	def get_icon_name(self):
		return "search"

class DummyAction (Action):
	"""
	Represents "No action", to be shown when there is no action
	"""
	def __init__(self, name=None):
		if not name:
			name = "No action available"
		super(DummyAction, self).__init__(name)
	
	def get_icon_name(self):
		return "exec"

class Source (KupferObject):
	"""
	Source: Data provider for a kupfer browser
	"""
	def __init__(self, name=None):
		if not name:
			name = self.__class__.__name__
		KupferObject.__init__(self, name)
		self.cached_items = None

	def set_refresh_callback(self, refresh_callback):
		"""
		Set function to be called on owner when data needs refresh
		"""
		self.refresh_callback = refresh_callback

	def get_items(self):
		"""
		Internal method to compute and return the needed items

		Subclasses should use this method to return a sequence or
		iterator to the leaves it contains
		"""
		return []

	def is_dynamic(self):
		"""
		Whether to recompute contents each time it is accessed
		"""
		return False

	def get_leaves(self):
		"""
		Return a list of all leaves
		"""
		if self.is_dynamic():
			return self.get_items()
		
		if not self.cached_items:
			self.cached_items = aslist(self.get_items())
		return self.cached_items

	def has_parent(self):
		return False

	def get_parent(self):
		raise NoParent

	def representation(self):
		"""
		Return represented object
		"""
		return self

class FileSource (Source):
	def __init__(self, dirlist, depth=0):
		name = path.basename(dirlist[0])
		if len(dirlist) > 1:
			name += " et al"
		super(FileSource, self).__init__(name)
		self.dirlist = dirlist
		self.depth = depth

	def get_items(self):
		iters = []
		
		def mkleaves(dir):
			files = utils.get_dirlist(dir, depth=self.depth, exclude=self._exclude_file)
			return (FileLeaf(f, path.basename(f)) for f in files)

		for d in self.dirlist:
			iters.append(mkleaves(d))

		return itertools.chain(*iters)

	def _exclude_file(self, filename):
		return filename.startswith(".") 

	def get_icon_name(self):
		return "folder-saved-search"

class DirectorySource (Source):
	def __init__(self, dir):
		name = path.basename(dir)
		super(DirectorySource, self).__init__(name)
		self.directory = dir
		self.deep = False

	def get_items(self):
		dirlist = utils.get_dirlist(self.directory, exclude=lambda f: f.startswith("."))
		def file_leaves(files):
			for file in files:
				basename = path.basename(file)
				if path.isdir(file):
					basename += "/"
				yield FileLeaf(file, basename)

		return file_leaves(dirlist)

	def _parent_path(self):
		return path.normpath(path.join(self.directory, path.pardir))

	def has_parent(self):
		return not path.samefile(self.directory , self._parent_path())

	def get_parent(self):
		if not self.has_parent():
			return FileSource.has_parent(self)
		return DirectorySource(self._parent_path())

	def get_icon_name(self):
		return "folder"

class SourcesSource (Source):
	def __init__(self, sources):
		super(SourcesSource, self).__init__("Catalog of Catalogs")
		self.sources = sources
	
	def get_items(self):
		return (SourceLeaf(s, str(s)) for s in self.sources)

	def get_icon_name(self):
		return "folder-saved-search"

class MultiSource (Source):
	def __init__(self, sources):
		super(MultiSource, self).__init__("Catalog")
		self.sources = sources
	
	def is_dynamic(self):
		"""
		MultiSource should be dynamic so some of its content
		also can be
		"""
		return True

	def get_items(self):
		iterators = []
		for so in self.sources:
			it = so.get_leaves()
			iterators.append(it)

		return itertools.chain(*iterators)

	def get_icon_name(self):
		return "folder-saved-search"

class AppSource (Source):
	"""
	Applications source

	This Source contains all user-visible applications (as given by
	the desktop files)
	"""
	def __init__(self):
		super(AppSource, self).__init__("All Applications")
	
	def get_icon_name(self):
		return "gnome-applications"

	def get_items(self):
		dirs = utils.get_xdg_data_dirs()
		from os import walk
		import gnomedesktop as gd

		desktop_files = []

		inc_files = set()

		def add_desktop_item(item):
			hid = item.get_boolean(gd.KEY_HIDDEN)
			nodisp = item.get_boolean(gd.KEY_NO_DISPLAY)
			type = item.get_string(gd.KEY_TYPE)

			if True in (hid, nodisp) or (type != "Application"):
				return
			file = gnomevfs.get_local_path_from_uri(item.get_location())
			name = path.basename(file)
			if name in inc_files:
				return
			inc_files.add(name)
			desktop_files.append(item)
		
		for d in dirs:
			apps = path.join(d, "applications")
			if not path.exists(apps):
				continue
			for root, dirnames, fnames in walk(apps):
				for file in fnames:
					abspath = path.join(root, file)
					item = gd.item_new_from_file(abspath, gd.LOAD_ONLY_IF_EXISTS)
					if item:
						add_desktop_item(item)

				del dirnames[:]
		
		return (AppLeaf(item) for item in desktop_files)


class UrlLeaf (Leaf):
	def __init__(self, obj, value):
		super(UrlLeaf, self).__init__(obj, value)
	
	def get_actions(self):
		return (OpenUrl(), Echo())

	def get_icon_name(self):
		return "internet-web-browser"

class BookmarksSource (Source):
	def __init__(self):
		super(BookmarksSource, self).__init__("Firefox Bookmarks")
	
	def get_items(self):
		from bookmarks import get_firefox_home_file, get_bookmarks
		bookmarks = get_bookmarks(get_firefox_home_file("bookmarks.html"))
		print "Loaded", len(bookmarks), "bookmarks"
		return (UrlLeaf(book["href"], book["title"][:40]) for book in bookmarks)

	def get_icon_name(self):
		return "internet-web-browser"


class RecentsSource (Source):
	def __init__(self):
		super(RecentsSource, self).__init__("Recent items")
		self.max_days = 14
	
	def get_items(self):
		from gtk import recent_manager_get_default

		count = 0
		manager = recent_manager_get_default()
		items = manager.get_items()
		for item in items:
			day_age = item.get_age()
			if day_age > self.max_days:
				break
			if not item.exists():
				continue

			uri = item.get_uri()
			name = item.get_short_name()
			if item.is_local():
				fileloc = item.get_uri_display()
				yield FileLeaf(fileloc, name)
			else:
				yield UrlLeaf(uri, name)
			count += 1
		print count, "recent items younger than", self.max_days, "days"
	
	def get_icon_name(self):
		return "emblem-important"

class PlacesSource (Source):
	"""
	Source for items from nautilus bookmarks 
	"""
	def __init__(self):
		super(PlacesSource, self).__init__("Places")
		self.places_file = "~/.gtk-bookmarks"
	
	def get_items(self):
		"""
		gtk-bookmarks: each line has url and optional title
		file:///path/to/that.end [title]
		"""
		fileloc = path.expanduser(self.places_file)
		if not path.exists(fileloc):
			return ()
		return self._get_places(fileloc)

	def _get_places(self, fileloc):
		for line in open(fileloc):
			if not line.strip():
				continue
			items = line.split()
			uri = items[0]
			if len(items) > 1:
				title = items[1]
			else:
				disp = gnomevfs.format_uri_for_display(uri)
				title =	path.basename(disp)
			scheme = gnomevfs.get_uri_scheme(uri)
			if "file" == scheme:
				loc = gnomevfs.get_local_path_from_uri(uri)
				yield FileLeaf(loc, title)
			else:
				yield UrlLeaf(uri, title)

	def get_icon_name(self):
		return "file-manager"

