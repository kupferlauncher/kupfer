import gio
import os
# since "path" is a very generic name, you often forget..
from os import path as os_path

from kupfer.objects import Action, FileLeaf, TextLeaf, TextSource
from kupfer import utils, pretty
from kupfer import plugin_support

__kupfer_name__ = _("File Actions")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
		"Trash",
		"MoveTo",
		"Rename",
		"CopyTo",
		"UnpackHere",
		"CreateArchive",
		"CreateArchiveIn",
	)
__description__ = _("More file actions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "archive_type",
		"label": _("Compressed archive type for 'Create Archive In'"),
		"type": str,
		"value": ".tar.gz",
		"alternatives": (
			".7z",
			".rar",
			".tar",
			".tar.gz",
			".zip",
			)
	},
)

class Trash (Action):
	# this should never be default
	rank_adjust = -10
	def __init__(self):
		Action.__init__(self, _("Move to Trash"))

	def activate(self, leaf):
		gfile = gio.File(leaf.object)
		gfile.trash()
	def valid_for_item(self, item):
		return os.access(item.object, os.R_OK | os.W_OK)
	def get_description(self):
		return _("Move this file to trash")
	def get_icon_name(self):
		return "user-trash-full"
	def item_types(self):
		yield FileLeaf

def _good_destination(dpath, spath):
	"""If directory path @dpath is a valid destination for file @spath
	to be copied or moved to
	"""
	if not os_path.isdir(dpath):
		return False
	spath = os_path.normpath(spath)
	dpath = os_path.normpath(dpath)
	dest_filename = os_path.join(dpath, os_path.basename(spath))
	if os_path.exists(dest_filename):
		return False
	if not os.access(dpath, os.R_OK | os.W_OK | os.X_OK):
		return False
	cpfx = os_path.commonprefix((spath, dpath))
	parent_spath = os_path.dirname(spath)
	if (os_path.samefile(dpath, spath) or (cpfx == spath) or
			(dpath == parent_spath)):
		return False
	return True

class MoveTo (Action, pretty.OutputMixin):
	def __init__(self):
		Action.__init__(self, _("Move To..."))
	def has_result(self):
		return True
	def activate(self, leaf, obj):
		sfile = gio.File(leaf.object)
		bname = sfile.get_basename()
		dfile = gio.File(os_path.join(obj.object, bname))
		try:
			ret = sfile.move(dfile, flags=gio.FILE_COPY_ALL_METADATA)
			self.output_debug("Move %s to %s (ret: %s)" % (sfile, dfile, ret))
		except gio.Error, exc:
			self.output_error("Move %s to %s Error: %s" % (sfile, dfile, exc))
		else:
			return FileLeaf(dfile.get_path())

	def valid_for_item(self, item):
		return os.access(item.object, os.R_OK | os.W_OK)
	def requires_object(self):
		return True

	def item_types(self):
		yield FileLeaf
	def object_types(self):
		yield FileLeaf
	def valid_object(self, obj, for_item):
		return _good_destination(obj.object, for_item.object)
	def get_description(self):
		return _("Move file to new location")

class RenameSource (TextSource):
	"""A source for new names for a file;
	here we "autopropose" the source file's extension,
	but allow overriding it as well as renaming to without
	extension (either using a terminating space, or selecting the
	normal TextSource-returned string).
	"""
	def __init__(self, sourcefile):
		self.sourcefile = sourcefile
		TextSource.__init__(self, _("Rename To..."))

	def get_items(self, text):
		if not text:
			return
		basename = os_path.basename(self.sourcefile.object)
		root, ext = os_path.splitext(basename)
		t_root, t_ext = os_path.splitext(text)
		if text.endswith(u" "):
			yield TextLeaf(text.rstrip())
		else:
			yield TextLeaf(text) if t_ext else TextLeaf(t_root + ext)

	def get_gicon(self):
		return self.sourcefile.get_gicon()

