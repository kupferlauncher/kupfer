# -*- coding: UTF-8 -*-
from __future__ import with_statement

import os

import glib

from kupfer.objects import (Leaf, Action, Source, TextLeaf,
		FilesystemWatchMixin, TextSource, AppLeafContentMixin)
from kupfer import utils, pretty, icons, plugin_support

__kupfer_name__ = _("Zim")
__kupfer_sources__ = ("ZimPagesSource", )
__kupfer_actions__ = (
		"CreateZimPage",
		"CreateZimPageInNotebook",
	)
__description__ = _("Access to Pages stored in Zim - "
                    "A Desktop Wiki and Outliner")
__version__ = "0.3"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

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
	cli = "zim '%s' '%s'" % (notebook, page.replace("'", "_"))
	utils.launch_commandline(cli)


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
		_start_zim("_default_", ":" + leaf.object.strip(':'))

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

def _get_zim_notebooks():
	''' Yield (notebook name, notebook path) from zim config

	@notebook_name: Unicode name
	@notebook_path: Filesystem byte string
	'''
	# We assume the notebook description is UTF-8 encoded
	zim_notebooks_file = os.path.expanduser('~/.config/zim/notebooks.list')
	try:
		with open(zim_notebooks_file, 'r') as noteboks_file:
			for line in noteboks_file.readlines():
				if not line.startswith('_default_'):
					notebook_name, notebook_path = line.strip().split('\t', 2)
					notebook_name = notebook_name.decode("UTF-8", "replace")
					notebook_path = os.path.expanduser(notebook_path)
					yield (notebook_name, notebook_path)

	except IOError, err:
		pretty.print_error(err)

class ZimNotebook (Leaf):
	def get_gicon(self):
		return icons.get_gicon_for_file(self.object)

class ZimNotebooksSource (Source):
	def __init__(self):
		Source.__init__(self, _("Zim Notebooks"))

	def get_items(self):
		for name, path in _get_zim_notebooks():
			yield ZimNotebook(name, name)

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

