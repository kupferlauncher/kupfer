# -*- coding: UTF-8 -*-

"""
Actions, Leaves, Sources for
kupfer
ɹǝɟdnʞ

Copyright 2007 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
Released under GNU General Public License v3 (or any later version)
"""

import itertools
from os import path
import os
import locale

import gobject
import gio

from . import icons
from . import pretty
from . import utils, launch

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

def tounicode(utf8str):
	"""Return `unicode` from UTF-8 encoded @utf8str
	This is to use the same error handling etc everywhere
	if ustr is unicode, just return it
	"""
	if isinstance(utf8str, unicode):
		return utf8str
	return utf8str.decode("UTF-8", "replace")

def toutf8(ustr):
	"""Return UTF-8 `str` from unicode @ustr
	This is to use the same error handling etc everywhere
	if ustr is `str`, just return it
	"""
	if isinstance(ustr, str):
		return ustr
	return ustr.encode("UTF-8", "replace")

def locale_sort(seq):
	""" Return @seq sorted in locale lexical order """
	locale_cmp = lambda s, o: locale.strcoll(unicode(s), unicode(o))
	seq = aslist(seq)
	seq.sort(cmp=locale_cmp)
	return seq

class KupferObject (object):
	"""
	Base class for Actions and Leaves
	"""
	def __init__(self, name=None):
		""" Init kupfer object with, where
		@name *should* be a unicode object but *may* be
		a UTF-8 encoded `str`
		"""
		if not name:
			name = self.__class__.__name__
		self.name = tounicode(name)
	
	def __str__(self):
		return toutf8(self.name)

	def __unicode__(self):
		"""Return a `unicode` representation of @self """
		return self.name

	def __repr__(self):
		return "".join(("<", self.__module__, ".", self.__class__.__name__,
			" ", toutf8(self.name), ">"))

	def get_description(self):
		"""Return a description of the specific item
		which *should* be a unicode object but *may* be
		a UTF-8 encoded `str` or None
		"""
		return None

	def get_thumbnail(self, width, height):
		"""Return pixbuf of size @width x @height if available
		Most objects will not implement this
		"""
		return None

	def get_pixbuf(self, icon_size):
		"""
		Returns an icon in pixbuf format with dimension @icon_size

		Subclasses should implement: get_gicon and get_icon_name,
		if they make sense.
		The methods are tried in that order.
		"""
		gicon = self.get_gicon()
		if gicon:
			pbuf = icons.get_icon_for_gicon(gicon, icon_size)
			if pbuf:
				return pbuf
		icon_name = self.get_icon_name()
		if icon_name:
			return icons.get_icon_for_name(icon_name, icon_size)
		return None

	def get_icon(self):
		"""
		Returns an icon in GIcon format

		Subclasses should implement get_gicon and
		get_icon_name, if they make sense.
		"""
		gicon = self.get_gicon()
		if not icons.is_good(gicon):
			gicon = gio.ThemedIcon(self.get_icon_name())
		return gicon

	def get_gicon(self):
		"""Return GIcon, if there is one
		by default constructs a GIcon from get_icon_name
		"""
		return None
	
	def get_icon_name(self):
		"""Return icon name. All items should have at least
		a generic icon name to return. """
		return "gtk-file"

def aslist(seq):
	"""
	Make lists from sequences that are not lists or tuples

	For iterators, sets etc.
	"""
	if not isinstance(seq, type([])) and not isinstance(seq, type(())):
		seq = list(seq)
	return seq

class Leaf (KupferObject):
	def __init__(self, obj, name):
		super(Leaf, self).__init__(name)
		self.object = obj
	
	def __hash__(self):
		return hash(str(self))

	def __eq__(self, other):
		return (type(self) == type(other) and self.object == other.object)

	def has_content(self):
		return False
	
	def content_source(self, alternate=False):
		"""Content of leaf. it MAY alter behavior with @alternate,
		as easter egg/extra mode"""
		raise NoContent

	def get_actions(self):
		return ()

class DummyLeaf (Leaf):
	"""
	Dummy Leaf, representing No Leaf available
	"""
	def __init__(self):
		super(DummyLeaf, self).__init__(None, _("No matches"))
	
	def get_icon_name(self):
		return "gtk-dialog-warning"

