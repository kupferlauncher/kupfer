# -*- coding: UTF-8 -*-

"""
Copyright 2007--2009 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""

import itertools
import os
from os import path

import gobject
import gio

from kupfer import datatools
from kupfer import icons, launch, utils
from kupfer import pretty
from kupfer.utils import locale_sort
from kupfer.helplib import PicklingHelperMixin, FilesystemWatchMixin
from kupfer.interface import TextRepresentation
from kupfer.kupferstring import tounicode, toutf8, tofolded

class Error (Exception):
	pass

class InvalidDataError (Error):
	"""The data is wrong for the given Leaf"""
	pass

class InvalidLeafError (Error):
	"""The Leaf passed to an Action is invalid"""
	pass

class KupferObject (object):
	"""
	Base class for kupfer data model

	This class provides a way to get at an object's:

	* icon with get_thumbnail, get_pixbuf and get_icon
	* name with unicode() or str()
	* description with get_description

	@rank_adjust should be used _very_ sparingly:
		Default actions should have +5 or +1
		Destructive (dangerous) actions should have -5 or -10
	"""
	rank_adjust = 0
	def __init__(self, name=None):
		""" Init kupfer object with, where
		@name *should* be a unicode object but *may* be
		a UTF-8 encoded `str`
		"""
		if not name:
			name = self.__class__.__name__
		self.name = tounicode(name)
		folded_name = tofolded(self.name)
		self.name_aliases = set()
		if folded_name != self.name:
			self.name_aliases.add(folded_name)

	def __str__(self):
		return toutf8(self.name)

	def __unicode__(self):
		"""Return a `unicode` representation of @self """
		return self.name

	def __repr__(self):
		key = str(self.repr_key())
		return "".join(("<", self.__module__, ".", self.__class__.__name__,
			((" %s" % key) if key else ""), ">"))

	def repr_key(self):
		"""
		Return an object whose str() will be used in the __repr__,
		self is returned by default.
		This value is used to recognize objects, for example learning commonly
		used objects.
		"""
		return self

	def get_description(self):
		"""Return a description of the specific item
		which *should* be a unicode object
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
			icon = icons.get_icon_for_name(icon_name, icon_size)
			if icon: return icon
		return icons.get_icon_for_name(KupferObject.get_icon_name(self), icon_size)

	def get_icon(self):
		"""
		Returns an icon in GIcon format

		Subclasses should implement: get_gicon and get_icon_name,
		if they make sense.
		The methods are tried in that order.
		"""
		return icons.get_gicon_with_fallbacks(self.get_gicon(),
				(self.get_icon_name(), KupferObject.get_icon_name(self)))

	def get_gicon(self):
		"""Return GIcon, if there is one"""
		return None
	
	def get_icon_name(self):
		"""Return icon name. All items should have at least
		a generic icon name to return.
		"""
		return "kupfer-object"

def aslist(seq):
	"""Return a list out of @seq, or seq if it is a list"""
	if not isinstance(seq, type([])) and not isinstance(seq, type(())):
		seq = list(seq)
	return seq

class Leaf (KupferObject):
	"""
	Base class for objects

	Leaf.object is the represented object (data)
	All Leaves should be hashable (__hash__ and __eq__)
	"""
	def __init__(self, obj, name):
		"""Represented object @obj and its @name"""
		super(Leaf, self).__init__(name)
		self.object = obj
		self._has_content = None
		self._content_source = None
	
	def __hash__(self):
		return hash(unicode(self))

	def __eq__(self, other):
		return (type(self) == type(other) and self.object == other.object)

	def add_content(self, content):
		"""Register content source @content with Leaf"""
		self._has_content = bool(content)
		self._content_source = content

	def has_content(self):
		return self._has_content

	def content_source(self, alternate=False):
		"""Content of leaf. it MAY alter behavior with @alternate,
		as easter egg/extra mode"""
		return self._content_source

	def get_actions(self):
		"""Default (builtin) actions for this Leaf"""
		return ()

