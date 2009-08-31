import os

import dbus
import gobject

from kupfer.objects import Source, Leaf, FileLeaf, SourceLeaf, PicklingHelperMixin
from kupfer import objects
from kupfer.helplib import WeakCallback

__kupfer_name__ = _("Selected File")
__kupfer_sources__ = ("SelectionSource", )
__description__ = _("Provides current nautilus selection, using Kupfer's Nautilus Extension")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class SelectedFile (FileLeaf):
	def __init__(self, filepath):
		"""@filepath is a filesystem byte string `str`"""
		basename = gobject.filename_display_basename(filepath)
		FileLeaf.__init__(self, filepath, _('Selected File "%s"') % basename)

	def rank_key(self):
		# return a constant rank key despite the changing name
		return _("Selected File")

class InvisibleSourceLeaf (SourceLeaf):
	"""Hack to hide this source"""
	def is_valid(self):
		return False

class SelectionSource (Source, PicklingHelperMixin):
	def __init__(self):
		Source.__init__(self, _("Selected File"))
		self.unpickle_finish()

	def unpickle_finish(self):
		session_bus = dbus.Bus()
		session_bus.add_signal_receiver(
				WeakCallback(self, "_selected_signal"),
				"SelectionChanged",
				dbus_interface="se.kaizer.KupferNautilusPlugin",
				byte_arrays=True)
		self._selection = []

	def _selected_signal(self, selection):
		self._selection = selection
		self.mark_for_update()

	def get_items(self):
		if len(self._selection) == 1:
			yield SelectedFile(self._selection[0])

	def get_description(self):
		return None
	def provides(self):
		yield FileLeaf
	def get_leaf_repr(self):
		return InvisibleSourceLeaf(self)
