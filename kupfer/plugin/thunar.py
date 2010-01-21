__kupfer_name__ = _("Thunar")
__kupfer_sources__ = ("ThunarObjects", )
__kupfer_actions__ = (
	"Reveal",
	"GetInfo",
	"MoveToTrash",
)
__description__ = _("File manager Thunar actions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os

import dbus
import gio
import glib

from kupfer.objects import Leaf, Action, Source
from kupfer.objects import FileLeaf, RunnableLeaf, SourceLeaf
from kupfer import pretty
from kupfer import plugin_support
from kupfer.weaklib import gobject_connect_weakly


plugin_support.check_dbus_connection()

SERVICE_NAME = "org.xfce.Thunar"
OBJECT_PATH = "/org/xfce/FileManager"
IFACE_NAME = "org.xfce.FileManager"

TRASH_IFACE_NAME = "org.xfce.Trash"

def _get_thunar():
	"""Return the dbus proxy object for Thunar
	we will activate it over d-bus (start if not running)
	"""
	bus = dbus.SessionBus()
	try:
		proxy_obj = bus.get_object(SERVICE_NAME, OBJECT_PATH)
	except dbus.DBusException, e:
		pretty.print_error(__name__, e)
		return
	iface_obj = dbus.Interface(proxy_obj, IFACE_NAME)
	return iface_obj

def _get_thunar_trash():
	"""Return the dbus proxy object for Thunar
	we will activate it over d-bus (start if not running)
	"""
	bus = dbus.SessionBus()
	try:
		proxy_obj = bus.get_object(SERVICE_NAME, OBJECT_PATH)
	except dbus.DBusException, e:
		pretty.print_error(__name__, e)
		return
	iface_obj = dbus.Interface(proxy_obj, TRASH_IFACE_NAME)
	return iface_obj

def _current_display():
	"return the current $DISPLAY"
	return os.getenv("DISPLAY", ":0")

def _dummy(*args):
	pass

class Reveal (Action):
	def __init__(self):
		Action.__init__(self, _("Select in File Manager"))

	def activate(self, leaf):
		gfile = gio.File(leaf.object)
		parent = gfile.get_parent()
		if not parent:
			return
		uri = parent.get_uri()
		bname = gfile.get_basename()
		_get_thunar().DisplayFolderAndSelect(uri, bname, _current_display(),
				reply_handler=_dummy, error_handler=_dummy)

	def item_types(self):
		yield FileLeaf

class GetInfo (Action):
	def __init__(self):
		Action.__init__(self, _("Show Properties"))

	def activate(self, leaf):
		gfile = gio.File(leaf.object)
		uri = gfile.get_uri()
		_get_thunar().DisplayFileProperties(uri, _current_display(),
				reply_handler=_dummy, error_handler=_dummy)

	def item_types(self):
		yield FileLeaf

	def get_description(self):
		return _("Show information about file in file manager")

class EmptyTrash (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, None, _("Empty Trash"))

	def run(self):
		_get_thunar_trash().EmptyTrash(_current_display(),
				reply_handler=_dummy, error_handler=_dummy)

	def get_description(self):
		return None
	def get_icon_name(self):
		return "user-trash-full"

class ThunarObjects (Source):
	def __init__(self):
		Source.__init__(self, _("Thunar"))

	def get_items(self):
		yield EmptyTrash()

	def provides(self):
		yield RunnableLeaf
	def get_leaf_repr(self):
		return InvisibleSourceLeaf(self)

class InvisibleSourceLeaf (SourceLeaf):
	# A hack to hide this source
	def is_valid(self):
		return False
