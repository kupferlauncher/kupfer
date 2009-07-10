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

class KupferObject (object):
	"""
	Base class for Actions and Leaves
	"""
	icon_size = 96
	def __init__(self, name=None):
		if not name:
			name = self.__class__.__name__
		self.name = name
		assert isinstance(self.name, str), "%s of %s is not str type" % (repr(self.name), type(self))
	
	def __str__(self):
		return self.name

	def __unicode__(self):
		"""Return a `unicode` representation of @self
		using self.name which *must* be a UTF-8 encoded `str`
		"""
		return self.name.decode("UTF-8", "replace")

	def get_description(self):
		"""Return a description of the specific item
		@return *must* be a UTF-8 encoded `str` or None
		"""
		return None

	def get_thumbnail(self, width, height):
		"""
		Return a thumbnail of file as pixbuf, restricted
		to @width x @height. Else None
		"""
		return None

	def get_pixbuf(self):
		"""
		Returns an icon in pixbuf format.

		Subclasses should implement: get_thumbnail, get_gicon
		and get_icon_name, if they make sense.
		The methods are tried in that order.
		"""
		thumb = self.get_thumbnail((self.icon_size * 4)/3, self.icon_size)
		if thumb:
			return thumb
		gicon = self.get_gicon()
		if gicon:
			pbuf = icons.get_icon_for_gicon(gicon, self.icon_size)
			if pbuf:
				return pbuf
		icon_name = self.get_icon_name()
		if icon_name:
			return icons.get_icon_for_name(icon_name, self.icon_size)
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
		"""
		# Resolve symlinks
		obj = path.realpath(obj) or obj
		# Use glib filename reading to make display name out of filenames
		# this function returns a `unicode` object that we decode
		if not name:
			name = gobject.filename_display_basename(obj).encode("UTF-8")
		super(FileLeaf, self).__init__(obj, name)

	def _is_valid(self):
		from os import access, R_OK
		return access(self.object, R_OK)

	def _is_executable(self):
		from os import access, X_OK, R_OK
		return access(self.object, R_OK | X_OK)

	def _is_dir(self):
		return path.isdir(self.object)

	def get_description(self):
		"""Format the path shorter:
		replace homedir by ~/
		"""
		# Use glib filename reading to make display name out of filenames
		# this function returns a `unicode` object that we decode
		desc = gobject.filename_display_name(self.object).encode("UTF-8")
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
		if self._is_dir(): return None
		return icons.get_thumbnail_for_file(self.object, width, height)
	def get_gicon(self):
		return icons.get_gicon_for_file(self.object)
	def get_icon_name(self):
		"""A more generic icon"""
		if self._is_dir():
			return "folder"
		else:
			return "gtk-file"

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
			name = _("Show")
		Launch.__init__(self, name, open_new=False)

	def get_description(self):
		return _("Show application window")

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

	def get_icon_name(self):
		return "exec"

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
	def __init__(self, name=None):
		if not name:
			name = self.__class__.__name__
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

	def get_leaves(self, force_update=False):
		"""
		Return a list of all leaves
		"""
		if self.is_dynamic():
			return self.get_items()
		
		if not self.cached_items or force_update:
			self.cached_items = aslist(self.get_items())
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

class FileSource (Source):
	def __init__(self, dirlist, depth=0):
		name = path.basename(dirlist[0])
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

class DirectorySource (Source):
	def __init__(self, dir, show_hidden=False):
		name = path.basename(dir) or dir
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

		# Make sure this is an ordered list!
		# sort in locale order
		locale_cmp = lambda s, o: locale.strcoll(unicode(s), unicode(o))
		return sorted(file_leaves(dirlist), cmp=locale_cmp)

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

class SourcesSource (Source):
	""" A source whose items are SourceLeaves for @source """
	def __init__(self, sources, name=_("Catalog index")):
		super(SourcesSource, self).__init__(name)
		self.sources = sources

	def get_items(self):
		"""Ask each Source for a Leaf substitute, else
		yield a SourceLeaf """
		for s in self.sources:
			yield s.get_leaf_repr() or SourceLeaf(s, str(s))

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
	"""Represent a text query"""
	def __init__(self, text):
		"""@text: UTF-8 encoded text this represents"""
		Leaf.__init__(self, text, name=text)
	
	def get_actions(self):
		return ()

	def get_description(self):
		return _('Text query "%s"') % self.object

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
		return ()

class ActionDecorator (object):
	"""Base class for an object assigning more actions to Leaves"""
	def __init__(self):
		pass
	def applies_to(self):
		"""return sequence of Leaf types this decorator applies to"""
		return ()
	def is_dynamic(self):
		""" dynamic is ignored for now"""
		return False
	def get_actions(self, leaf=None):
		"""Return actions for @leaf (only passed in to dynamic decors)"""
		return ()

