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

import gio
import os
import re
# since "path" is a very generic name, you often forget..
from os import path as os_path

from kupfer.objects import OperationError
from kupfer.objects import Action, FileLeaf, TextLeaf, TextSource
from kupfer import utils, pretty
from kupfer import plugin_support
from kupfer import commandexec
from kupfer import runtimehelper


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
	to be copied or moved to. Additional checking is done in
	good_destination_final
	"""
	if not os_path.isdir(dpath):
		return False
	spath = os_path.normpath(spath)
	dpath = os_path.normpath(dpath)
	if not os.access(dpath, os.R_OK | os.W_OK | os.X_OK):
		return False
	cpfx = os_path.commonprefix((spath, dpath))
	if os_path.samefile(dpath, spath) or cpfx == spath:
		return False
	return True

def _good_destination_final(dpath, spath):
	"""Perform a final check that the file @spath can
	be copied or moved to @dpath
	"""
	dest_filename = os_path.join(dpath, os_path.basename(spath))
	if os_path.exists(dest_filename):
		return False
	parent_spath = os_path.dirname(spath)
	return not (dpath == parent_spath)

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
			raise OperationError(unicode(exc))
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
		name = _("Rename To...").rstrip(".")
		TextSource.__init__(self, name)

	def get_rank(self):
		# this should rank high
		return 100

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
			raise OperationError(unicode(exc))
		else:
			return FileLeaf(dfile.get_path())

	def activate_multiple(self, objs, iobjs):
		raise NotImplementedError

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

	def has_result(self):
		return True

	def _finish_callback(self, gfile, result, data):
		ctx = commandexec.DefaultActionExecutionContext()
		self.output_debug("Finished copying", gfile)
		dfile, action_token = data
		try:
			gfile.copy_finish(result)
		except gio.Error:
			ctx.register_late_error(action_token)
		else:
			ctx.register_late_result(action_token, FileLeaf(dfile.get_path()))

	def activate(self, leaf, obj):
		sfile = gio.File(leaf.object)
		dpath = os_path.join(obj.object, os_path.basename(leaf.object))
		dfile = gio.File(dpath)
		ctx = commandexec.DefaultActionExecutionContext()
		action_token = ctx.get_async_token()
		try:
			ret = sfile.copy_async(dfile, self._finish_callback,
					user_data=(dfile, action_token),
					flags=gio.FILE_COPY_ALL_METADATA)
			self.output_debug("Copy %s to %s (ret: %s)" % (sfile, dfile, ret))
		except gio.Error, exc:
			raise OperationError(unicode(exc))

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
		utils.spawn_async_notify_as("file-roller.desktop",
				["file-roller", "--extract-here", leaf.object])

	def valid_for_item(self, item):
		tail, ext = os.path.splitext(item.object)
		# FIXME: Make this detection smarter
		# check for standard extension or a multi-part rar extension
		return (ext.lower() in self.extensions_set or
			re.search(r".r\d+$", ext.lower()) is not None)

	def item_types(self):
		yield FileLeaf
	def get_description(self):
		return _("Extract compressed archive")

class CreateArchive (Action):
	def __init__(self):
		Action.__init__(self, _("Create Archive"))

	@classmethod
	def _make_archive(cls, filepaths):
		cmd = ["file-roller", "--add"]
		cmd.extend(filepaths)
		utils.spawn_async(cmd)

	def activate(self, leaf):
		self._make_archive((leaf.object, ))
	def activate_multiple(self, objs):
		self._make_archive([L.object for L in objs])

	def item_types(self):
		yield FileLeaf
	def get_description(self):
		return _("Create a compressed archive from folder")

class CreateArchiveIn (Action):
	def __init__(self):
		Action.__init__(self, _("Create Archive In..."))

	@classmethod
	def _make_archive(cls, basename, dirpath, filepaths):
		archive_type = __kupfer_settings__["archive_type"]
		archive_path = \
			utils.get_destpath_in_directory(dirpath, basename, archive_type)
		cmd = ["file-roller", "--add-to=%s" % (archive_path, )]
		cmd.extend(filepaths)
		runtimehelper.register_async_file_result(archive_path)
		utils.spawn_async(cmd)
		return archive_path

	def activate(self, leaf, iobj):
		archive_type = __kupfer_settings__["archive_type"]
		dirpath = iobj.object
		basename = os_path.basename(leaf.object)
		self._make_archive(basename, dirpath, (leaf.object, ))

	def activate_multiple(self, objs, iobjs):
		archive_type = __kupfer_settings__["archive_type"]
		# TRANS: Default filename (no extension) for 'Create Archive In...'
		basename = _("Archive")
		for iobj in iobjs:
			self._make_archive(basename, iobj.object, [L.object for L in objs])

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
