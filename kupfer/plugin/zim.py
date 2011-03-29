# -*- coding: UTF-8 -*-
from __future__ import with_statement

__kupfer_name__ = _("Zim")
__kupfer_sources__ = ("ZimPagesSource", )
__kupfer_actions__ = (
		"CreateZimPage",
		"CreateZimPageInNotebook",
	)
__description__ = _("Access to Pages stored in Zim - "
                    "A Desktop Wiki and Outliner")
__version__ = "2010-02-03"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os

import gio
import glib

from kupfer.objects import Leaf, Action, Source, TextLeaf, TextSource
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import config, utils, pretty, icons, plugin_support


__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "page_name_starts_colon",
		"label": _("Page names start with :colon"),
		"type": bool,
		"value": False,
	},
)

'''
TODO:
	use FilesystemWatchMixin (?)
'''


def _start_zim(notebook, page):
	''' Start zim and open given notebook and page. '''
	utils.spawn_async(("zim", notebook, page.replace("'", "_")))


class ZimPage(Leaf):
	""" Represent single Zim page """
	def __init__(self, page_id, page_name, notebook_path, notebook_name):
		Leaf.__init__(self, page_id, page_name)
		self.page = page_name
		self.notebook = notebook_path
		self.notebook_name = notebook_name

	def get_actions(self):
		yield OpenZimPage()
		yield CreateZimSubPage()

	def get_description(self):
		return _('Zim Page from Notebook "%s"') % self.notebook_name

	def get_icon_name(self):
		return "text-x-generic"


class CreateZimPage(Action):
	""" Create new page in default notebook """
	def __init__(self):
		Action.__init__(self, _('Create Zim Page'))

	def activate(self, leaf):
		notebook = _get_default_notebook()
		_start_zim(notebook, ":" + leaf.object.strip(':'))

	def get_description(self):
		return _("Create page in default notebook")
	def get_icon_name(self):
		return 'document-new'

	def item_types(self):
		yield TextLeaf

class CreateZimPageInNotebook(Action):
	""" Create new page in default notebook """
	def __init__(self):
		Action.__init__(self, _('Create Zim Page In...'))

	def activate(self, leaf, iobj):
		_start_zim(iobj.object, ":" + leaf.object.strip(':'))

	def get_icon_name(self):
		return 'document-new'

	def item_types(self):
		yield TextLeaf

	def requires_object(self):
		return True
	def object_types(self):
		yield ZimNotebook
	def object_source(self, for_item=None):
		return ZimNotebooksSource()

class OpenZimPage(Action):
	""" Open Zim page  """
	rank_adjust = 10

	def __init__(self):
		Action.__init__(self, _('Open'))

	def activate(self, leaf):
		_start_zim(leaf.notebook, leaf.page)

	def get_icon_name(self):
		return 'document-open'

	def item_types(self):
		yield ZimPage


class CreateZimSubPage(Action):
	""" Open Zim page  """
	def __init__(self):
		Action.__init__(self, _('Create Subpage...'))

	def activate(self, leaf, iobj):
		_start_zim(leaf.notebook, leaf.page + ":" + iobj.object.strip(':'))

	def get_icon_name(self):
		return 'document-new'

	def item_types(self):
		yield ZimPage

	def requires_object(self):
		return True

	def object_types(self):
		yield TextLeaf
	
	def object_source(self, for_item=None):
		return TextSource()

def _read_zim_notebooks_old(zim_notebooks_file):
	''' Yield (notebook name, notebook path) from zim config

	@notebook_name: Unicode name
	@notebook_path: Filesystem byte string
	'''
	# We assume the notebook description is UTF-8 encoded
	with open(zim_notebooks_file, 'r') as notebooks_file:
		for line in notebooks_file.readlines():
			if not line.startswith('_default_'):
				notebook_name, notebook_path = line.strip().split('\t', 2)
				notebook_name = notebook_name.decode("UTF-8", "replace")
				notebook_path = os.path.expanduser(notebook_path)
				yield (notebook_name, notebook_path)


