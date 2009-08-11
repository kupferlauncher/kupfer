import os
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

import gio

from kupfer.objects import (Leaf, Action, Source,
		AppLeaf, FileLeaf, UrlLeaf, PicklingHelperMixin, AppLeafContentMixin)
from kupfer import objects
from kupfer import launch, icons

__kupfer_name__ = _("Abiword")
__kupfer_sources__ = ("RecentsSource", )
__kupfer_contents__ = ("RecentsSource", )
__description__ = _("Recently used documents in Abiword")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class AbiwordHandler(ContentHandler):
	"""Parse abiword's config file and get the recent applications"""
	def __init__(self, allFiles, application="abiword"):
		ContentHandler.__init__(self)
		self.allFiles = allFiles
		self.fWantScope = False
		self.application = application

	def startElement(self, sName, attributes):
		if sName == "AbiPreferences" and attributes["app"] == self.application:
			self.fWantScope = True
		elif sName == "Recent" and self.fWantScope:
			mnum = int(attributes["max"])
			for num in xrange(1, mnum+1):
				attr ="name%d" % num
				if attr in attributes:
					self.allFiles.append(attributes[attr])
	def characters(self, sData):
		pass

	def endElement(self,sName):
		if sName == "AbiPreferences":
			self.fWantScope = False

def get_abiword_files(xmlfilepath):
	sFile = os.path.expanduser(xmlfilepath)
	parser = make_parser()
	allFiles = []
	handler = AbiwordHandler(allFiles)
	parser.setContentHandler(handler)
	parser.parse(sFile)
	return allFiles

class RecentsSource (AppLeafContentMixin, Source, PicklingHelperMixin):
	appleaf_content_id = "abiword.desktop"
	def __init__(self, name=None):
		if not name:
			name = _("Abiword Recent Items")
		super(RecentsSource, self).__init__(name)
		self.unpickle_finish()

	def pickle_prepare(self):
		# monitor is not pickleable
		self.monitor = None

	def unpickle_finish(self):
		"""Set up change monitor"""
		abifile = self._get_abiword_file()
		if not abifile: return
		gfile = gio.File(abifile)
		self.monitor = gfile.monitor_file(gio.FILE_MONITOR_NONE, None)
		if self.monitor:
			self.monitor.connect("changed", self._changed)

	def _changed(self, monitor, file1, file2, evt_type):
		"""Change callback; something changed"""
		if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
				gio.FILE_MONITOR_EVENT_DELETED,
				gio.FILE_MONITOR_EVENT_CHANGED):
			self.mark_for_update()

	def _get_abiword_file(self):
		abifile = os.path.expanduser("~/.AbiSuite/AbiWord.Profile")
		if not os.path.exists(abifile):
			return None
		return abifile

	def get_items(self):
		abifile = self._get_abiword_file()
		if not abifile:
			self.output_debug("Abiword profie not found at", abifile)
			return
		for uri in get_abiword_files(abifile):
			gfile = gio.File(uri)
			if not gfile.query_exists():
				continue

			if gfile.get_path():
				leaf = FileLeaf(gfile.get_path())
			else:
				leaf = UrlLeaf(gfile.get_uri(), gfile.get_basename())
			yield leaf

	def get_description(self):
		return _("Recently used documents in Abiword")

	def get_icon_name(self):
		return "document-open-recent"
	def provides(self):
		yield FileLeaf
		yield UrlLeaf