class FileLeaf (Leaf):
	"""
	Represents one file
	"""
	# To save memory with (really) many instances
	__slots__ = ("name", "object")

	def __init__(self, obj, name=None):
		"""
		Construct a FileLeaf

		The display name of the file is normally
		derived from the full path, and @name
		should normally be left unspecified.
		@obj: byte string (file system encoding)
		@name: unicode name or None for using basename
		"""
		# Resolve symlinks
		obj = path.realpath(obj) or obj
		# Use glib filename reading to make display name out of filenames
		# this function returns a `unicode` object
		if not name:
			name = gobject.filename_display_basename(obj)
		super(FileLeaf, self).__init__(obj, name)

	def __repr__(self):
		return "".join(("<", self.__module__, ".", self.__class__.__name__,
			" ", self.object, ">"))

	def _is_valid(self):
		from os import access, R_OK
		return access(self.object, R_OK)

	def _is_executable(self):
		from os import access, X_OK, R_OK
		return access(self.object, R_OK | X_OK)

	def is_dir(self):
		return path.isdir(self.object)
	def is_valid(self):
		return self._is_valid()

	def get_description(self):
		"""Format the path shorter:
		replace homedir by ~/
		"""
		# Use glib filename reading to make display name out of filenames
		# this function returns a `unicode` object
		desc = gobject.filename_display_name(self.object)
		homedir = path.expanduser("~/")
		if desc.startswith(homedir) and homedir != desc:
			desc = desc.replace(homedir, "~/", 1)
		return desc

	def get_actions(self):
		acts = [RevealFile(), ]
		app_actions=[]
		default = None
		if path.isdir(self.object):
			acts.extend([OpenTerminal(), SearchInside()])
			default = OpenDirectory()
		elif self._is_valid():
			gfile = gio.File(self.object)
			info = gfile.query_info(gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE)
			content_type = info.get_attribute_string(gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE)
			def_app = gio.app_info_get_default_for_type(content_type, False)
			def_key = def_app.get_id() if def_app else None
			types = gio.app_info_get_all_for_type(content_type)
			apps = {}
			for info in types:
				key = info.get_id()
				if key not in apps:
					try:
						is_default = (key == def_key)
						app = OpenWith(info, is_default)
						apps[key] = app
					except InvalidData:
						pass
			if def_key:
				if not def_key in apps:
					print "No default found for %s, but found %s" % (self, apps)
				else:
					app_actions.append(apps.pop(def_key))
			app_actions.extend(apps.values())

			if self._is_executable():
				acts.extend((Execute(), Execute(in_terminal=True)))
			elif app_actions:
				default = app_actions.pop(0)
			else:
				app_actions.append(Show())
		if app_actions:
			acts.extend(app_actions)
		if default:
			acts.insert(0, default)
		return acts

	def has_content(self):
		return path.isdir(self.object)
	def content_source(self, alternate=False):
		if self.has_content():
			return DirectorySource(self.object, show_hidden=alternate)
		else:
			return Leaf.content_source(self)

	def get_thumbnail(self, width, height):
		if self.is_dir(): return None
		return icons.get_thumbnail_for_file(self.object, width, height)
	def get_gicon(self):
		return icons.get_gicon_for_file(self.object)
	def get_icon_name(self):
		"""A more generic icon"""
		if self.is_dir():
			return "folder"
		else:
			return "gtk-file"

def ConstructFileLeafTypes():
	""" Return a seq of the Leaf types returned by ConstructFileLeaf"""
	yield FileLeaf
	yield AppLeaf

def ConstructFileLeaf(obj):
	"""
	If the path in @obj points to a Desktop Item file,
	return an AppLeaf, otherwise return a FileLeaf
	"""
	root, ext = path.splitext(obj)
	if ext == ".desktop":
		try:
			return AppLeaf(path=obj)
		except InvalidData:
			pass
	return FileLeaf(obj)

class SourceLeaf (Leaf):
	def __init__(self, obj, name=None):
		"""Create SourceLeaf for source @obj"""
		if not name:
			name = unicode(obj)
		Leaf.__init__(self, obj, name)
	def has_content(self):
		return True

	def get_actions(self):
		yield SearchInside()
		if not self.object.is_dynamic():
			yield RescanSource()

	def content_source(self, alternate=False):
		return self.object

	def get_description(self):
		return self.object.get_description()

	def get_gicon(self):
		return self.object.get_gicon()

	def get_icon_name(self):
		return self.object.get_icon_name()

