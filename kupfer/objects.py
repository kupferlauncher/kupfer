# -*- coding: UTF-8 -*-

"""
Copyright 2007--2009 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""

import itertools
from os import path

import gobject
import gio

from kupfer import pretty
from kupfer import icons, launch, utils
from kupfer.utils import locale_sort

class Error (Exception):
	pass

class InvalidDataError (Error):
	"""The data is wrong for the given Leaf"""
	pass

class InvalidLeafError (Error):
	"""The Leaf passed to an Action is invalid"""
	pass

def tounicode(utf8str):
	"""Return `unicode` from UTF-8 encoded @utf8str
	This is to use the same error handling etc everywhere
	"""
	return utf8str.decode("UTF-8", "replace") if utf8str is not None else u""

def toutf8(ustr):
	"""Return UTF-8 `str` from unicode @ustr
	This is to use the same error handling etc everywhere
	if ustr is `str`, just return it
	"""
	if isinstance(ustr, str):
		return ustr
	return ustr.encode("UTF-8", "replace")

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
	"""
	Make lists from sequences that are not lists or tuples

	For iterators, sets etc.
	"""
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

class DummyLeaf (Leaf):
	"""
	Dummy Leaf, representing No Leaf available
	"""
	def __init__(self):
		super(DummyLeaf, self).__init__(None, _("No matches"))

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

	def repr_key(self):
		return self.object

	def is_valid(self):
		from os import access, R_OK
		return access(self.object, R_OK)

	def _is_executable(self):
		from os import access, X_OK, R_OK
		return access(self.object, R_OK | X_OK)

	def is_dir(self):
		return path.isdir(self.object)

	def get_description(self):
		"""Format the path shorter:
		replace homedir by ~/
		"""
		return utils.get_display_path_for_bytestring(self.object)

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

	def content_source(self, alternate=False):
		return self.object

	def get_description(self):
		return self.object.get_description()

	def get_gicon(self):
		return self.object.get_gicon()

	def get_icon_name(self):
		return self.object.get_icon_name()

class AppLeaf (Leaf, PicklingHelperMixin, pretty.OutputMixin):
	def __init__(self, item=None, init_path=None, app_id=None):
		"""Try constructing an Application for GAppInfo @item,
		for file @path or for package name @app_id.
		"""
		self.init_item = item
		self.init_path = init_path
		self.init_item_id = app_id and app_id + ".desktop"
		# unpickle_finish will raise InvalidDataError on invalid item
		self.unpickle_finish()
		Leaf.__init__(self, self.object, self.object.get_name())
		self.name_aliases = self._get_aliases()

	def _get_aliases(self):
		# find suitable aliases
		name_aliases = set()
		# use package name: non-extension part of ID
		lowername = unicode(self).lower()
		package_name = self._get_package_name()
		if package_name and package_name not in lowername:
			name_aliases.add(package_name)
		# FIXME: We don't use the executable since package name is better
		# newer versions have get_commandline
		# executable = getattr(self.object, "get_commandline", self.object.get_executable)()
		# invalid_execs = set(("env", "sudo", "su-to-root", "gksu", "gksudo"))
		return name_aliases

	def pickle_prepare(self):
		self.init_item_id = self.object and self.object.get_id()
		self.object = None
		self.init_item = None

	def unpickle_finish(self):
		"""Try to set self.object from init's parameters"""
		item = None
		if self.init_item:
			item = self.init_item
		else:
			# Construct an AppInfo item from either path or item_id
			from gio.unix import DesktopAppInfo, desktop_app_info_new_from_filename
			if self.init_path:
				item = desktop_app_info_new_from_filename(self.init_path)
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
		return self.get_id() or self

	def _get_package_name(self):
		package_name, ext = path.splitext(self.object.get_id() or "")
		return package_name

	def get_id(self):
		"""Return the unique ID for this app.

		This is the GIO id "gedit.desktop" minus the .desktop part
		"""
		return self._get_package_name()

	def get_actions(self):
		if launch.application_is_running(self.object):
			yield ShowApplication()
			yield LaunchAgain()
		else:
			yield Launch()

	def get_description(self):
		"""Use Application's description, else use executable"""
		app_desc = self.object.get_description()
		return tounicode(app_desc if app_desc else self.object.get_executable())

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
		"""
		Use this action with @leaf and @obj

		@leaf: the object (Leaf)
		@obj: an indirect object (Leaf), if self.requires_object
		"""
		pass

	def is_factory(self):
		"""
		If this action returns a new source in activate
		return True
		"""
		return False

	def is_async(self):
		"""
		If this action should run on a separate thread, return True.
		activate(..) should return a tuple of two functions
		(start_cb, finish_cb) with the following signatures:
			start_cb (leaf, obj=None)
			finish_cb (retval)
		finish_cb is passed the return value from start_cb

		start_cb is called asynchronously, then finish_cb is called,
		if start_cb does not raise, on the main thread.
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
		self.name_aliases = set()
		if is_default:
			self.rank_adjust = 5
			self.name_aliases.add(_("Open with %s") % name)
		package_name, ext = path.splitext(self.desktop_item.get_id() or "")
		if package_name:
			self.name_aliases.add(_("Open with %s") % package_name)

	def repr_key(self):
		return self

	def activate(self, leaf):
		if not self.desktop_item.supports_files() and not self.desktop_item.supports_uris():
			print self, "does not support opening files"
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
	rank_adjust = 5
	def __init__(self, name=None):
		if not name:
			name = _("Go To")
		Launch.__init__(self, name, open_new=False)

	def get_description(self):
		return _("Show application window")
	def get_icon_name(self):
		return "gtk-jump-to-ltr"

class LaunchAgain (Launch):
	"""Launch instance without checking if running"""
	rank_adjust = 0
	def __init__(self, name=None):
		if not name:
			name = _("Launch Again")
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

	def repr_key(self):
		return self.in_terminal
	
	def activate(self, leaf):
		cli = "%s %s" % (leaf.object, self.args)
		utils.launch_commandline(cli, in_terminal=self.in_terminal)

	def get_description(self):
		if self.in_terminal:
			return _("Run this program in a Terminal")
		else:
			return _("Run this program")

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
			self.cached_items = aslist(sort_func(self.get_items()))
			if force_update:
				self.output_info("Loaded %d items" % len(self.cached_items))
			else:
				self.output_debug("Loaded %d items" % len(self.cached_items))
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

class FilesystemWatchMixin (object):
	"""A mixin for Sources watching directories"""

	def monitor_directories(self, *directories):
		"""Register @directories for monitoring;

		On changes, the Source will be marked for update.
		This method returns a monitor token that has to be
		stored for the monitor to be active; and it can not be pickled.
		The token will be a false value if nothing could be monitored.

		Nonexisting directories are skipped.
		"""
		tokens = []
		for directory in directories:
			gfile = gio.File(directory)
			if not gfile.query_exists():
				continue
			monitor = gfile.monitor_directory(gio.FILE_MONITOR_NONE, None)
			if monitor:
				monitor.connect("changed", self.__directory_changed)
				tokens.append(monitor)
		return tokens

	def monitor_include_file(self, gfile):
		"""Return whether @gfile should trigger an update event
		by default, files beginning with "." are ignored
		"""
		return not (gfile and gfile.get_basename().startswith("."))

	def __directory_changed(self, monitor, file1, file2, evt_type):
		if (evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
				gio.FILE_MONITOR_EVENT_DELETED) and
				self.monitor_include_file(file1)):
			self.mark_for_update()

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

	def pickle_prepare(self):
		# the monitor token is not pickleable
		self.monitor = None

	def unpickle_finish(self):
		self.monitor = self.monitor_directories(self.directory)

	def get_items(self):
		exclude = lambda f: f.startswith(".") if not self.show_hidden else None
		dirlist = utils.get_dirlist(self.directory, exclude=exclude)
		def file_leaves(files):
			for file in files:
				yield ConstructFileLeaf(file)

		return file_leaves(dirlist)
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

class RunnableLeaf (Leaf):
	"""Leaf where the Leaf is basically the action itself,
	for items such as Quit, Log out etc. Is executed by the
	only action Do
	"""
	def __init__(self, obj=None, name=None):
		Leaf.__init__(self, obj, name)
	def get_actions(self):
		yield Do()
	def run(self):
		raise NotImplementedError

class Do (Action):
	"""Perform the action in a RunnableLeaf"""
	def __init__(self, name=None):
		if not name: name = _("Do")
		super(Do, self).__init__(name=name)
	def activate(self, leaf):
		leaf.run()
	def get_description(self):
		return _("Perform action")

class TextLeaf (Leaf):
	"""Represent a text query
	represented object is the unicode string
	"""
	def __init__(self, text, name=None):
		"""@text *must* be unicode or UTF-8 str"""
		text = tounicode(text)
		if not name:
			lines = [l for l in text.splitlines() if l.strip()]
			name = lines[0] if lines else text
		Leaf.__init__(self, text, name)

	def get_actions(self):
		return ()

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

	def get_rank(self):
		"""All items are given this rank"""
		return 50
	# This is not yet implemented
	#def has_ranked_items(self):
	#"""If True, use get_ranked_items(), else get_items()"""
	#def get_ranked_items(self, text):
	#"""Return a sequence of tuple of (item, rank)"""
	def get_items(self, text):
		"""Get leaves for unicode string @text"""
		return ()
	def provides(self):
		"""A seq of the types of items it provides"""
		yield Leaf

