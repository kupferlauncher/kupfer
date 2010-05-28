__kupfer_name__ = _("Thunar")
__kupfer_sources__ = ("ThunarObjects", )
__kupfer_actions__ = (
	"Reveal",
	"GetInfo",
	"SendTo",
)
__description__ = _("File manager Thunar actions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os

import dbus
import gio

from kupfer.objects import Leaf, Action, Source
from kupfer.objects import FileLeaf, RunnableLeaf, SourceLeaf, AppLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import config
from kupfer import plugin_support
from kupfer import pretty
from kupfer import utils

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


class SendTo (Action):
	""" Send files to  selected app from "send to" list """
	def __init__(self):
		Action.__init__(self, _("Send To..."))

	def activate_multiple(self, leaves, iobjs):
		for app in iobjs:
			utils.launch_app(app.object, paths=[leaf.object for leaf in leaves])

	def activate(self, leaf, iobj):
		self.activate_multiple((leaf, ), (iobj, ))

	def item_types(self):
		yield FileLeaf

	def requires_object(self):
		return True

	def object_types(self):
		yield AppLeaf

	def object_source(self, for_item=None):
		return _SendToAppsSource()


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

class ThunarObjects (AppLeafContentMixin, Source):
	appleaf_content_id = "Thunar"
	def __init__(self):
		Source.__init__(self, _("Thunar"))

	def get_items(self):
		yield EmptyTrash()

	def provides(self):
		yield RunnableLeaf


class _SendToAppsSource (Source):
	""" Send To items source """
	def __init__(self):
		Source.__init__(self, _("Thunar Send To Objects"))

	def get_items(self):
		for data_dir in config.get_data_dirs("sendto", package="Thunar"):
			for filename in os.listdir(data_dir):
				if not filename.endswith('.desktop'):
					continue
				file_path = os.path.join(data_dir, filename)
				if not os.path.isfile(file_path):
					continue
				item = gio.unix.desktop_app_info_new_from_filename(file_path)
				if item:
					yield AppLeaf(item)

	def get_icon_name(self):
		return "Thunar"

	def provides(self):
		yield AppLeaf
