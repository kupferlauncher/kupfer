
__kupfer_name__ = _("Send Keys")
__kupfer_actions__ = (
	"CopyAndPaste",
	"SendKeys",
	"TypeText",
	)
__description__ = _("Send synthetic keyboard events using "
                    "xautomation")
__version__ = ""
__author__ = ""

import gtk

from kupfer.objects import Leaf, Action, TextLeaf
from kupfer.objects import OperationError
from kupfer import utils
from kupfer import interface


class CopyAndPaste (Action):
	# rank down since it applies everywhere
	rank_adjust = -2
	def __init__(self):
		Action.__init__(self, _("Paste to Foreground Window"))
	def activate(self, leaf):
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
		interface.copy_to_clipboard(leaf, clip)
		xte_paste_argv = ['xte', 'usleep 300000', 'keydown Control_L',
		                  'key v', 'keyup Control_L']
		try:
			utils.spawn_async_raise(xte_paste_argv)
		except utils.SpawnError as exc:
			raise OperationError(exc)
	def item_types(self):
		yield Leaf
	def valid_for_item(self, leaf):
		try:
			return bool(interface.get_text_representation(leaf))
		except AttributeError:
			pass
	def get_description(self):
		return _("Copy to clipboard and send Ctrl+V to foreground window")
	def get_icon_name(self):
		return "edit-paste"

class SendKeys (Action):
	def __init__(self):
		Action.__init__(self, _("Send Keys"))
	def activate(self, leaf):
		text = leaf.object
		keys, orig_mods = gtk.accelerator_parse(text)
		m = {
			gtk.gdk.SHIFT_MASK: "Shift_L",
			gtk.gdk.CONTROL_MASK: "Control_L",
			gtk.gdk.SUPER_MASK: "Super_L",
			gtk.gdk.MOD1_MASK: "Alt_L",
		}
		mod_names = []
		mods = orig_mods
		for mod in m:
			if mod & mods:
				mod_names.append(m[mod])
				mods &= ~mod
		if mods != 0:
			raise OperationError("Keys not yet implemented: %s" %
					gtk.accelerator_get_label(keys, orig_mods))
		key_arg = 'key %s' % (gtk.gdk.keyval_name(keys), )
		mods_down = ['keydown ' + n for n in mod_names]
		mods_up = ['keyup ' + n for n in reversed(mod_names)]

		xte_paste_argv = ['xte', 'usleep 300000'] + \
				mods_down + [key_arg] + mods_up
		try:
			utils.spawn_async_raise(xte_paste_argv)
		except utils.SpawnError as exc:
			raise OperationError(exc)
	def item_types(self):
		yield TextLeaf
	def valid_for_item(self, leaf):
		text = leaf.object
		keys, mods = gtk.accelerator_parse(text)
		return keys
	def get_description(self):
		return _("Send keys to foreground window")

class TypeText (Action):
	rank_adjust = -2 
	def __init__(self):
		Action.__init__(self, _("Type Text"))
	def activate(self, leaf):
		text = interface.get_text_representation(leaf)
		xte_paste_argv = ['xte', 'usleep 300000']
		# replace all newlines with 'key Return'
		for line in text.splitlines(True):
			xte_paste_argv.append("str " + line.rstrip("\r\n"))
			if line.endswith("\n"):
				xte_paste_argv.append("key Return")
		try:
			utils.spawn_async_raise(xte_paste_argv)
		except utils.SpawnError as exc:
			raise OperationError(exc)
	def item_types(self):
		yield Leaf
	def valid_for_item(self, leaf):
		try:
			return bool(interface.get_text_representation(leaf))
		except AttributeError:
			pass
	def get_description(self):
		return _("Type the text to foreground window")

