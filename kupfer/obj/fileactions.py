import os
import gio

from kupfer import icons
from kupfer import pretty
from kupfer import utils

from kupfer.obj.base import Action, InvalidDataError

def get_actions_for_file(fileleaf):
	acts = [RevealFile(), ]
	app_actions = []
	default = None
	if fileleaf.is_dir():
		acts.append(OpenTerminal())
		default = OpenDirectory()
	elif fileleaf.is_valid():
		gfile = gio.File(fileleaf.object)
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
				pretty.print_debug("No default found for %s, but found %s" % (fileleaf, apps))
			else:
				app_actions.append(apps.pop(def_key))
		# sort the non-default OpenWith actions
		open_with_sorted = utils.locale_sort(apps.values())
		app_actions.extend(open_with_sorted)

		if fileleaf._is_executable():
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
		package_name, ext = os.path.splitext(self.desktop_item.get_id() or "")
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
		parent = os.path.normpath(os.path.join(fileloc, os.path.pardir))
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

class Execute (Action):
	""" Execute executable file (FileLeaf) """
	rank_adjust = 5
	def __init__(self, in_terminal=False, quoted=True):
		name = _("Run in Terminal") if in_terminal else _("Run (Execute)")
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

