import os

import gio
import glib

from kupfer.objects import Leaf, Action, Source, FileLeaf
from kupfer import icons, plugin_support, utils
from kupfer.helplib import FilesystemWatchMixin, PicklingHelperMixin

__kupfer_name__ = _("Templates")
__kupfer_sources__ = ("TemplatesSource", )
__kupfer_actions__ = ("CreateNewDocument", )
__description__ = _("Create documents from templates")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

DEFAULT_TMPL_DIR = "~/Templates"

def _reversed_action(action, name=None, rank=0):
	"""Return a reversed version a three-part action

	@action: the action class
	@name: use a different name
	"""
	class ReverseAction (action):
		rank_adjust = rank
		def __init__(self):
			Action.__init__(self, name or unicode(action()))
		def activate(self, leaf, iobj):
			return action.activate(self, iobj, leaf)
		def item_types(self):
			return action.object_types(self)
		def valid_for_item(self, leaf):
			try:
				return leaf.valid_object(leaf)
			except AttributeError:
				return True
		def object_types(self):
			return action.item_types(self)
		def valid_object(self, obj, for_item=None):
			return action.valid_for_item(self, obj)
		def object_source(self, for_item=None):
			return None
	ReverseAction.__name__ = "Reverse" + action.__name__
	return ReverseAction

class Template (FileLeaf):
	def __init__(self, path):
		basename = glib.filename_display_basename(path)
		FileLeaf.__init__(self, path, _("%s template") % basename)

	def get_actions(self):
		yield CreateDocumentIn()
		for a in FileLeaf.get_actions(self):
			yield a

	def get_gicon(self):
		file_gicon = FileLeaf.get_gicon(self)
		return icons.ComposedIcon("text-x-generic-template", file_gicon)

class CreateNewDocument (Action):
	def __init__(self):
		Action.__init__(self, _("Create New Document..."))

	def has_result(self):
		return True
	def activate(self, leaf, iobj):
		filename = os.path.basename(iobj.object)
		gfile = gio.File(iobj.object)
		destpath = utils.get_destpath_in_directory(leaf.object, filename)
		destfile = gio.File(destpath)
		ret = gfile.copy(destfile, flags=gio.FILE_COPY_ALL_METADATA)
		return FileLeaf(destpath)

	def item_types(self):
		yield FileLeaf

	def valid_for_item(self, leaf):
		return leaf.is_dir()

	def requires_object(self):
		return True
	def object_types(self):
		yield Template
	def object_source(self, for_item=None):
		return TemplatesSource()
	def get_icon_name(self):
		return "document-new"

CreateDocumentIn = _reversed_action(CreateNewDocument, rank=10)

class TemplatesSource (Source, PicklingHelperMixin, FilesystemWatchMixin):
	def __init__(self):
		Source.__init__(self, _("Templates"))
		self.unpickle_finish()

	def unpickle_finish(self):
		"""Set up change callback"""
		tmpl_var = os.getenv("XDG_TEMPLATES_DIR", DEFAULT_TMPL_DIR)
		self.tmpl_dir = os.path.expanduser(tmpl_var)
		self.monitor_token = self.monitor_directories(self.tmpl_dir)

	def get_items(self):
		try:
			for fname in os.listdir(self.tmpl_dir):
				yield Template(os.path.join(self.tmpl_dir, fname))
		except EnvironmentError, exc:
			self.output_error(exc)

	def get_description(self):
		return _("Recently used documents")

	def get_icon_name(self):
		return "system-file-manager"

	def provides(self):
		yield Template

