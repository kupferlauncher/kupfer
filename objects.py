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
	def get_pixbuf(self):
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

	def get_pixbuf(self):
		uri = gnomevfs.get_uri_from_local_path(self.object)
		return get_icon_for_uri(uri)

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
	
	def __str__(self):
		return "Echo"

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
	from os import walk
	paths = []
	def include_file(file):
		return (not include or include(file)) and (not exclude or not exclude(file))
		
	for dirname, dirnames, fnames in walk(folder):
		# skip deep directories
		head, dp = dirname, 0
		while head != folder:
			head, tail = path.split(head)
			dp += 1
		if dp > depth:
			del dirnames[:]
			continue
		
		excl_dir = []
		for dir in dirnames:
			if not include_file(dir):
				excl_dir.append(dir)
				continue
			abspath = path.join(dirname, dir)
			paths.append(abspath)
		
		for file in fnames:
			if not include_file(file):
				continue
			abspath = path.join(dirname, file)
			paths.append(abspath)

		for dir in reversed(excl_dir):
			dirnames.remove(dir)

	return paths


def get_icon_for_uri(uri, icon_size=48):
	"""
	Returns a pixbuf representing the file at
	the URI generally (mime-type based)
	
	@param icon_size: a pixel size of the icon
	@type icon_size: an integer object.
	 
	"""
	from gtk import icon_theme_get_default, ICON_LOOKUP_USE_BUILTIN
	from gnomevfs import get_mime_type
	from gnome.ui import ThumbnailFactory, icon_lookup

	mtype = get_mime_type(uri)
	icon_theme = icon_theme_get_default()
	thumb_factory = ThumbnailFactory(16)
	icon_name, num = icon_lookup(icon_theme, thumb_factory,  file_uri=uri, custom_icon="")
	icon = icon_theme.load_icon(icon_name, icon_size, ICON_LOOKUP_USE_BUILTIN)
	return icon

class FileSource (Source):
	def __init__(self, dirlist, depth=0):
		self.dirlist = dirlist
		self.depth = depth

	def __str__(self):
		dirs = [path.basename(dir) for dir in self.dirlist]
		dirstr = ", ".join(dirs)
		return "%s %s" % (Source.__str__(self), dirstr)

	def get_items(self):
		iters = []
		
		def mkleaves(dir):
			print "mkleaves", dir
			files = get_dirlist(dir, depth=self.depth, exclude=self._exclude_file)
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