class AppLeaf (Leaf):
	def __init__(self, item=None, path=None, item_id=None):
		super(AppLeaf, self).__init__(item, "")
		self.path = path
		if not item:
			item = self._get_item(path,item_id)
		self._init_from_item(item)
		if not self.object:
			raise InvalidData

	def _get_item(self, path=None, item_id=None):
		"""Construct an AppInfo item from either path or item_id"""
		from gio.unix import DesktopAppInfo, desktop_app_info_new_from_filename
		item = None
		if path:
			item = desktop_app_info_new_from_filename(path)
		if item_id:
			item = DesktopAppInfo(item_id)
		return item

	def _init_from_item(self, item):
		if item:
			value = item.get_name() or item.get_executable()
		else:
			value = "Unknown"
		self.object = item
		self.name = value

	def __getstate__(self):
		"""Return state for pickle"""
		item_id = self.object.get_id() if self.object else None
		return (self.path, item_id)
	
	def __setstate__(self, state):
		path, item_id = state
		self.path = path
		self._init_from_item(self._get_item(path, item_id))

	def get_actions(self):
		if launch.application_is_running(self.object):
			yield ShowApplication()
			yield LaunchAgain()
		else:
			yield Launch()

	def get_description(self):
		"""description: Use "App description (executable)" """
		return _("%(description)s (%(exec)s)") % (
				{"description": self.object.get_description() or "",
				 "exec": self.object.get_executable() or "",
				})

	def get_gicon(self):
		return self.object.get_icon()

	def get_icon_name(self):
		return "exec"

class Action (KupferObject):
	'''
	Base class for all actions

	Implicit interface:
	  valid_object will be called once for each (secondary) object
	  to see if it applies. If it is not defined, all objects are
	  assumed ok (within the other type/source constraints)

	def valid_object(self, obj, for_item):
		"""Whether @obj is good for secondary obj,
		where @for_item is passed in as a hint for
		which it should be applied to
		"""
		return True
	'''

	def activate(self, leaf, obj=None):
		"""
		Use this action with @leaf and @obj

		@leaf: a Leaf object
		@obj: a secondary Leaf object
		"""
		pass

	def is_factory(self):
		"""
		If this action returns a new source in activate
		return True
		"""
		return False

	def item_types(self):
		"""Yield items this action may apply to. This is used only
		when this action is specified in __kupfer_actions__ to "decorate"
		"""
		return ()

	def valid_for_item(self, item):
		"""Whether action can be used with exactly @item"""
		return True

	def requires_object(self):
		"""
		If this action requires a secondary object
		to complete is action
		"""
		return False

	def object_source(self, for_item=None):
		"""Source to use for object or None
		to use the catalog (flat, filtered for @object_types)
		"""
		return None

	def object_types(self):
		return ()

	def get_icon_name(self):
		"""
		Return a default icon for actions
		"""
		return "gtk-execute"

class Echo (Action):
	"""
	Simply echo information about the object
	to the terminal
	"""
	def __init__(self):
		super(Echo, self).__init__("Echo")
	
	def activate(self, leaf):
		print "Echo"
		print "\n".join("%s: %s" % (k, v) for k,v in
			zip(("Leaf", "Name", "Object", "Value",
				"Id", "Actions", "Content"),
				(repr(leaf), leaf.name, leaf.object, id(leaf),
				leaf.get_actions(), leaf.has_content())))
		if type(leaf) == AppLeaf:
			print ".desktop:", leaf.object.get_location()

	def get_description(self):
		return "Print debug output"
	def get_icon_name(self):
		return "emblem-system"

