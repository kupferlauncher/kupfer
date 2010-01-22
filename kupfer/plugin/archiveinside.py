"""
A test project to see if we can make a plugin that allows us to
drill down into compressed archives.

Issues to resolve:

 * Refuse looking into archives over a certain size
 * Add option to clean up at Kupfer's exit
 * Handle zip, tar.gz and anything we can
"""
__kupfer_name__ = _("Look inside Archives")
__kupfer_contents__ = ("ArchiveContent", )
__description__ = _("Recently used documents and bookmarked folders")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import hashlib
import os
import tarfile

from kupfer.objects import Source, FileLeaf
from kupfer.obj.sources import DirectorySource
from kupfer import utils



class ArchiveContent (Source):
	_unarchived_files = []
	def __init__(self, fileleaf):
		Source.__init__(self, _("Content of %s") % fileleaf)
		self.path = fileleaf.object

	def repr_key(self):
		return self.path

	def get_items(self):
		# always use the same destination for the same file
		basename = os.path.basename(os.path.normpath(self.path))
		root, ext = os.path.splitext(basename)
		mtime = os.stat(self.path).st_mtime
		fileid = hashlib.sha1("%s%s" % (self.path, mtime)).hexdigest()
		pth = os.path.join("/tmp", "kupfer-%s-%s" % (root, fileid, ))
		if not os.path.exists(pth):
			zf = tarfile.TarFile.gzopen(self.path)
			zf.extractall(path=pth)
			self._unarchived_files.append(zf)
		files = list(DirectorySource(pth).get_leaves())
		if len(files) == 1 and files[0].has_content():
			return files[0].content_source().get_leaves()
		return files

	def get_description(self):
		return None

	@classmethod
	def decorates_type(cls):
		return FileLeaf

	@classmethod
	def decorate_item(cls, leaf):
		root, ext = os.path.splitext(leaf.object)
		if leaf.object.lower().endswith(".tar.gz"):
			return cls(leaf)
		return None