class FileLeaf (Leaf, TextRepresentation):
	"""
	Represents one file
	"""
	serilizable = True
	# To save memory with (really) many instances
	__slots__ = ("name", "object")

	def __init__(self, obj, name=None):
		"""Construct a FileLeaf

		The display name of the file is normally derived from the full path,
		and @name should normally be left unspecified.

		@obj: byte string (file system encoding)
		@name: unicode name or None for using basename
		"""
		if obj is None:
			raise InvalidLeafError("File path for %s may not be None" % name)
		# Use glib filename reading to make display name out of filenames
		# this function returns a `unicode` object
		if not name:
			name = gobject.filename_display_basename(obj)
		super(FileLeaf, self).__init__(obj, name)

	def __eq__(self, other):
		try:
			return (type(self) == type(other) and
					unicode(self) == unicode(other) and
					path.samefile(self.object, other.object))
		except OSError, exc:
			pretty.print_debug(__name__, exc)
			return False

	def repr_key(self):
		return self.object

	def canonical_path(self):
		"""Return the true path of the File (without symlinks)"""
		return path.realpath(self.object)

	def is_valid(self):
		return os.access(self.object, os.R_OK)

	def _is_executable(self):
		return os.access(self.object, os.R_OK | os.X_OK)

	def is_dir(self):
		return path.isdir(self.object)

	def get_text_representation(self):
		return gobject.filename_display_name(self.object)

	def get_description(self):
		"""Format the path shorter:
		replace homedir by ~/
		"""
		return utils.get_display_path_for_bytestring(self.canonical_path())

	def get_actions(self):
		acts = [RevealFile(), ]
		app_actions = []
		default = None
		if self.is_dir():
			acts.append(OpenTerminal())
			default = OpenDirectory()
		elif self.is_valid():
			gfile = gio.File(self.object)
			info = gfile.query_info(gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE)
			content_type = info.get_attribute_string(gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE)
			def_app = gio.app_info_get_default_for_type(content_type, False)
			def_key = def_app.get_id() if def_app else None
			apps_for_type = gio.app_info_get_all_for_type(content_type)
			apps = {}
			for info in apps_for_type:
				key = info.get_id()
				if key not in apps:
					try:
						is_default = (key == def_key)
						app = OpenWith(info, is_default)
						apps[key] = app
					except InvalidDataError:
						pass
			if def_key:
				if not def_key in apps:
					pretty.print_debug("No default found for %s, but found %s" % (self, apps))
				else:
					app_actions.append(apps.pop(def_key))
			# sort the non-default OpenWith actions
			open_with_sorted = locale_sort(apps.values())
			app_actions.extend(open_with_sorted)

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
		return self.is_dir() or Leaf.has_content(self)
	def content_source(self, alternate=False):
		if self.is_dir():
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
			return AppLeaf(init_path=obj)
		except InvalidDataError:
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

	def repr_key(self):
		return repr(self.object)

	def content_source(self, alternate=False):
		return self.object

	def get_description(self):
		return self.object.get_description()

	def get_gicon(self):
		return self.object.get_gicon()

	def get_icon_name(self):
		return self.object.get_icon_name()

