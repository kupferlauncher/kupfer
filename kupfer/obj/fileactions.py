import os
import gio

from kupfer import icons
from kupfer import pretty
from kupfer import utils
from kupfer import launch

from kupfer.obj.base import Action, InvalidDataError, OperationError

class NoDefaultApplicationError (OperationError):
	pass

def is_good_executable(fileleaf):
	if not fileleaf._is_executable():
		return False
	ctype, uncertain = gio.content_type_guess(fileleaf.object, None, True)
	return uncertain or gio.content_type_can_be_executable(ctype)

def get_actions_for_file(fileleaf):
	acts = [RevealFile(), ]
	if fileleaf.is_dir():
		acts.append(OpenTerminal())
	elif fileleaf.is_valid():
		if is_good_executable(fileleaf):
			acts.extend((Execute(), Execute(in_terminal=True)))
	return [Open()] + acts

class Open (Action):
	""" Open with default application """
	rank_adjust = 5
	def __init__(self, name=_("Open")):
		Action.__init__(self, name)

	@classmethod
	def default_application_for_leaf(cls, leaf):
		content_attr = gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE
		gfile = gio.File(leaf.object)
		info = gfile.query_info(content_attr)
		content_type = info.get_attribute_string(content_attr)
		def_app = gio.app_info_get_default_for_type(content_type, False)
		if not def_app:
			apps_for_type = gio.app_info_get_all_for_type(content_type)
			raise NoDefaultApplicationError(
					(_("No default application for %(file)s (%(type)s)") % 
					 {"file": unicode(leaf), "type": content_type}) + "\n" +
					_('Please use "%s"') % _("Set Default Application...")
				)
		return def_app

	def wants_context(self):
		return True

	def activate(self, leaf, ctx):
		self.activate_multiple((leaf, ), ctx)

	def activate_multiple(self, objects, ctx):
		appmap = {}
		leafmap = {}
		for obj in objects:
			app = self.default_application_for_leaf(obj)
			id_ = app.get_id()
			appmap[id_] = app
			leafmap.setdefault(id_, []).append(obj)

		for id_, leaves in leafmap.iteritems():
			app = appmap[id_]
			launch.launch_application(app, paths=[L.object for L in leaves],
			                          activate=False,
			                          screen=ctx and ctx.environment.get_screen())

	def get_description(self):
		return _("Open with default application")

	def get_icon_name(self):
		return "gtk-execute"

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
		try:
			utils.spawn_terminal(leaf.object)
		except utils.SpawnError as exc:
			raise OperationError(exc)

	def get_description(self):
		return _("Open this location in a terminal")
	def get_icon_name(self):
		return "terminal"

class Execute (Action):
	""" Execute executable file (FileLeaf) """
	rank_adjust = 10
	def __init__(self, in_terminal=False, quoted=True):
		name = _("Run in Terminal") if in_terminal else _("Run (Execute)")
		super(Execute, self).__init__(name)
		self.in_terminal = in_terminal
		self.quoted = quoted

	def repr_key(self):
		return (self.in_terminal, self.quoted)
	
	def activate(self, leaf):
		if self.quoted:
			argv = [leaf.object]
		else:
			argv = utils.argv_for_commandline(leaf.object)
		if self.in_terminal:
			utils.spawn_in_terminal(argv)
		else:
			utils.spawn_async(argv)

	def get_description(self):
		if self.in_terminal:
			return _("Run this program in a Terminal")
		else:
			return _("Run this program")

