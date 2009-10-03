# -*- coding: utf8 -*-
from __future__ import with_statement

import os

from kupfer.objects import Leaf, Action, Source, TextLeaf
from kupfer.utils import spawn_async

__kupfer_name__ = _("Zim pages")
__kupfer_sources__ = ("ZimPagesSource", )
__kupfer_actions__ = ("OpenZimPageAction", )
__description__ = _("Zim pages")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"



class ZimPageLeaf(Leaf):
	""" Represent single Zim page """
	def __init__(self, notebook, page):
		full_name = notebook + " " + page
		super(ZimPageLeaf, self).__init__(full_name, page)
		self.page = page
		self.notebook = notebook

	def get_actions(self):
		yield OpenZimPageAction()

	def get_description(self):
		return _('Zim page from notebook "%s"') % self.notebook

	def get_icon_name(self):
		return "text-x-generic"



class OpenZimPageAction(Action):
	""" Open Zim page (or create it) """
	def __init__(self):
		super(OpenZimPageAction, self).__init__(_('Open Zim page'))

	def activate(self, leaf):
		if isinstance(leaf, ZimPageLeaf):
			# leaf are zim pages
			cli = ("zim", leaf.notebook, leaf.page)

		else:
			# leaf is enetere text (textleaf)
			page = leaf.object
			if page.find(' :') > -1:
				notebook, page = page.split(' ', 2)
				cli = ('zim', notebook, str(page))

			else:
				cli = ('zim', '_default_', str(page))

		spawn_async(cli)

	def get_icon_name(self):
		return 'document-open'

	def item_types(self):
		yield ZimPageLeaf
		yield TextLeaf



class ZimPagesSource(Source):
	''' Index pages in all Zim notebooks '''
	def __init__(self, name=_("Zim pages")):
		super(ZimPagesSource, self).__init__(name)
		# path to file with list notebooks
		self._zim_notebooks_file = os.path.expanduser('~/.config/zim/notebooks.list')

	def is_dynamic(self):
		return False

	def get_items(self):
		for notebook_name, notebook_path in self._get_notebooks():
			notebook_path_len = len(notebook_path)
			for root, dirs, files in os.walk(notebook_path):
				# find pages in notebook
				for filename in files:
					if filename.endswith('.txt'):
						file_path = os.path.join(root, filename)
						page_name = file_path[notebook_path_len:-4].replace(os.path.sep, ':')
						yield ZimPageLeaf(notebook_name, page_name)

	def get_description(self):
		return _("Pages stored in Zim notebooks")

	def get_icon_name(self):
		return "zim"

	def provides(self):
		yield ZimPageLeaf

	def _get_notebooks(self):
		''' get (notebook name, notebook path) from zim config '''
		try:
			with open(self._zim_notebooks_file, 'r') as noteboks_file:
				for line in noteboks_file.readlines():
					if not line.startswith('_default_'):
						notebook_name, notebook_path = line.strip().split('\t', 2)
						notebook_path = os.path.expanduser(notebook_path)
						yield (notebook_name, notebook_path)
		except Exception, err:
			print err