class AppLeaf (Leaf, pretty.OutputMixin):
	def __init__(self, item=None, init_path=None, app_id=None):
		"""Try constructing an Application for GAppInfo @item,
		for file @path or for package name @app_id.
		"""
		self.init_item = item
		self.init_path = init_path
		self.init_item_id = app_id and app_id + ".desktop"
		# finish will raise InvalidDataError on invalid item
		self.finish()
		Leaf.__init__(self, self.object, self.object.get_name())
		self.name_aliases.update(self._get_aliases())

	def _get_aliases(self):
		# find suitable alias
		# use package name: non-extension part of ID
		lowername = unicode(self).lower()
		package_name = self._get_package_name()
		if package_name and package_name not in lowername:
			yield package_name

	def __getstate__(self):
		self.init_item_id = self.object and self.object.get_id()
		state = dict(vars(self))
		state["object"] = None
		state["init_item"] = None
		return state

	def __setstate__(self, state):
		vars(self).update(state)
		self.finish()

	def finish(self):
		"""Try to set self.object from init's parameters"""
		item = None
		if self.init_item:
			item = self.init_item
		else:
			# Construct an AppInfo item from either path or item_id
			from gio.unix import DesktopAppInfo, desktop_app_info_new_from_filename
			if self.init_path and os.access(self.init_path, os.X_OK):
				item = desktop_app_info_new_from_filename(self.init_path)
				try:
					# try to annotate the GAppInfo object
					item.init_path = self.init_path
				except AttributeError, exc:
					self.output_debug(exc)
			elif self.init_item_id:
				try:
					item = DesktopAppInfo(self.init_item_id)
				except RuntimeError:
					self.output_debug(self, "Application", self.init_item_id,
							"not found")
		self.object = item
		if not self.object:
			raise InvalidDataError

	def repr_key(self):
		return self.get_id()

	def _get_package_name(self):
		return os.path.basename(self.get_id())

	def get_id(self):
		"""Return the unique ID for this app.

		This is the GIO id "gedit.desktop" minus the .desktop part for
		system-installed applications.
		"""
		return launch.application_id(self.object)

	def get_actions(self):
		if launch.application_is_running(self.object):
			yield Launch(_("Go To"), is_running=True)
			yield CloseAll()
		else:
			yield Launch()
		yield LaunchAgain()

	def get_description(self):
		# Use Application's description, else use executable
		# for "file-based" applications we show the path
		app_desc = tounicode(self.object.get_description())
		ret = tounicode(app_desc if app_desc else self.object.get_executable())
		if self.init_path:
			app_path = utils.get_display_path_for_bytestring(self.init_path)
			return u"(%s) %s" % (app_path, ret)
		return ret

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

	def repr_key(self):
		"""by default, actions of one type are all the same"""
		return ""

	def activate(self, leaf, obj=None):
		"""Use this action with @leaf and @obj

		@leaf: the object (Leaf)
		@obj: an indirect object (Leaf), if self.requires_object
		"""
		pass

	def is_factory(self):
		"""Return whether action may return a result collection as a Source"""
		return False

	def has_result(self):
		"""Return whether action may return a result item as a Leaf"""
		return False

	def is_async(self):
		"""If this action runs asynchronously, return True.

		Then activate(..) must return an object from the kupfer.task module,
		which will be queued to run by Kupfer's task scheduler.
		"""
		return False

	def item_types(self):
		"""Yield types this action may apply to. This is used only
		when this action is specified in __kupfer_actions__ to "decorate"
		"""
		return ()

	def valid_for_item(self, item):
		"""Whether action can be used with exactly @item"""
		return True

	def requires_object(self):
		"""If this action requires a secondary object
		to complete is action, return True
		"""
		return False

	def object_source(self, for_item=None):
		"""Source to use for object or None,
		to use the catalog (flat and filtered for @object_types)
		"""
		return None

	def object_types(self):
		"""Yield types this action may use as indirect objects, if the action
		requrires it.
		"""
		return ()

	def get_icon_name(self):
		return "gtk-execute"

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
			raise InvalidDataError

		name = desktop_item.get_name()
		action_name = _("Open") if is_default else _("Open with %s") % name
		Action.__init__(self, action_name)
		self.desktop_item = desktop_item
		self.is_default = is_default

		# add a name alias from the package name of the application
		if is_default:
			self.rank_adjust = 5
			self.name_aliases.add(_("Open with %s") % name)
		package_name, ext = path.splitext(self.desktop_item.get_id() or "")
		if package_name:
			self.name_aliases.add(_("Open with %s") % package_name)

	def repr_key(self):
		return "" if self.is_default else self.desktop_item.get_id()

	def activate(self, leaf):
		if not self.desktop_item.supports_files() and not self.desktop_item.supports_uris():
			pretty.print_error(__name__, self.desktop_item,
				"says it does not support opening files, still trying to open")
		utils.launch_app(self.desktop_item, paths=(leaf.object,))

	def get_description(self):
		if self.is_default:
			return _("Open with %s") % self.desktop_item.get_name()
		else:
			# no description is better than a duplicate title
			#return _("Open with %s") % self.desktop_item.get_name()
			return u""
	def get_gicon(self):
		return icons.ComposedIcon(self.get_icon_name(),
				self.desktop_item.get_icon(), emblem_is_fallback=True)
	def get_icon_name(self):
		return "gtk-execute"

