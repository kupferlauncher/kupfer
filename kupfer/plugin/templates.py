import os

import gio
import glib

from kupfer.objects import Leaf, Action, Source, FileLeaf
from kupfer import icons, utils
from kupfer import helplib
from kupfer.helplib import FilesystemWatchMixin, PicklingHelperMixin
from kupfer import plugin_support

__kupfer_name__ = _("Document Templates")
__kupfer_sources__ = ("TemplatesSource", )
__kupfer_actions__ = ("CreateNewDocument", )
__description__ = _("Create new documents from your templates")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

DEFAULT_TMPL_DIR = "~/Templates"

class Template (FileLeaf):
	def __init__(self, path):
		basename = glib.filename_display_basename(path)
		nameroot, ext = os.path.splitext(basename)
		FileLeaf.__init__(self, path, _("%s template") % nameroot)

	def get_actions(self):
		yield CreateDocumentIn()
		for a in FileLeaf.get_actions(self):
			yield a

	def get_gicon(self):
		file_gicon = FileLeaf.get_gicon(self)
		return icons.ComposedIcon("text-x-generic-template", file_gicon)

class EmptyFile (Leaf):
	def __init__(self):
		Leaf.__init__(self, None, _("Empty File"))
	def get_actions(self):
		yield CreateDocumentIn()
	def get_icon_name(self):
		return "gtk-file"

class CreateNewDocument (Action):
	def __init__(self):
		Action.__init__(self, _("Create New Document..."))

	def has_result(self):
		return True
	def activate(self, leaf, iobj):
		if iobj.object:
			# Copy the template to destination directory
			basename = os.path.basename(iobj.object)
			tmpl_gfile = gio.File(iobj.object)
			destpath = utils.get_destpath_in_directory(leaf.object, basename)
			destfile = gio.File(destpath)
			tmpl_gfile.copy(destfile, flags=gio.FILE_COPY_ALL_METADATA)
		else:
			# create new empty file
			filename = unicode(iobj)
			f, destpath = utils.get_destfile_in_directory(leaf.object, filename)
			f.close()
		return FileLeaf(destpath)

	def item_types(self):
		yield FileLeaf
	def valid_for_item(self, leaf):
		return leaf.is_dir()

	def requires_object(self):
		return True
	def object_types(self):
		yield Template
		yield EmptyFile
	def object_source(self, for_item=None):
		return TemplatesSource()

	def get_description(self):
		return _("Create a new document from template")
	def get_icon_name(self):
		return "document-new"

CreateDocumentIn = helplib.reverse_action(CreateNewDocument, rank=10)

class TemplatesSource (Source, PicklingHelperMixin, FilesystemWatchMixin):
	def __init__(self):
		Source.__init__(self, _("Document Templates"))
		self.unpickle_finish()

	def unpickle_finish(self):
		# Set up change callback
		tmpl_dir = glib.get_user_special_dir(glib.USER_DIRECTORY_TEMPLATES)
		if not tmpl_dir:
			tmpl_dir = os.path.expanduser(DEFAULT_TMPL_DIR)
		self.tmpl_dir = tmpl_dir
		self.monitor_token = self.monitor_directories(self.tmpl_dir)

	def get_items(self):
		yield EmptyFile()
		try:
			for fname in os.listdir(self.tmpl_dir):
				yield Template(os.path.join(self.tmpl_dir, fname))
		except EnvironmentError, exc:
			self.output_error(exc)

	def should_sort_lexically(self):
		return True

	def get_description(self):
		return None
	def get_icon_name(self):
		return "system-file-manager"

	def provides(self):
		yield Template

