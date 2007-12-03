# -*- coding: UTF-8 -*-

import gobject
import gnomevfs
import itertools
from os import path

import utils

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
	"""
	Base class for Actions and Leaves
	"""
	icon_size = 96
	def __init__(self, name):
		self.name = name
	
	def __str__(self):
		return self.name

	def get_pixbuf(self):
		return None


class Leaf (KupferObject):
	def __init__(self, obj, value):
		super(Leaf, self).__init__(value)
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
		acts = [Echo(), Dragbox()]
		default = None
		if path.isdir(self.object):
			acts.extend([OpenTerminal()])
			default = Show(name="Open")
		else:
			type = gnomevfs.get_mime_type(self.object)
			def_app = gnomevfs.mime_get_default_application(type)
			types = gnomevfs.mime_get_all_applications(type)
			apps = set()
			if def_app:
				default = Show(def_app)
				apps.add(def_app[1])
			for info in types:
				id = info[1]
				if id not in apps:
					acts.append(Show(info))
					apps.add(id)
		if not default:
			default = Show()
		acts.insert(0, default)
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
		icon = utils.get_icon_for_uri(uri, self.icon_size)
		return icon

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
	
	def get_pixbuf(self):
		return utils.get_icon_for_name("utilities-terminal", self.icon_size)


class Echo (Action):
	def __init__(self):
		super(Echo, self).__init__("Echo")
	
	def activate(self, leaf):
		print "Echo:", leaf.object
	
	def __str__(self):
		return "Echo"

class Show (Action):
	def __init__(self, app_spec=None, name=None):
		"""
		Action that launches a file with app_spec

		app_spec: application info as given by for example mime_get_default_application
		if app_spec is None, open with default viewer
		"""
		self.app_spec = app_spec
		if not name:
			if self.app_spec:
				name= "Show with %s" % self.app_spec[1]
			else:
				name = "Show"
		super(Show, self).__init__(name)

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
	
	def activate(self, leaf):
		print "Show: %s" % (leaf.object,)
		uri = gnomevfs.get_uri_from_local_path(leaf.object)
		if self.app_spec:
			self._open_uri(uri, self.app_spec)
		else:
			gnomevfs.url_show(uri)
	
	def get_pixbuf(self):
		if not self.app_spec:
			return utils.get_application_icon(None, self.icon_size)
		app_icon = utils.get_desktop_icon(self.app_spec[0], self.icon_size)
		if not app_icon:
			app_icon= utils.get_application_icon(None, self.icon_size)
		return app_icon
		

class OpenTerminal (Action):
	def __init__(self):
		super(OpenTerminal, self).__init__("Open Terminal here")
	
	def activate(self, leaf):
		argv = ["gnome-terminal"]
		print argv
		utils.spawn_async(argv, in_dir=leaf.object)


class Dragbox (Action):
	def __init__(self):
		super(Dragbox, self).__init__("Put on dragbox")
	
	def activate(self, leaf):
		path = leaf.object
		argv = ["dragbox", "--file", path]
		gobject.spawn_async(argv, flags=gobject.SPAWN_SEARCH_PATH)


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
			files = utils.get_dirlist(dir, depth=self.depth, exclude=self._exclude_file)
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
		dirlist = utils.get_dirlist(self.directory, exclude=lambda f: f.startswith("."))
		def file_leaves(files):
			for file in files:
				basename = path.basename(file)
				if path.isdir(file):
					basename += "/"
				yield FileLeaf(file, basename)

		return file_leaves(dirlist)

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

class Launch (Action):
	def __init__(self):
		Action.__init__(self, "Launch")
	
	def activate(self, leaf):
		desktop_item = leaf.object
		args = []
		desktop_item.launch(args, 0)
	
	def get_pixbuf(self):
		return utils.get_icon_for_name("exec", self.icon_size)

class AppLeaf (Leaf):
	def __init__(self, item):
		from gnomedesktop import KEY_NAME, KEY_EXEC
		value = "%s (%s)" % (item.get_localestring(KEY_NAME), item.get_string(KEY_NAME))
		Leaf.__init__(self, item, value)
	
	def get_actions(self):
		return (Launch(),)

	def get_pixbuf(self):
		from gtk import icon_theme_get_default
		icon_file = self.object.get_icon(icon_theme_get_default())
		#icon_file = gnomevfs.get_local_path_from_uri(icon_uri)
		if not icon_file:
			return utils.get_application_icon(None, self.icon_size)
		return utils.get_icon_from_file(icon_file, self.icon_size)

class AppSource (Source):

	def get_items(self):
		dirs = utils.get_xdg_data_dirs()
		from os import walk
		from gnomedesktop import item_new_from_file, LOAD_ONLY_IF_EXISTS
		import gnomedesktop as gd

		desktop_files = []

		inc_files = set()

		def add_desktop_item(item):
			# "true" or "false"
			hid = item.get_string(gd.KEY_HIDDEN)
			nodisp = item.get_string(gd.KEY_NO_DISPLAY)
			type = item.get_string(gd.KEY_TYPE)

			if "true" in (hid, nodisp) or (type != "Application"):
				return
			file = gnomevfs.get_local_path_from_uri(item.get_location())
			name = path.basename(file)
			if name in inc_files:
				print name, "already in"
				return
			inc_files.add(name)
			desktop_files.append(item)
		
		for d in dirs:
			apps = path.join(d, "applications")
			if not path.exists(apps):
				continue
			for root, dirnames, fnames in walk(apps):
				for file in fnames:
					abspath = path.join(root, file)
					item = item_new_from_file(abspath, LOAD_ONLY_IF_EXISTS)
					if item:
						add_desktop_item(item)

				del dirnames[:]
		#print desktop_files
		
		return [AppLeaf(item) for item in desktop_files]


				



