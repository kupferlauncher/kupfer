import os
# since "path" is a very generic name, you often forget..
from os import path as os_path
import subprocess

from kupfer.objects import Leaf, Action, FileLeaf, TextLeaf
from kupfer import utils, pretty

__kupfer_name__ = _("Image Tools")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
		"Scale",
		"Rotate90",
		"Rotate270",
		"Autorotate",
	)
__description__ = _("Image transformation tools")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class PredefinedSize (Leaf):
	pass

class Scale (Action):
	def __init__(self):
		Action.__init__(self, _("Scale..."))

	def has_result(self):
		return True

	def activate(self, leaf, obj):
		size = self._make_size(obj.object)
		fpath = leaf.object
		dirname = os_path.dirname(fpath)
		head, ext = os_path.splitext(os_path.basename(fpath))
		filename = "%s_%s%s" % (head, size, ext)
		dpath = utils.get_destpath_in_directory(dirname, filename)
		cmdline = "convert -scale '%s' '%s' '%s'" % (size, fpath, dpath)
		utils.launch_commandline(cmdline)
		return FileLeaf(dpath)

	def item_types(self):
		yield FileLeaf

	def valid_for_item(self, item):
		# FIXME: Make this detection smarter
		root, ext = os_path.splitext(item.object)
		return ext.lower() in (".jpeg", ".jpg", ".png", ".gif")

	def requires_object(self):
		return True

	def object_types(self):
		yield PredefinedSize
		yield TextLeaf

	@classmethod
	def _make_size(self, text):
		size = None
		try:
			size = "%g" % float(text.strip())
		except ValueError:
			try:
				twoparts = text.split("x", 1)
				size = "%gx%g" % (float(twoparts[0].strip()),
						float(twoparts[1].strip()))
			except ValueError:
				pass
		return size

	def valid_object(self, obj, for_item=None):
		if isinstance(obj, TextLeaf):
			return self._make_size(obj.object)
		elif isinstance(obj, PredefinedSize):
			return True

	def get_description(self):
		return _("Scale image to fit inside given pixel measure(s)")

class RotateBase (Action):
	def __init__(self, name, rotation):
		Action.__init__(self, name)
		self.rotation = rotation

	def has_result(self):
		return True

	def activate(self, leaf, obj=None):
		fpath = leaf.object
		dirname = os_path.dirname(fpath)
		head, ext = os_path.splitext(os_path.basename(fpath))
		filename = "%s_%s%s" % (head, self.rotation, ext)
		dpath = utils.get_destpath_in_directory(dirname, filename)
		cmdline = ("jpegtran -copy all -rotate '%s' -outfile '%s' '%s'" %
				(self.rotation, dpath, fpath))
		utils.launch_commandline(cmdline)
		return FileLeaf(dpath)

	def item_types(self):
		yield FileLeaf

	def valid_for_item(self, item):
		# FIXME: Make this detection smarter
		root, ext = os_path.splitext(item.object)
		return ext.lower() in (".jpeg", ".jpg")

class Rotate90 (RotateBase):
	def __init__(self):
		RotateBase.__init__(self, _("Rotate Clockwise"), "90")

	def get_icon_name(self):
		return "object-rotate-right"

class Rotate270 (RotateBase):
	def __init__(self):
		RotateBase.__init__(self, _("Rotate Counter-Clockwise"), "270")

	def get_icon_name(self):
		return "object-rotate-left"

class Autorotate (Action):
	def __init__(self):
		Action.__init__(self, _("Autorotate"))

	def has_result(self):
		return True

	def activate(self, leaf, obj=None):
		fpath = leaf.object
		dirname = os_path.dirname(fpath)
		cmdline = "jhead -autorot '%s'" % fpath
		utils.launch_commandline(cmdline)

	def item_types(self):
		yield FileLeaf

	def valid_for_item(self, item):
		root, ext = os_path.splitext(item.object)
		if not ext.lower() in (".jpeg", ".jpg"):
			return False
		# Launch jhead to see if 1) it is installed, 2) Orientation nondefault
		try:
			cmdargs = ("jhead", item.object)
			proc = subprocess.Popen(cmdargs, stdout=subprocess.PIPE)
		except OSError:
			pretty.print_debug(__name__ , "Action %s needs 'jhead'" % self)
		else:
			out, err = proc.communicate()
			pretty.print_debug(__name__, "Running", cmdargs)
			return any(li.startswith("Orientation") for li in out.splitlines())

	def get_description(self):
		return _("Rotate JPEG (in-place) according to its EXIF metadata")