class OpenWith (Action):
	"""
	Open a FileLeaf with a specified application
	"""

	def __init__(self, desktop_item, is_default=False):
		"""
		Construct an "Open with application" item:

		Application of @name should open, if
		@is_default, it means it is the default app and
		should only be styled "Open"
		"""
		if not desktop_item:
			raise InvalidData

		name = desktop_item.get_name()
		action_name = _("Open") if is_default else _("Open with %s") % name
		Action.__init__(self, action_name)
		self.desktop_item = desktop_item
		self.is_default = is_default
	
	def activate(self, leaf):
		if not self.desktop_item.supports_files() and not self.desktop_item.supports_uris():
			print self, "does not support opening files"
		utils.launch_app(self.desktop_item, paths=(leaf.object,))

	def get_description(self):
		if self.is_default:
			return _("Open with %s (default)") % self.desktop_item.get_name()
		else:
			return _("Open with %s") % self.desktop_item.get_name()
	def get_pixbuf(self, size):
		return icons.compose_icon("gtk-execute",self.desktop_item.get_icon(), icon_size=size)
	def get_gicon(self):
		return self.desktop_item.get_icon()
	def get_icon_name(self):
		return "gtk-execute"

class OpenUrl (Action):
	def __init__(self, name=None):
		"""
		open url
		"""
		if not name:
			name = _("Open URL")
		super(OpenUrl, self).__init__(name)
	
	def activate(self, leaf):
		url = leaf.object
		self.open_url(url)
	
	def open_url(self, url):
		utils.show_url(url)

	def get_description(self):
		return _("Open URL with default viewer")

	def get_icon_name(self):
	  	return "forward"

class Show (Action):
	""" Open file with default viewer """
	def __init__(self, name=_("Open")):
		super(Show, self).__init__(name)
	
	def activate(self, leaf):
		utils.show_path(leaf.object)

	def get_description(self):
		return _("Open with default viewer")

	def get_icon_name(self):
		return "gtk-execute"

class OpenDirectory (Show):
	def __init__(self):
		super(OpenDirectory, self).__init__(_("Open"))

	def get_description(self):
		return _("Open folder")

	def get_icon_name(self):
		return "folder-open"

class RevealFile (Action):
	def __init__(self, name=_("Reveal")):
		super(RevealFile, self).__init__(name)
	
	def activate(self, leaf):
		fileloc = leaf.object
		parent = path.normpath(path.join(fileloc, path.pardir))
		utils.show_path(parent)

	def get_description(self):
		return _("Open parent folder")

	def get_icon_name(self):
		return "folder-open"

class OpenTerminal (Action):
	def __init__(self, name=_("Open Terminal here")):
		super(OpenTerminal, self).__init__(name)
	
	def activate(self, leaf):
		argv = ["gnome-terminal"]
		utils.spawn_async(argv, in_dir=leaf.object)

	def get_description(self):
		return _("Open this location in a terminal")
	def get_icon_name(self):
		return "terminal"

class Launch (Action):
	"""
	Launch operation base class

	Launches an application (AppLeaf)
	"""
	def __init__(self, name=None, in_terminal=False, open_new=False):
		if not name:
			name = _("Launch")
		Action.__init__(self, name)
		self.in_terminal = in_terminal
		self.open_new = open_new
	
	def activate(self, leaf):
		desktop_item = leaf.object
		launch.launch_application(leaf.object, activate=not self.open_new)

	def get_description(self):
		return _("Launch application")

class ShowApplication (Launch):
	"""Show application if running, else launch"""
	def __init__(self, name=None):
		if not name:
			name = _("Go to")
		Launch.__init__(self, name, open_new=False)

	def get_description(self):
		return _("Show application window")
	def get_icon_name(self):
		return "gtk-jump-to-ltr"

class LaunchAgain (Launch):
	"""Launch instance without checking if running"""
	def __init__(self, name=None):
		if not name:
			name = _("Launch again")
		Launch.__init__(self, name, open_new=True)

	def get_description(self):
		return _("Launch another instance of this application")

class Execute (Launch):
	"""
	Execute executable file (FileLeaf)
	"""
	def __init__(self, in_terminal=False, args=""):
		name = _("Run in Terminal") if in_terminal else _("Run")
		super(Execute, self).__init__(name)
		self.in_terminal = in_terminal
		self.args = args
	
	def activate(self, leaf):
		cli = "%s %s" % (leaf.object, self.args)
		utils.launch_commandline(cli, in_terminal=self.in_terminal)

	def get_description(self):
		if self.in_terminal:
			return _("Run this program in a Terminal")
		else:
			return _("Run this program")

class SearchInside (Action):
	"""
	A factory action: works on a Leaf object with content
	
	Return a new source with the contents of the Leaf
	"""
	def __init__(self):
		super(SearchInside, self).__init__(_("Search content..."))
	
	def is_factory(self):
		return True
	
	def activate(self, leaf):
		if not leaf.has_content():
			raise InvalidLeaf("Must have content")
		return leaf.content_source()

	def get_description(self):
		return _("Search inside this catalog")

	def get_icon_name(self):
		return "search"

