
__kupfer_name__ = _("Paste")
__kupfer_actions__ = (
	"CopyAndPaste",
	)
__description__ = _("Copy to clipboard and send Ctrl+V to foreground window")
__version__ = ""
__author__ = ""

import gtk

from kupfer.objects import Leaf, Action, Source, OperationError
from kupfer import pretty
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
		if not utils.spawn_async(xte_paste_argv):
			raise OperationError(_("Command '%s' not found!") % ("xte", ))
	def item_types(self):
		yield Leaf
	def valid_for_item(self, leaf):
		try:
			return bool(interface.get_text_representation(leaf))
		except AttributeError:
			pass
	def get_description(self):
		return __description__
	def get_icon_name(self):
		return "edit-paste"
