import os
import gio

from kupfer import icons
from kupfer import pretty
from kupfer import utils

from kupfer.obj.base import Action, InvalidDataError

def get_actions_for_file(fileleaf):
	acts = [RevealFile(), ]
	if fileleaf.is_dir():
		acts.append(OpenTerminal())
	elif fileleaf.is_valid():
		if fileleaf._is_executable():
			acts.extend((Execute(), Execute(in_terminal=True)))
	return [Show()] + acts

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

