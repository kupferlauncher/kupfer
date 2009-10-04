# -*- coding: utf8 -*-
from __future__ import with_statement

import os

from kupfer.objects import (Leaf, Action, Source, TextLeaf,
		FilesystemWatchMixin, TextSource, AppLeafContentMixin)
from kupfer import utils

__kupfer_name__ = _("Zim")
__kupfer_sources__ = ("ZimPagesSource", )
__kupfer_contents__ = ("ZimPagesSource", )
__kupfer_actions__ = ("CreateZimPage", )
__description__ = _("Access to Pages stored in Zim - A Desktop Wiki and Outliner")
__version__ = "0.2"
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
	def __init__(self, notebook, page):
		full_name = notebook + " " + page
		Leaf.__init__(self, full_name, page)
		self.page = page
		self.notebook = notebook

	def get_actions(self):
		yield OpenZimPage()
		yield CreateZimSubPage()

	def get_description(self):
		return _('Zim Page from Notebook "%s"') % self.notebook

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
		Action.__init__(self, _('Create Zim SubPage'))

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

	def get_items(self):
		for notebook_name, notebook_path in self._get_notebooks():
			notebook_path_len = len(notebook_path)
			for root, dirs, files in os.walk(notebook_path):
				# find pages in notebook
				for filename in files:
					if filename.endswith('.txt'):
						file_path = os.path.join(root, filename)
						page_name = file_path[notebook_path_len:-4]
						page_name = page_name.replace(os.path.sep, ':').replace('_', ' ')
						yield ZimPage(notebook_name, page_name)

	def get_description(self):
		return _("Pages stored in Zim Notebooks")

	def get_icon_name(self):
		return "zim"

	def provides(self):
		yield ZimPage

	def _get_notebooks(self):
		''' get (notebook name, notebook path) from zim config '''
		try:
			with open(self._zim_notebooks_file, 'r') as noteboks_file:
				for line in noteboks_file.readlines():
					if not line.startswith('_default_'):
						notebook_name, notebook_path = line.strip().split('\t', 2)
						notebook_path = os.path.expanduser(notebook_path)
						yield (notebook_name, notebook_path)

		except IOError, err:
			self.output_error(err)

