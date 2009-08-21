import os
import urllib2

from kupfer.objects import Action, Source, UrlLeaf, FileLeaf
from kupfer import utils, pretty

__kupfer_name__ = _("URL Actions")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
		"DownloadAndOpen",
		"DownloadTo",
	)
__description__ = _("URL Actions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

def _download_uri(uri, destdir):
	"""
	Download @uri to directory @destdir
	URI downloading may raise (IOError, EnvironmentError);
	these are not handled here.
	"""
	import shutil

	response = urllib2.urlopen(uri)
	
	header_basename = response.headers.get('Content-Disposition')
	destname = header_basename or os.path.basename(response.url)
	destpath = utils.get_destpath_in_directory(destdir, destname)
	destfile = open(destpath, "wb")
	try:
		shutil.copyfileobj(response, destfile)
	finally:
		response.close()
		destfile.close()

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
	def get_description(self):
		return None

class DownloadTo (Action):
	def __init__(self):
		Action.__init__(self, _("Download To..."))

	def is_async(self):
		return True
	def activate(self, leaf, obj):
		return self._start_action, self._finish_action

	def _start_action(self, leaf, iobj=None):
		uri = leaf.object
		destdir = iobj.object
		_download_uri(uri, destdir)

	def _finish_action(self, ret):
		pass

	def item_types(self):
		yield UrlLeaf
	def requires_object(self):
		return True
	def object_types(self):
		yield FileLeaf
	def valid_object(self, obj, for_item=None):
		return utils.is_directory_writable(obj.object)
	def get_description(self):
		return _("Download URL to a chosen location")

