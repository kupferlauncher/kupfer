# -*- coding: UTF-8 -*-

"""
Copyright 2007--2009 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""

import os
from os import path

import gobject
import gio

from kupfer import icons, launch, utils
from kupfer import pretty
from kupfer.utils import locale_sort
from kupfer.obj.base import Leaf, Action, Source, InvalidDataError
from kupfer.obj.helplib import PicklingHelperMixin, FilesystemWatchMixin
from kupfer.interface import TextRepresentation
from kupfer.kupferstring import tounicode

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

def _directory_content(dirpath, show_hidden):
	from kupfer.obj.sources import DirectorySource
	return DirectorySource(dirpath, show_hidden)

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
			raise InvalidDataError("File path for %s may not be None" % name)
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
			return _directory_content(self.object, alternate)
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

