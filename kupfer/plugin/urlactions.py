from kupfer.objects import Action, Source, UrlLeaf
from kupfer import utils

__kupfer_name__ = _("URL Actions")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
	)
__description__ = _("Actions on URLs")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class DownloadAndOpen (Action):
	"""Asynchronous action to download file and open it"""
	def __init__(self):
		Action.__init__(self, _("Download and Open"))

	def is_async(self):
		return True
	def activate(self, leaf):
		return self._start_action, self._finish_action

	def _start_action(self, leaf, iobj=None):
		import urllib
		uri = leaf.object
		return urllib.urlretrieve(uri)

	def _finish_action(self, ret):
		filename, headers = ret
		utils.show_path(filename)

	def item_types(self):
		yield UrlLeaf
	def valid_for_item(self, item):
		return True
	def get_description(self):
		return None