class RescanSource (Action):
	"""
	A source action: Rescan a source!
	"""
	def __init__(self):
		super(RescanSource, self).__init__(_("Rescan"))
	
	def is_factory(self):
		return False
	
	def activate(self, leaf):
		if not leaf.has_content():
			raise InvalidLeaf("Must have content")
		source = leaf.object
		if not source.is_dynamic():
			cache = source.get_leaves(force_update=True)

	def get_description(self):
		return _("Force reindex of this source")

	def get_icon_name(self):
		return "gtk-refresh"

class DummyAction (Action):
	"""
	Represents "No action", to be shown when there is no action
	"""
	def __init__(self, name=None):
		if not name:
			name = _("No action")
		super(DummyAction, self).__init__(name)
	
	def get_icon_name(self):
		return "gtk-execute"

class Source (KupferObject, pretty.OutputMixin):
	"""
	Source: Data provider for a kupfer browser

	Sources are hashable and treated as equal if
	their @repr are equal!
	"""
	def __init__(self, name):
		KupferObject.__init__(self, name)
		self.cached_items = None

	def __eq__(self, other):
		return (type(self) == type(other) and repr(self).__eq__(repr(other)))

	def __hash__(self ):
		return hash(repr(self))

	def __repr__(self):
		return "%s.%s(\"%s\")" % (self.__class__.__module__, self.__class__.__name__, str(self))

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

	def mark_for_update(self):
		"""
		Mark source as changed

		it should be reloaded on next used (if normally cached)
		"""
		self.cached_items = None

	def should_sort_lexically(self):
		"""
		Sources should return items by most relevant order (most
		relevant first). If this is True, Source will sort items
		from get_item() in locale lexical order
		"""
		return False

	def get_leaves(self, force_update=False):
		"""
		Return a list of all leaves
		"""
		if self.should_sort_lexically():
			# sort in locale order
			sort_func = locale_sort
		else:
			sort_func = lambda x: x

		if self.is_dynamic():
			return sort_func(self.get_items())
		
		if not self.cached_items or force_update:
			self.cached_items = aslist(sort_func(self.get_items()))
			self.output_info("Loaded %d items" % len(self.cached_items))
		return self.cached_items

	def has_parent(self):
		return False

	def get_parent(self):
		raise NoParent

	def get_leaf_repr(self):
		"""Return, if appicable, another object
		to take the source's place as Leaf"""
		return None

	def provides(self):
		"""A seq of the types of items it provides;
		empty is taken as anything -- however most sources
		should set this to exactly the type they yield
		"""
		return ()

class FileSource (Source):
	def __init__(self, dirlist, depth=0):
		"""
		@dirlist: Directories as byte strings
		"""
		name = gobject.filename_display_basename(dirlist[0])
		super(DirectorySource, self).__init__(name)
		if len(dirlist) > 1:
			name = _("%s et al") % name
		super(FileSource, self).__init__(name)
		self.dirlist = dirlist
		self.depth = depth

	def __repr__(self):
		"""Unique for each configuration"""
		return "<%s %s depth=%d>" % (type(self).__name__,
				" ".join(sorted(self.dirlist)), self.depth)

	def get_items(self):
		iters = []
		
		def mkleaves(dir):
			files = utils.get_dirlist(dir, depth=self.depth, exclude=self._exclude_file)
			return (ConstructFileLeaf(f) for f in files)

		for d in self.dirlist:
			iters.append(mkleaves(d))

		return itertools.chain(*iters)

	def _exclude_file(self, filename):
		return filename.startswith(".") 

	def get_description(self):
		return (_("Recursive source of %(dir)s, (%(levels)d levels)") %
				{"dir": self.name, "levels": self.depth})

	def get_icon_name(self):
		return "folder-saved-search"
	def provides(self):
		return ConstructFileLeafTypes()