class OpenUrl (Action):
	rank_adjust = 5
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
	rank_adjust = 5
	def __init__(self, name=_("Open")):
		super(Show, self).__init__(name)
	
	def activate(self, leaf):
		utils.show_path(leaf.object)

	def get_description(self):
		return _("Open with default viewer")

	def get_icon_name(self):
		return "gtk-execute"

class OpenDirectory (Show):
	rank_adjust = 5
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
	def __init__(self, name=_("Open Terminal Here")):
		super(OpenTerminal, self).__init__(name)
	
	def activate(self, leaf):
		# any: take first successful command
		any(utils.spawn_async((term, ), in_dir=leaf.object) for term in
			("xdg-terminal", "gnome-terminal", "xterm"))

	def get_description(self):
		return _("Open this location in a terminal")
	def get_icon_name(self):
		return "terminal"

class Launch (Action):
	"""
	Launch operation base class

	Launches an application (AppLeaf)
	"""
	rank_adjust = 5
	def __init__(self, name=None, is_running=False, open_new=False):
		if not name:
			name = _("Launch")
		Action.__init__(self, name)
		self.is_running = is_running
		self.open_new = open_new
	
	def activate(self, leaf):
		desktop_item = leaf.object
		launch.launch_application(leaf.object, activate=not self.open_new)

	def get_description(self):
		if self.is_running:
			return _("Show application window")
		return _("Launch application")

	def get_icon_name(self):
		if self.is_running:
			return "gtk-jump-to-ltr"
		return Action.get_icon_name(self)

class LaunchAgain (Launch):
	"""Launch instance without checking if running"""
	rank_adjust = 0
	def __init__(self, name=None):
		if not name:
			name = _("Launch Again")
		Launch.__init__(self, name, open_new=True)
	def item_types(self):
		yield AppLeaf
	def valid_for_item(self, leaf):
		return launch.application_is_running(leaf.object)
	def get_description(self):
		return _("Launch another instance of this application")

class CloseAll (Action):
	"""Attept to close all application windows"""
	rank_adjust = -10
	def __init__(self):
		Action.__init__(self, _("Close"))
	def activate(self, leaf):
		return launch.application_close_all(leaf.object)
	def item_types(self):
		yield AppLeaf
	def valid_for_item(self, leaf):
		return launch.application_is_running(leaf.object)
	def get_description(self):
		return _("Attept to close all application windows")
	def get_icon_name(self):
		return "gtk-close"

class Execute (Launch):
	"""
	Execute executable file (FileLeaf)
	"""
	rank_adjust = 5
	def __init__(self, in_terminal=False, quoted=True):
		name = _("Run in Terminal") if in_terminal else _("Run")
		super(Execute, self).__init__(name)
		self.in_terminal = in_terminal
		self.quoted = quoted

	def repr_key(self):
		return (self.in_terminal, self.quoted)
	
	def activate(self, leaf):
		cmd = "'%s'" % leaf.object if self.quoted else leaf.object
		utils.launch_commandline(cmd, in_terminal=self.in_terminal)

	def get_description(self):
		if self.in_terminal:
			return _("Run this program in a Terminal")
		else:
			return _("Run this program")