def _get_default_notebook():
	''' Find default notebook '''
	zim_notebooks_file = config.get_config_file("notebooks.list", package="zim")
	if not zim_notebooks_file:
		pretty.print_error(__name__, "Zim notebooks.list not found")
		return None
	with open(zim_notebooks_file, 'r') as notebooks_file:
		for line in notebooks_file.readlines():
			if line.strip() == "[NotebookList]":
				# new file format == pyzim
				return ''
			if line.strip() != '_default_': # when no default notebook
				notebook_name, notebook_path = line.strip().split('\t', 2)
				if notebook_name == '_default_':
					# _default_ is pointing at name of the default notebook
					return notebook_path.decode("UTF-8", "replace")
				else:
					# assume first notebook as default
					return notebook_name.decode("UTF-8", "replace")


def _read_zim_notebook_name(notebook_path):
	npath = os.path.join(notebook_path, "notebook.zim")
	with open(npath, "r") as notebook_file:
		for line in notebook_file:
			if line.startswith("name="):
				_ignored, b_name = line.strip().split("=", 1)
				us_name = b_name.decode("unicode_escape")
				return us_name
	return os.path.basename(notebook_path)

def _read_zim_notebooks_new(zim_notebooks_file):
	''' Yield (notebook name, notebook path) from zim config

	@notebook_name: Unicode name
	@notebook_path: Filesystem byte string
	'''
	default_url = None
	with open(zim_notebooks_file, 'r') as notebooks_file:
		for line in notebooks_file:
			if line.startswith("["):
				continue
			if line.startswith("Default="):
				_ignored, notebook_url = line.split("=", 1)
				notebook_url = notebook_url.strip()
				default_url = notebook_url
			elif line.strip() != default_url:
				notebook_url = line.strip()
			else:
				continue
			notebook_path = gio.File(notebook_url).get_path()
			try:
				notebook_name = _read_zim_notebook_name(notebook_path)
			except IOError:
				pass
			else:
				yield (notebook_name, notebook_path)

def _get_zim_notebooks():
	''' Yield (notebook name, notebook path) from zim config

	@notebook_name: Unicode name
	@notebook_path: Filesystem byte string
	'''
	# We assume the notebook description is UTF-8 encoded
	zim_notebooks_file = config.get_config_file("notebooks.list", package="zim")
	if not zim_notebooks_file:
		pretty.print_error(__name__, "Zim notebooks.list not found")
		return []
	try:
		with open(zim_notebooks_file, 'r') as notebooks_file:
			for line in notebooks_file.readlines():
				if line.strip() == "[NotebookList]":
					return _read_zim_notebooks_new(zim_notebooks_file)
				else:
					return _read_zim_notebooks_old(zim_notebooks_file)
	except IOError, err:
		pretty.print_error(__name__, err)

class ZimNotebook (Leaf):
	def get_gicon(self):
		return icons.get_gicon_for_file(self.object)

class ZimNotebooksSource (Source):
	def __init__(self):
		Source.__init__(self, _("Zim Notebooks"))

	def get_items(self):
		for name, path in _get_zim_notebooks():
			yield ZimNotebook(path, name)

	def get_icon_name(self):
		return "zim"

	def provides(self):
		yield ZimNotebook

class ZimPagesSource(AppLeafContentMixin, Source):
	''' Index pages in all Zim notebooks '''
	appleaf_content_id = "zim"

	def __init__(self, name=_("Zim Pages")):
		Source.__init__(self, name)
		# path to file with list notebooks
		self._version = 2

	def get_items(self):
		strip_name_first_colon = not __kupfer_settings__["page_name_starts_colon"]
		for notebook_name, notebook_path in _get_zim_notebooks():
			for root, dirs, files in os.walk(notebook_path):
				# find pages in notebook
				for filename in files:
					file_path = os.path.join(root, filename)
					page_name, ext = os.path.splitext(file_path)
					if not ext.lower() == ".txt":
						continue
					page_name = page_name.replace(notebook_path, "", 1)
					# Ask GLib for the correct unicode representation
					# of the page's filename
					page_name = glib.filename_display_name(page_name)
					if strip_name_first_colon:
						page_name = page_name.lstrip(os.path.sep)
					page_name = (page_name
							.replace(os.path.sep, u":")
							.replace(u"_", u" "))
					yield ZimPage(file_path, page_name, notebook_path,
							notebook_name)

	def get_description(self):
		return _("Pages stored in Zim Notebooks")

	def get_icon_name(self):
		return "zim"

	def provides(self):
		yield ZimPage