class DirectorySource (Source):
	def __init__(self, dir, show_hidden=False):
		# Use glib filename reading to make display name out of filenames
		# this function returns a `unicode` object
		name = gobject.filename_display_basename(dir)
		super(DirectorySource, self).__init__(name)
		self.directory = dir
		self.show_hidden = show_hidden
		self._setup_change_monitor()

	def __repr__(self):
		return "%s.%s(\"%s\", show_hidden=%s)" % (self.__class__.__module__, self.__class__.__name__, str(self.directory), self.show_hidden)

	def __getstate__(self):
		"""Custom pickling routines """
		# monitor is not pickleable
		self.monitor = None
		return self.__dict__

	def __setstate__(self, state):
		"""Custom pickling routines to restore file monitoring
		upon unpickling"""
		self.__dict__.update(state)
		self._setup_change_monitor()

	def get_items(self):
		exclude = lambda f: f.startswith(".") if not self.show_hidden else None
		dirlist = utils.get_dirlist(self.directory, exclude=exclude)
		def file_leaves(files):
			for file in files:
				yield ConstructFileLeaf(file)

		return file_leaves(dirlist)
	def should_sort_lexically(self):
		return True

	def _setup_change_monitor(self):
		gfile = gio.File(self.directory)
		self.monitor = gfile.monitor_directory(gio.FILE_MONITOR_NONE, None)
		if self.monitor:
			self.monitor.connect("changed", self._changed)

	def _changed(self, monitor, file1, file2, evt_type):
		"""Change callback; something changed in the directory"""
		# mark for update only for significant changes
		# (for example, changed files need no update, only new files)
		if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
				gio.FILE_MONITOR_EVENT_DELETED):
			# ignore invisible files
			# (since lots of dotfiles are touched in $HOME)
			if file1 and file1.get_basename().startswith("."):
				return
			self.mark_for_update()

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
		return FileLeaf(self.directory)
	def provides(self):
		return ConstructFileLeafTypes()

class SourcesSource (Source):
	""" A source whose items are SourceLeaves for @source """
	def __init__(self, sources):
		super(SourcesSource, self).__init__(_("Catalog index"))
		self.sources = sources

	def get_items(self):
		"""Ask each Source for a Leaf substitute, else
		yield a SourceLeaf """
		for s in self.sources:
			yield s.get_leaf_repr() or SourceLeaf(s)

	def should_sort_lexically(self):
		return True

	def get_description(self):
		return _("An index of all available sources")

	def get_icon_name(self):
		return "folder-saved-search"

class MultiSource (Source):
	"""
	A source whose items are the combined items
	of all @sources
	"""
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
		for so in self.sources:
			it = so.get_leaves()
			iterators.append(it)

		return itertools.chain(*iterators)

	def get_description(self):
		return _("Root catalog")

	def get_icon_name(self):
		return "folder-saved-search"

class UrlLeaf (Leaf):
	# slots saves memory since we have lots this Leaf
	__slots__ = ("name", "object")
	def __init__(self, obj, name):
		super(UrlLeaf, self).__init__(obj, name)

	def get_actions(self):
		return (OpenUrl(), )

	def get_description(self):
		return self.object

	def get_icon_name(self):
		return "text-html"

class TextLeaf (Leaf):
	"""Represent a text query
	represented object is the unicode string
	"""
	def __init__(self, text):
		Leaf.__init__(self, text, name=text)
	
	def get_actions(self):
		return ()

	def get_description(self):
		# TRANS: This is description for a TextLeaf, a free-text search
		return _('"%s"') % self.object

	def get_icon_name(self):
		return "gtk-select-all"

class TextSource (KupferObject):
	"""TextSource base class implementation,

	this is a psedo Source"""
	def __init__(self, name=None):
		if not name:
			name = _("Text matches")
		KupferObject.__init__(self, name)

	def __eq__(self, other):
		return (type(self) == type(other) and repr(self).__eq__(repr(other)))

	def __hash__(self ):
		return hash(repr(self))

	def __repr__(self):
		return "%s.%s(\"%s\")" % (self.__class__.__module__, self.__class__.__name__, str(self))

	def get_rank(self):
		return 50
	def has_ranked_items(self):
		"""If True, use get_ranked_items(), else get_items()"""
		return False
	def get_ranked_items(self, text):
		"""Return a sequence of tuple of (item, rank)"""
		return ()
	def get_items(self, text):
		"""Get leaves for unicode string @text"""
		return ()
	def provides(self):
		"""A seq of the types of items it provides"""
		yield Leaf