class Source (KupferObject, pretty.OutputMixin):
	"""
	Source: Data provider for a kupfer browser

	All Sources should be hashable and treated as equal if
	their @repr are equal!

	"""
	def __init__(self, name):
		KupferObject.__init__(self, name)
		self.cached_items = None
		self._version = 1

	@property
	def version(self):
		"""version is for pickling (save and restore from cache),
		subclasses should increase self._version when changing"""
		return self._version

	def __eq__(self, other):
		return type(self) == type(other) and repr(self) == repr(other)

	def __hash__(self ):
		return hash(repr(self))

	def initialize(self):
		"""
		Called when a Source enters Kupfer's system for real

		This method is called at least once for any "real" Source. A Source
		must be able to return an icon name for get_icon_name as well as a
		description for get_description, even if this method was never called.
		"""
		pass

	def repr_key(self):
		# use the source's name so that it is reloaded on locale change
		return (str(self), self.version)

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
		Return a list of all leaves.

		Subclasses should implement get_items, so that Source
		can handle sorting and caching.
		if @force_update, ignore cache, print number of items loaded
		"""
		if self.should_sort_lexically():
			# sort in locale order
			sort_func = locale_sort
		else:
			sort_func = lambda x: x

		if self.is_dynamic():
			return sort_func(self.get_items())
		
		if self.cached_items is None or force_update:
			cache_type = aslist if force_update else datatools.SavedIterable
			self.cached_items = cache_type(sort_func(self.get_items()))
			if force_update:
				self.output_info("Loaded %d items" % len(self.cached_items))
			else:
				self.output_debug("Loaded items")
		return self.cached_items

	def has_parent(self):
		return False

	def get_parent(self):
		return None

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
		name = gobject.filename_display_basename(dir)
		super(DirectorySource, self).__init__(name)
		self.directory = dir
		self.show_hidden = show_hidden
		self.unpickle_finish()

	def __repr__(self):
		return "%s.%s(\"%s\", show_hidden=%s)" % (self.__class__.__module__,
				self.__class__.__name__, str(self.directory), self.show_hidden)

	def unpickle_finish(self):
		self.monitor = self.monitor_directories(self.directory)

	def get_items(self):
		try:
			for fname in os.listdir(self.directory):
				if self.show_hidden or not fname.startswith("."):
					yield ConstructFileLeaf(path.join(self.directory, fname))
		except OSError, exc:
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
		return FileLeaf(self.directory)
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

class AppLeafContentMixin (object):
	"""
	Mixin for Source that correspond one-to-one with a AppLeaf

	This Mixin sees to that the Source is set as content for the application
	with id 'cls.appleaf_content_id', which may also be a sequence of ids.

	Source has to define the attribute appleaf_content_id and must
	inherit this mixin BEFORE the Source

	This Mixin defines:
	get_leaf_repr
	decorates_type,
	decorates_item
	"""
	@classmethod
	def get_leaf_repr(cls):
		if not hasattr(cls, "_cached_leaf_repr"):
			cls._cached_leaf_repr = cls.__get_leaf_repr()
		return cls._cached_leaf_repr
	@classmethod
	def __get_appleaf_id_iter(cls):
		if hasattr(cls.appleaf_content_id, "__iter__"):
			ids = iter(cls.appleaf_content_id)
		else:
			ids = (cls.appleaf_content_id, )
		return ids
	@classmethod
	def __get_leaf_repr(cls):
		for appleaf_id in cls.__get_appleaf_id_iter():
			try:
				return AppLeaf(app_id=appleaf_id)
			except InvalidDataError:
				pass
	@classmethod
	def decorates_type(cls):
		return AppLeaf
	@classmethod
	def decorate_item(cls, leaf):
		if leaf == cls.get_leaf_repr():
			return cls()

class UrlLeaf (Leaf, TextRepresentation):
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

class RunnableLeaf (Leaf):
	"""Leaf where the Leaf is basically the action itself,
	for items such as Quit, Log out etc. Is executed by the
	only action Perform
	"""
	def __init__(self, obj=None, name=None):
		Leaf.__init__(self, obj, name)
	def get_actions(self):
		yield Perform()
	def run(self):
		raise NotImplementedError
	def repr_key(self):
		return ""
	def get_gicon(self):
		iname = self.get_icon_name()
		if iname:
			return icons.get_gicon_with_fallbacks(None, (iname, ))
		return icons.ComposedIcon("kupfer-object", "gtk-execute")
	def get_icon_name(self):
		return ""

class Perform (Action):
	"""Perform the action in a RunnableLeaf"""
	rank_adjust = 5
	def __init__(self, name=None):
		if not name: name = _("Perform")
		super(Perform, self).__init__(name=name)
	def activate(self, leaf):
		return leaf.run()
	def get_description(self):
		return _("Carry out command")

class TextLeaf (Leaf, TextRepresentation):
	"""Represent a text query
	represented object is the unicode string
	"""
	serilizable = True
	def __init__(self, text, name=None):
		"""@text *must* be unicode or UTF-8 str"""
		text = tounicode(text)
		if not name:
			lines = [l for l in text.splitlines() if l.strip()]
			name = lines[0] if lines else text
		Leaf.__init__(self, text, name)

	def get_actions(self):
		return ()

	def repr_key(self):
		return hash(self.object)

	def get_description(self):
		lines = [l for l in self.object.splitlines() if l.strip()]
		desc = lines[0] if lines else self.object
		numlines = len(lines) or 1

		# TRANS: This is description for a TextLeaf, a free-text search
		# TRANS: The plural parameter is the number of lines %(num)d
		return ngettext('"%(text)s"', '(%(num)d lines) "%(text)s"',
			numlines) % {"num": numlines, "text": desc }

	def get_icon_name(self):
		return "gtk-select-all"

class TextSource (KupferObject):
	"""TextSource base class implementation,

	this is a psedo Source"""
	def __init__(self, name=None):
		if not name:
			name = _("Text Matches")
		KupferObject.__init__(self, name)

	def __eq__(self, other):
		return (type(self) == type(other) and repr(self).__eq__(repr(other)))

	def __hash__(self ):
		return hash(repr(self))

	def initialize(self):
		pass

	def get_rank(self):
		"""All items are given this rank"""
		return 20

	def get_items(self, text):
		"""Get leaves for unicode string @text"""
		return ()

	def has_parent(self):
		return False

	def provides(self):
		"""A seq of the types of items it provides"""
		yield Leaf

class TimedPerform (Perform):
	"""A timed proxy version of Perform

	Proxy factory/result/async from a delegate action
	Delay action by a couple of seconds
	"""
	def __init__(self):
		Action.__init__(self, _("Run After Delay..."))

	def activate(self, leaf, iobj=None):
		from kupfer import scheduler
		# make a timer that will fire when Kupfer exits
		interval = utils.parse_time_interval(iobj.object)
		pretty.print_debug(__name__, "Run %s in %s seconds" % (leaf, interval))
		timer = scheduler.Timer(True)
		timer.set(interval, leaf.run)

	def requires_object(self):
		return True
	def object_types(self):
		yield TextLeaf

	def valid_object(self, iobj, for_item=None):
		interval = utils.parse_time_interval(iobj.object)
		return interval > 0

	def get_description(self):
		return _("Perform command after a specified time interval")

class ComposedLeaf (RunnableLeaf):
	serilizable = True
	def __init__(self, obj, action, iobj=None):
		object_ = (obj, action, iobj)
		# A slight hack: We remove trailing ellipsis and whitespace
		format = lambda o: unicode(o).strip(".… ")
		name = u" → ".join([format(o) for o in object_ if o is not None])
		RunnableLeaf.__init__(self, object_, name)

	def __getstate__(self):
		from kupfer import puid
		state = dict(vars(self))
		state["object"] = [puid.get_unique_id(o) for o in self.object]
		return state

	def __setstate__(self, state):
		from kupfer import puid
		vars(self).update(state)
		objid, actid, iobjid = state["object"]
		obj = puid.resolve_unique_id(objid)
		act = puid.resolve_action_id(actid, obj)
		iobj = puid.resolve_unique_id(iobjid)
		if (not obj or not act) or (iobj is None) != (iobjid is None):
			raise InvalidDataError("Parts of %s not restored" % unicode(self))
		self.object[:] = [obj, act, iobj]

	def get_actions(self):
		yield Perform()
		yield TimedPerform()

	def repr_key(self):
		return self

	def run(self):
		from kupfer import commandexec
		ctx = commandexec.DefaultActionExecutionContext()
		obj, action, iobj = self.object
		return ctx.run(obj, action, iobj, delegate=True)

	def get_gicon(self):
		obj, action, iobj = self.object
		return icons.ComposedIcon(obj.get_icon(), action.get_icon())

class _MultipleLeafContentSource (Source):
	def __init__(self, leaf):
		Source.__init__(self, unicode(leaf))
		self.leaf = leaf
	def get_items(self):
		return self.leaf.object

class MultipleLeaf (Leaf):
	"""
	A Leaf representing a collection of leaves.

	The represented object is a frozenset of the contained Leaves
	"""
	def __init__(self, obj, name):
		Leaf.__init__(self, frozenset(obj), name)

	def has_content(self):
		return True

	def content_source(self, alternate=False):
		return _MultipleLeafContentSource(self)

	def get_description(self):
		n = len(self.object)
		return ngettext("%s object", "%s objects", n) % (n, )
	def get_gicon(self):
		pass
