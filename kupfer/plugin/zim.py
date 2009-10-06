# -*- coding: utf8 -*-
from __future__ import with_statement

import os

import glib

from kupfer.objects import (Leaf, Action, Source, TextLeaf,
		FilesystemWatchMixin, TextSource, AppLeafContentMixin)
from kupfer import utils

__kupfer_name__ = _("Zim")
__kupfer_sources__ = ("ZimPagesSource", )
__kupfer_contents__ = ("ZimPagesSource", )
__kupfer_actions__ = ("CreateZimPage", )
__description__ = _("Access to Pages stored in Zim - A Desktop Wiki and Outliner")
__version__ = "0.3"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


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
	def __init__(self, page_id, page_name, notebook_id, notebook_name):
		Leaf.__init__(self, page_id, page_name)
		self.page = page_name
		self.notebook = notebook_id
		self.notebook_name = notebook_name

	def get_actions(self):
		yield OpenZimPage()
		yield CreateZimSubPage()

	def get_description(self):
		return _('Zim Page from Notebook "%s"') % self.notebook_name

	def get_icon_name(self):
		return "text-x-generic"


class CreateZimPage(Action):
	''' create new page '''
	rank_adjust = 5

	def __init__(self):
		Action.__init__(self, _('Create Zim Page as SubPage of'))

	def activate(self, leaf, iobj):
		_start_zim(iobj.notebook, iobj.page + ":" + leaf.object.strip(':'))

	def get_icon_name(self):
		return 'document-new'

	def item_types(self):
		yield TextLeaf

	def requires_object(self):
		return True

	def object_types(self):
		yield ZimPage

	def object_source(self, for_item=None):
		return ZimPagesSource()


class OpenZimPage(Action):
	""" Open Zim page  """
	rank_adjust = 10

	def __init__(self):
		Action.__init__(self, _('Open Zim Page'))

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


class ZimPagesSource(AppLeafContentMixin, Source):
	''' Index pages in all Zim notebooks '''
	appleaf_content_id = "zim"

	def __init__(self, name=_("Zim Pages")):
		Source.__init__(self, name)
		# path to file with list notebooks
		self._zim_notebooks_file = os.path.expanduser('~/.config/zim/notebooks.list')
		self._version = 2

	def get_items(self):
		for notebook_name, notebook_path in self._get_notebooks():
			notebook_file = os.path.join(notebook_path, "notebook.zim")
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
					page_name = (page_name
							.lstrip(os.path.sep)
							.replace(os.path.sep, u":")
							.replace(u"_", u" "))
					yield ZimPage(file_path, page_name, notebook_file,
							notebook_name)

	def get_description(self):
		return _("Pages stored in Zim Notebooks")

	def get_icon_name(self):
		return "zim"

	def provides(self):
		yield ZimPage

	def _get_notebooks(self):
		''' Yield (notebook name, notebook path) from zim config

		@notebook_name: Unicode name
		@notebook_path: Filesystem byte string
		'''
		# We assume the notebook description is UTF-8 encoded
		try:
			with open(self._zim_notebooks_file, 'r') as noteboks_file:
				for line in noteboks_file.readlines():
					if not line.startswith('_default_'):
						notebook_name, notebook_path = line.strip().split('\t', 2)
						notebook_name = notebook_name.decode("UTF-8", "replace")
						notebook_path = os.path.expanduser(notebook_path)
						yield (notebook_name, notebook_path)

		except IOError, err:
			self.output_error(err)

