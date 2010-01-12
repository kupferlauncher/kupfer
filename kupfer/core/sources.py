import gzip
import hashlib
import itertools
import cPickle as pickle
import os
import threading
import time

import gobject
gobject.threads_init()

from kupfer import config, pretty, scheduler
from kupfer.obj import base, sources

class PeriodicRescanner (gobject.GObject, pretty.OutputMixin):
	"""
	Periodically rescan a @catalog of sources

	Do first rescan after @startup seconds, then
	followup with rescans in @period.

	Each campaign of rescans is separarated by @campaign
	seconds
	"""
	def __init__(self, period=5, startup=10, campaign=3600):
		super(PeriodicRescanner, self).__init__()
		self.startup = startup
		self.period = period
		self.campaign=campaign
		self.timer = scheduler.Timer()
		# Source -> time mapping
		self.latest_rescan_time = {}
		self._min_rescan_interval = campaign/10

	def set_catalog(self, catalog):
		self.catalog = catalog
		self.cur = iter(self.catalog)
		self.output_debug("Registering new campaign, in %d s" % self.startup)
		self.timer.set(self.startup, self._new_campaign)
	
	def _new_campaign(self):
		self.output_info("Starting new campaign, interval %d s" % self.period)
		self.cur = iter(self.catalog)
		self.timer.set(self.period, self._periodic_rescan_helper)

	def _periodic_rescan_helper(self):
		# Advance until we find a source that was not recently rescanned
		for next in self.cur:
			oldtime = self.latest_rescan_time.get(next, 0)
			if (time.time() - oldtime) > self._min_rescan_interval:
				self.timer.set(self.period, self._periodic_rescan_helper)
				self._start_source_rescan(next)
				return
		# No source to scan found
		self.output_info("Campaign finished, pausing %d s" % self.campaign)
		self.timer.set(self.campaign, self._new_campaign)

	def register_rescan(self, source, sync=False):
		"""Register an object for rescan
		If @sync, it will be rescanned synchronously
		"""
		self._start_source_rescan(source, sync)

	def _start_source_rescan(self, source, sync=False):
		self.latest_rescan_time[source] = time.time()
		if sync:
			self.rescan_source(source)
		elif not source.is_dynamic():
			thread = threading.Thread(target=self.rescan_source, args=(source,))
			thread.setDaemon(True)
			thread.start()

	def rescan_source(self, source):
		items = source.get_leaves(force_update=True)
		gobject.idle_add(self.emit, "reloaded-source", source)