class Rename (Action, pretty.OutputMixin):
	def __init__(self):
		Action.__init__(self, _("Rename To..."))

	def has_result(self):
		return True
	def activate(self, leaf, obj):
		sfile = gio.File(leaf.object)
		bname = sfile.get_basename()
		dest = os_path.join(os_path.dirname(leaf.object), obj.object)
		dfile = gio.File(dest)
		try:
			ret = sfile.move(dfile)
			self.output_debug("Move %s to %s (ret: %s)" % (sfile, dfile, ret))
		except gio.Error, exc:
			self.output_error("Move %s to %s Error: %s" % (sfile, dfile, exc))
		else:
			return FileLeaf(dest)

	def item_types(self):
		yield FileLeaf
	def valid_for_item(self, item):
		return os.access(item.object, os.R_OK | os.W_OK)

	def requires_object(self):
		return True
	def object_types(self):
		yield TextLeaf

	def valid_object(self, obj, for_item):
		dest = os_path.join(os_path.dirname(for_item.object), obj.object)
		return os_path.exists(os_path.dirname(dest)) and \
				not os_path.exists(dest)

	def object_source(self, for_item):
		return RenameSource(for_item)

	def get_description(self):
		return None

class CopyTo (Action, pretty.OutputMixin):
	def __init__(self):
		Action.__init__(self, _("Copy To..."))
		if gio.pygio_version < (2, 18):
			self.output_info("Requires pygobject version 2.18 or later")

	def has_result(self):
		return True

	def _finish_callback(self, gfile, result):
		self.output_debug("Finished copying", gfile)

	def activate(self, leaf, obj):
		sfile = gio.File(leaf.object)
		dpath = os_path.join(obj.object, os_path.basename(leaf.object))
		dfile = gio.File(dpath)
		try:
			ret = sfile.copy_async(dfile, self._finish_callback,
					flags=gio.FILE_COPY_ALL_METADATA)
			self.output_debug("Copy %s to %s (ret: %s)" % (sfile, dfile, ret))
		except gio.Error, exc:
			self.output_error("Copy %s to %s Error: %s" % (sfile, dfile, exc))
		else:
			return FileLeaf(dpath)

	def item_types(self):
		yield FileLeaf
	def valid_for_item(self, item):
		return (not item.is_dir()) and os.access(item.object, os.R_OK)
	def requires_object(self):
		return True
	def object_types(self):
		yield FileLeaf
	def valid_object(self, obj, for_item):
		return _good_destination(obj.object, for_item.object)
	def get_description(self):
		return _("Copy file to a chosen location")

class UnpackHere (Action):
	def __init__(self):
		Action.__init__(self, _("Extract Here"))
		self.extensions_set = set((".rar", ".7z", ".zip", ".gz", ".tgz",
			".tar", ".lzma", ".bz2"))
	def activate(self, leaf):
		utils.launch_commandline("file-roller --extract-here %s" % leaf.object)

	def valid_for_item(self, item):
		tail, ext = os.path.splitext(item.object)
		# FIXME: Make this detection smarter
		return ext.lower() in self.extensions_set

	def item_types(self):
		yield FileLeaf
	def get_description(self):
		return _("Extract compressed archive")

class CreateArchive (Action):
	def __init__(self):
		Action.__init__(self, _("Create Archive"))
	def activate(self, leaf):
		utils.launch_commandline("file-roller --add %s" % leaf.object)

	def valid_for_item(self, item):
		# FIXME: Only for directories right now
		return item.is_dir()
	def item_types(self):
		yield FileLeaf
	def get_description(self):
		return _("Create a compressed archive from folder")

class CreateArchiveIn (Action):
	def __init__(self):
		Action.__init__(self, _("Create Archive In..."))
	def activate(self, leaf, iobj):
		archive_type = __kupfer_settings__["archive_type"]
		dirpath = iobj.object
		basename = os_path.basename(leaf.object)
		archive_path = \
			utils.get_destpath_in_directory(dirpath, basename, archive_type)
		utils.launch_commandline("file-roller --add-to='%s' '%s'" %
				(archive_path, leaf.object))

	def valid_for_item(self, item):
		# FIXME: Only for directories right now
		return item.is_dir()
	def item_types(self):
		yield FileLeaf
	def requires_object(self):
		return True
	def object_types(self):
		yield FileLeaf
	def valid_object(self, obj, for_item=None):
		return utils.is_directory_writable(obj.object)
	def get_description(self):
		return _("Create a compressed archive from folder")
