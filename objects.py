# -*- coding: UTF-8 -*-

import gobject
import gnomevfs
import itertools

from os import path

class Error (Exception):
	pass

class NoParent (Error):
	pass

class NoContent (Error):
	pass

class NoApplication (Error):
	pass


class Source (object):
	"""
	Source: Data provider for a kupfer browser

	required are
	set_refresh_callback
	get_items
	"""
	def set_refresh_callback(self, refresh_callback):
		"""
		Set function to be called on owner when data needs refresh
		"""
		self.refresh_callback = refresh_callback

	def get_items(self):
		"""
		return a list of leaves
		"""
		return []

	def has_parent(self):
		return False

	def get_parent(self):
		raise NoParent

	def __str__(self):
		return self.__class__.__name__

	def representation(self):
		"""
		Return represented object
		"""
		return self


class KupferObject (object):
	def get_pixmap(self):
		return None


class Leaf (KupferObject):
	def __init__(self, obj, value):
		self.object = obj
		self.value = value
	
	def __repr__(self):
		return "<%s %s at %x>" % (self.__class__.__name__, self.object, id(self))
	
	def has_content(self):
		return False
	
	def content_source(self):
		raise NoContent

	def get_actions(self):
		return ()


class FileLeaf (Leaf):
	def get_actions(self):
		acts = [Show(), Echo(), Dragbox()]
		if path.isdir(self.object):
			pass
		else:
			type = gnomevfs.get_mime_type(self.object)
			print type
			types = gnomevfs.mime_get_short_list_applications(type)
			apps = set()
			for info in types:
				id = info[1]
				if id not in apps:
					acts.append(Show(info))
					apps.add(id)
		return acts

	def has_content(self):
		return path.isdir(self.object)


	def content_source(self):
		if self.has_content():
			return DirectorySource(self.object)
		else:
			return Leaf.content_source(self)

class SourceLeaf (Leaf):
	def has_content(self):
		return True

	def content_source(self):
		return self.object


class Action (KupferObject):
	def activate(self, leaf):
		pass
	
	def activate_many(self, leaves):
		pass


class Echo (Action):
	def activate(self, leaf):
		print "Echo:", leaf.object


class Show (Action):
	def __init__(self, app_spec=None):
		"""
		Action that launches a file with app_spec

		app_spec: application info as given by for example mime_get_default_application
		if app_spec is None, open with default viewer
		"""
		self.app_spec = app_spec

	def _open_uri(self, uri, app_spec):
		"""
		By Ed Catmur ed at catmur.co.uk 
		http://www.daa.com.au/pipermail/pygtk/2007-March/013618.html

		Try open with given app_spec
		"""
		mime = gnomevfs.get_mime_type (uri)
		scheme = gnomevfs.get_uri_scheme (uri)
		# http://bugzilla.gnome.org/show_bug.cgi?id=411560

		id, name, command, multi, paths_for_local, schemes, term = app_spec
		argv = command.split()
		if scheme == 'file' and paths_for_local:
			argv.append(gnomevfs.get_local_path_from_uri (uri))
			return gobject.spawn_async (argv, flags=gobject.SPAWN_SEARCH_PATH)
		elif scheme == 'file' or scheme in schemes:
			argv.append(uri)
			return gobject.spawn_async (argv, flags=gobject.SPAWN_SEARCH_PATH)

		raise NoApplication
	
	def __repr__(self):
		return "<%s %s at %x>" % (self.__class__.__name__, str(self), id(self))
	
	def __str__(self):
		if not self.app_spec:
			return "Show"
		return "Show with %s" % self.app_spec[1]
	
	def activate(self, leaf):
		print "Show: %s" % (leaf.object,)
		uri = gnomevfs.get_uri_from_local_path(leaf.object)
		if self.app_spec:
			self._open_uri(uri, self.app_spec)
		else:
			gnomevfs.url_show(uri)


class Dragbox (Action):

	def __str__(self):
		return "Put on dragbox"
	
	def activate(self, leaf):
		path = leaf.object
		argv = ["dragbox", "--file", path]
		gobject.spawn_async(argv, flags=gobject.SPAWN_SEARCH_PATH)


def get_dirlist(folder, depth=0, include=None, exclude=None):
	"""
	Return a list of absolute paths in folder
	include, exclude: a function returning a boolean
	def include(filename):
		return ShouldInclude
	"""
	class Context (object):
		pass

	context = Context()
	context.dirlist = []
	context.depth = 0
	def get_listing(context, dirname, fnames):
		for file in fnames:
			abspath = path.join(dirname, file)
			if include and not include(file):
				continue
			if exclude and exclude(file):
				continue
			context.dirlist.append(abspath)

		# don't recurse
		context.depth += 1
		if context.depth > depth:
			del fnames[:]

	path.walk(folder, get_listing, context)
	return context.dirlist


class FileSource (Source):

	def __init__(self, dirlist, deep=False):
		self.dirlist = dirlist
		self.deep = deep

	def __str__(self):
		dirs = [path.basename(dir) for dir in self.dirlist]
		dirstr = ", ".join(dirs)
		return "%s %s" % (Source.__str__(self), dirstr)

	def get_items(self):
		iters = []
		
		def mkleaves(dir):
			print "mkleaves", dir
			files = get_dirlist(dir, depth=self.deep, exclude=self._exclude_file)
			return (FileLeaf(f, path.basename(f)) for f in files)

		for d in self.dirlist:
			iters.append(mkleaves(d))

		return itertools.chain(*iters)

	def _exclude_file(self, filename):
		return filename.startswith(".") 


class DirectorySource (FileSource):

	def __init__(self, dir):
		self.directory = dir
		self.deep = False

	def get_items(self):
		dirlist = get_dirlist(self.directory, exclude=lambda f: f.startswith("."))
		items = (FileLeaf(file, path.basename(file)) for file in dirlist)
		return items

	def __str__(self):
		return "%s %s" % (Source.__str__(self), path.basename(self.directory))
	
	def _parent_path(self):
		return path.normpath(path.join(self.directory, path.pardir))

	def has_parent(self):
		return self.directory != self._parent_path()

	def get_parent(self):
		if not self.has_parent():
			return FileSource.has_parent(self)
		return DirectorySource(self._parent_path())


class SourcesSource (Source):

	def __init__(self, sources):
		self.sources = sources
	
	def get_items(self):
		return (SourceLeaf(s, str(s)) for s in self.sources)


