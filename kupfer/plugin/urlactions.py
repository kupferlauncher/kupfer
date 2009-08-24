import os
import urllib2

from kupfer.objects import Action, Source, UrlLeaf, FileLeaf
from kupfer import utils, pretty, task

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

class DownloadTask (task.StepTask):
	def __init__(self, uri, destdir, finish_callback=None):
		super(DownloadTask, self).__init__()
		self.response = urllib2.urlopen(uri)

		header_basename = self.response.headers.get('Content-Disposition')
		destname = header_basename or os.path.basename(self.response.url)
		self.destpath = utils.get_destpath_in_directory(destdir, destname)
		self.done = False
		self.destfile = open(self.destpath, "wb")
		self.bufsize = 8192
		self.finish_callback = finish_callback

	def step(self):
		buf = self.response.read(self.bufsize)
		if not buf:
			self.done = True
			return False
		self.destfile.write(buf)
		return True

	def finish(self):
		self.destfile.close()
		self.response.close()
		if not self.done:
			print "Deleting unfinished", self.destfile
			os.unlink(self.destpath)
		elif self.finish_callback:
			self.finish_callback(self.destpath)

class DownloadAndOpen (Action):
	"""Asynchronous action to download file and open it"""
	def __init__(self):
		Action.__init__(self, _("Download and Open"))

	def is_async(self):
		return True
	def activate(self, leaf):
		uri = leaf.object
		destdir = "/tmp"
		return DownloadTask(uri, destdir, self._finish_action)

	def _finish_action(self, filename):
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
		uri = leaf.object
		return DownloadTask(uri, obj.object)

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