gobject.signal_new("reloaded-source", PeriodicRescanner, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

class SourcePickler (pretty.OutputMixin):
	"""
	Takes care of pickling and unpickling Kupfer Sources.
	"""
	pickle_version = 3
	name_template = "k%s-v%d.pickle.gz"

	def __init__(self):
		self.open = lambda f,mode: gzip.open(f, mode, compresslevel=3)

	def rm_old_cachefiles(self):
		"""Checks if there are old cachefiles from last version,
		and deletes those
		"""
		for dpath, dirs, files in os.walk(config.get_cache_home()):
			# Look for files matching beginning and end of
			# name_template, with the previous file version
			chead, ctail = self.name_template.split("%s")
			ctail = ctail % ((self.pickle_version -1),)
			obsolete_files = []
			for cfile in files:
				if cfile.startswith(chead) and cfile.endswith(ctail):
					cfullpath = os.path.join(dpath, cfile)
					obsolete_files.append(cfullpath)
		if obsolete_files:
			self.output_info("Removing obsolete cache files:", sep="\n",
					*obsolete_files)
			for fpath in obsolete_files:
				# be overly careful
				assert fpath.startswith(config.get_cache_home())
				assert "kupfer" in fpath
				os.unlink(fpath)

	def get_filename(self, source):
		"""Return cache filename for @source"""
		bytes = hashlib.md5(repr(source)).digest()
		hashstr = bytes.encode("base64").rstrip("\n=").replace("/", "-")
		filename = self.name_template % (hashstr, self.pickle_version)
		return os.path.join(config.get_cache_home(), filename)

	def unpickle_source(self, source):
		cached = self._unpickle_source(self.get_filename(source))
		if not cached:
			return None

		# check consistency
		if source == cached:
			return cached
		else:
			self.output_debug("Cached version mismatches", source)
		return None
	def _unpickle_source(self, pickle_file):
		try:
			pfile = self.open(pickle_file, "rb")
		except IOError, e:
			return None
		try:
			source = pickle.loads(pfile.read())
			assert isinstance(source, base.Source), "Stored object not a Source"
			sname = os.path.basename
			self.output_debug("Loading", source, "from", sname(pickle_file))
		except (pickle.PickleError, Exception), e:
			source = None
			self.output_info("Error loading %s: %s" % (pickle_file, e))
		return source

	def pickle_source(self, source):
		return self._pickle_source(self.get_filename(source), source)
	def _pickle_source(self, pickle_file, source):
		"""
		When writing to a file, use pickle.dumps()
		and then write the file in one go --
		if the file is a gzip file, pickler's thousands
		of small writes are very slow
		"""
		output = self.open(pickle_file, "wb")
		sname = os.path.basename
		self.output_debug("Storing", source, "as", sname(pickle_file))
		output.write(pickle.dumps(source, pickle.HIGHEST_PROTOCOL))
		output.close()
		return True

class SourceDataPickler (pretty.OutputMixin):
	""" Takes care of pickling and unpickling Kupfer Sources' configuration
	or data.

	The SourceDataPickler requires a protocol of three methods:

	config_save_name()
	  Return an ascii name to be used as a token/key for the configuration

	config_save()
	  Return an object to be saved as configuration

	config_restore(obj)
	  Receive the configuration object `obj' to load
	"""
	pickle_version = 1
	name_template = "config-%s-v%d.pickle"

	def __init__(self):
		self.open = open

	@classmethod
	def get_filename(cls, source):
		"""Return filename for @source"""
		name = source.config_save_name()
		filename = cls.name_template % (name, cls.pickle_version)
		return config.save_config_file(filename)

	@classmethod
	def source_has_config(self, source):
		return getattr(source, "config_save_name", None)

	def load_source(self, source):
		data = self._load_data(self.get_filename(source))
		if not data:
			return True
		source.config_restore(data)

	def _load_data(self, pickle_file):
		try:
			pfile = self.open(pickle_file, "rb")
		except IOError, e:
			return None
		try:
			data = pickle.load(pfile)
			sname = os.path.basename(pickle_file)
			self.output_debug("Loaded configuration from", sname)
			self.output_debug(data)
		except (pickle.PickleError, Exception), e:
			data = None
			self.output_error("Loading %s: %s" % (pickle_file, e))
		return data

	def save_source(self, source):
		return self._save_data(self.get_filename(source), source)
	def _save_data(self, pickle_file, source):
		sname = os.path.basename(pickle_file)
		obj = source.config_save()
		try:
			data = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)
		except pickle.PickleError, exc:
			import traceback
			self.output_error("Unable to save configuration for", source)
			self.output_error("Saving configuration raised an exception:")
			traceback.print_exc()
			self.output_error("Please file a bug report")
			data = None
		if data:
			self.output_debug("Storing configuration for", source, "as", sname)
			output = self.open(pickle_file, "wb")
			output.write(data)
			output.close()
		return True

class SourceController (pretty.OutputMixin):
	"""Control sources; loading, pickling, rescanning"""
	def __init__(self):
		self.rescanner = PeriodicRescanner(period=3)
		self.sources = set()
		self.toplevel_sources = set()
		self.text_sources = set()
		self.content_decorators = set()
		self.action_decorators = set()

	def add(self, srcs, toplevel=False):
		srcs = set(self._try_unpickle(srcs))
		self.sources.update(srcs)
		if toplevel:
			self.toplevel_sources.update(srcs)
		self.rescanner.set_catalog(self.sources)
	def add_text_sources(self, srcs):
		self.text_sources.update(srcs)
	def get_text_sources(self):
		return self.text_sources
	def set_content_decorators(self, decos):
		self.content_decorators = decos
	def set_action_decorators(self, decos):
		self.action_decorators = decos
		for typ in self.action_decorators:
			self._disambiguate_actions(self.action_decorators[typ])
	def _disambiguate_actions(self, actions):
		"""Rename actions by the same name (adding a suffix)"""
		# FIXME: Disambiguate by plugin name, not python module name
		names = {}
		renames = []
		for action in actions:
			name = unicode(action)
			if name in names:
				renames.append(names[name])
				renames.append(action)
			else:
				names[name] = action
		for action in renames:
			self.output_debug("Disambiguate Action %s" % (action, ))
			action.name += " (%s)" % (type(action).__module__.split(".")[-1],)

	def clear_sources(self):
		pass
	def __contains__(self, src):
		return src in self.sources
	def __getitem__(self, src):
		if not src in self:
			raise KeyError
		for s in self.sources:
			if s == src:
				return s
	@property
	def root(self):
		"""Get the root source of catalog"""
		if len(self.sources) == 1:
			root_catalog, = self.sources
		elif len(self.sources) > 1:
			firstlevel = self._firstlevel
			root_catalog = sources.MultiSource(firstlevel)
		else:
			root_catalog = None
		return root_catalog

	@property
	def _firstlevel(self):
		firstlevel = getattr(self, "_pre_root", None)
		if firstlevel:
			return firstlevel
		sourceindex = set(self.sources)
		kupfer_sources = sources.SourcesSource(self.sources)
		sourceindex.add(kupfer_sources)
		# Make sure firstlevel is ordered
		# So that it keeps the ordering.. SourcesSource first
		firstlevel = []
		firstlevel.append(sources.SourcesSource(sourceindex))
		firstlevel.extend(set(self.toplevel_sources))
		self._pre_root = firstlevel
		return firstlevel

	@classmethod
	def good_source_for_types(cls, s, types):
		"""return whether @s provides good leaves for @types
		"""
		provides = list(s.provides())
		if not provides:
			return True
		for t in provides:
			if issubclass(t, types):
				return True

	def root_for_types(self, types):
		"""
		Get root for a flat catalog of all catalogs
		providing at least Leaves of @types

		Take all sources which:
			Provide a type T so that it is a subclass
			to one in the set of types we want
		"""
		types = tuple(types)
		firstlevel = set()
		# include the Catalog index since we want to include
		# the top of the catalogs (like $HOME)
		catalog_index = (sources.SourcesSource(self.sources), )
		for s in itertools.chain(self.sources, catalog_index):
			if self.good_source_for_types(s, types):
				firstlevel.add(s)
		return sources.MultiSource(firstlevel)

	def get_canonical_source(self, source):
		"Return the canonical instance for @source"
		# check if we already have source, then return that
		if source in self:
			return self[source]
		else:
			source.initialize()
			return source

	def get_contents_for_leaf(self, leaf, types=None):
		"""Iterator of content sources for @leaf,
		providing @types (or None for all)"""
		for typ in self.content_decorators:
			if not isinstance(leaf, typ):
				continue
			for content in self.content_decorators[typ]:
				dsrc = content.decorate_item(leaf)
				if dsrc:
					if types and not self.good_source_for_types(dsrc, types):
						continue
					yield self.get_canonical_source(dsrc)

	def get_actions_for_leaf(self, leaf):
		for typ in self.action_decorators:
			if isinstance(leaf, typ):
				for act in self.action_decorators[typ]:
					yield act

	def decorate_object(self, obj, action=None):
		if hasattr(obj, "has_content"):
			types = tuple(action.object_types()) if action else ()
			contents = list(self.get_contents_for_leaf(obj, types))
			content = contents[0] if contents else None
			if len(contents) > 1:
				content = sources.SourcesSource(contents, name=unicode(obj),
						use_reprs=False)
			obj.add_content(content)

	def finish(self):
		self._pickle_sources(self.sources)

	def save_data(self):
		configsaver = SourceDataPickler()
		for source in self.sources:
			if configsaver.source_has_config(source):
				configsaver.save_source(source)

	def _try_unpickle(self, sources):
		"""
		Try to unpickle the source that is equivalent to the
		"dummy" instance @source, if it doesn't succeed,
		the "dummy" becomes live.
		"""
		sourcepickler = SourcePickler()
		configsaver = SourceDataPickler()
		for source in set(sources):
			news = None
			if configsaver.source_has_config(source):
				configsaver.load_source(source)
			else:
				news = sourcepickler.unpickle_source(source)
			yield news or source

	def _pickle_sources(self, sources):
		sourcepickler = SourcePickler()
		sourcepickler.rm_old_cachefiles()
		for source in sources:
			if (source.is_dynamic() or
			    SourceDataPickler.source_has_config(source)):
				continue
			sourcepickler.pickle_source(source)

	def _checked_rescan_source(self, source, force=True):
		"""
		Rescan @source and check for exceptions, if it
		raises, we remove it from our source catalog
		"""
		# to "rescue the toplevel", we throw out sources that
		# raise exceptions on rescan
		try:
			if force:
				self.rescanner.register_rescan(source, sync=True)
			else:
				source.get_leaves()
		except Exception:
			import traceback
			self.output_error("Loading %s raised an exception:" % source)
			traceback.print_exc()
			self.output_error("This error is probably a bug in %s" % source)
			self.output_error("Please file a bug report")
			self.sources.discard(source)
			self.toplevel_sources.discard(source)

	def cache_toplevel_sources(self):
		"""Ensure that all toplevel sources are cached"""
		for src in set(self.sources):
			src.initialize()
		for src in set(self.toplevel_sources):
			self._checked_rescan_source(src, force=False)

_source_controller = None
def GetSourceController():
	global _source_controller
	if _source_controller is None:
		_source_controller = SourceController()
	return _source_controller

