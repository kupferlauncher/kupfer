import gzip
import hashlib
import itertools
import os
import cPickle as pickle
import threading
import time
import operator

import gobject
gobject.threads_init()

from . import objects
from . import search, learn
from . import config, pretty, scheduler, task

# "Enums"
# Which pane
SourcePane, ActionPane, ObjectPane = (1,2,3)

# In two-pane or three-pane mode
SourceActionMode, SourceActionObjectMode = (1,2)

def identity(x):
	return x

def dress_leaves(seq, action):
	"""yield items of @seq "dressed" by the source controller"""
	sc = GetSourceController()
	for itm in seq:
		sc.decorate_object(itm.object, action=action)
		yield itm

class Searcher (object):
	"""
	This class searches KupferObjects efficiently, and
	stores searches in a cache for a very limited time (*)

	(*) As of this writing, the cache is used when the old key
	is a prefix of the search key.
	"""

	def __init__(self):
		self._source_cache = {}
		self._old_key = None

	def search(self, sources, key, score=True, item_check=None, decorator=None):
		"""
		@sources is a sequence listing the inputs, which should be
		Sources, TextSources or sequences of KupferObjects

		If @score, sort by rank.
		filters (with identity() as default):
			@item_check: Check items before adding to search pool
			@decorator: Decorate items before access

		Return (first, match_iter), where first is the first match,
		and match_iter an iterator to all matches, including the first match.
		"""
		if not self._old_key or not key.startswith(self._old_key):
			self._source_cache.clear()
		self._old_key = key

		if not item_check: item_check = identity
		if not decorator: decorator = identity

		match_iters = []
		for src in sources:
			fixedrank = 0
			rankables = None
			if isinstance(src, objects.Source):
				try:
					# stored rankables
					rankables = self._source_cache[src]
				except KeyError:
					# check uncached items
					items = item_check(src.get_leaves())
			elif isinstance(src, objects.TextSource):
				items = item_check(src.get_items(key))
				fixedrank = src.get_rank()
			else:
				items = item_check(src)

			if not rankables:
				rankables = search.make_rankables(items)

			if score:
				if fixedrank:
					rankables = search.add_rank_objects(rankables, fixedrank)
				elif key:
					rankables = search.score_objects(rankables, key)
				matches = search.bonus_objects(rankables, key)
				if isinstance(src, objects.Source):
					# we fork off a copy of the iterator to save
					matches, self._source_cache[src] = itertools.tee(matches)
			else:
				# we only want to list them
				matches = rankables

			match_iters.append(matches)
		
		matches = itertools.chain(*match_iters)
		if score:
			matches = sorted(matches, key=operator.attrgetter("rank"),
					reverse=True)

		def as_set_iter(seq):
			"""yield items of @seq with set semantics; no duplicates"""
			coll = set()
			for obj in seq:
				reprobj = obj.object
				if reprobj not in coll:
					yield obj
					coll.add(reprobj)

		def valid_check(seq):
			"""yield items of @seq that are valid"""
			for itm in seq:
				obj = itm.object
				if (not hasattr(obj, "is_valid")) or obj.is_valid():
					yield itm

		def peekfirst(seq):
			"""This function will return (firstitem, iter)
			where firstitem is the first item of @seq or None if empty,
			and iter an equivalent copy of @seq
			"""
			seq = iter(seq)
			for itm in seq:
				old_iter = itertools.chain((itm, ), seq)
				return (itm, old_iter)
			return (None, seq)

		# Check if the items are valid as the search
		# results are accessed through the iterators
		unique_matches = as_set_iter(matches)
		match, match_iter = peekfirst(decorator(valid_check(unique_matches)))
		return match, match_iter

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
			assert isinstance(source, objects.Source), "Stored object not a Source"
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


class SourceController (pretty.OutputMixin):
	"""Control sources; loading, pickling, rescanning"""
	def __init__(self, pickle=True):
		self.rescanner = PeriodicRescanner(period=3)
		self.sources = set()
		self.toplevel_sources = set()
		self.text_sources = set()
		self.pickle = pickle
		self.content_decorators = set()
		self.action_decorators = set()

	def _as_set(self, s):
		if isinstance(s, set):
			return s
		return set(s)
	def add(self, srcs, toplevel=False):
		srcs = self._as_set(srcs)
		self._unpickle_or_rescan(srcs, rescan=toplevel)
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
			sourceindex = set(self.sources)
			kupfer_sources = objects.SourcesSource(self.sources)
			sourceindex.add(kupfer_sources)
			# Make sure firstlevel is ordered
			# So that it keeps the ordering.. SourcesSource first
			firstlevel = []
			firstlevel.append(objects.SourcesSource(sourceindex))
			firstlevel.extend(set(self.toplevel_sources))
			root_catalog = objects.MultiSource(firstlevel)
		else:
			root_catalog = None
		return root_catalog

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
		catalog_index = (objects.SourcesSource(self.sources), )
		for s in itertools.chain(self.sources, catalog_index):
			if self.good_source_for_types(s, types):
				firstlevel.add(s)
		return objects.MultiSource(firstlevel)

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
					# check if we already have source, then return that
					yield self[dsrc] if (dsrc in self) else dsrc

	def get_actions_for_leaf(self, leaf):
		for typ in self.action_decorators:
			if isinstance(leaf, typ):
				for act in self.action_decorators[typ]:
					yield act

	def decorate_object(self, obj, action=None):
		if hasattr(obj, "has_content"):
			types = tuple(action.object_types()) if action else ()
			contents = list(self.get_contents_for_leaf(obj, types))
			content = contents and contents[0]
			if len(contents) > 1:
				content = objects.SourcesSource(contents, name=unicode(obj),
						use_reprs=False)
			obj.add_content(content)

	def finish(self):
		self._pickle_sources(self.sources)
	def _unpickle_or_rescan(self, sources, rescan=True):
		"""
		Try to unpickle the source that is equivalent to the
		"dummy" instance @source, if it doesn't succeed,
		the "dummy" becomes live and is rescanned if @rescan
		"""
		sourcepickler = SourcePickler()
		for source in list(sources):
			if self.pickle:
				news = sourcepickler.unpickle_source(source)
			else:
				news = None
			if news:
				sources.remove(source)
				sources.add(news)
			elif rescan:
				# to "rescue the toplevel", we throw out sources that
				# raise exceptions on rescan
				try:
					self.rescanner.register_rescan(source, sync=True)
				except StandardError, exp:
					self.output_error("Loading %s: raised %s %s" % (
						source, type(exp).__name__, exp))
					sources.remove(source)

	def _pickle_sources(self, sources):
		if not self.pickle:
			return
		sourcepickler = SourcePickler()
		sourcepickler.rm_old_cachefiles()
		for source in sources:
			if source.is_dynamic():
				continue
			sourcepickler.pickle_source(source)

_source_controller = None
def GetSourceController():
	global _source_controller
	if _source_controller is None:
		_source_controller = SourceController()
	return _source_controller

class Pane (gobject.GObject):
	"""
	signals:
		search-result (match, match_iter, context)
	"""
	__gtype_name__ = "Pane"
	def __init__(self):
		super(Pane, self).__init__()
		self.selection = None
		self.latest_key = None
		self.outstanding_search = -1
		self.outstanding_search_id = -1
		self.searcher = Searcher()

	def select(self, item):
		self.selection = item
	def get_selection(self):
		return self.selection
	def reset(self):
		self.selection = None
	def get_latest_key(self):
		return self.latest_key
	def get_can_enter_text_mode(self):
		return False
	def emit_search_result(self, match, match_iter, context):
		self.emit("search-result", match, match_iter, context)

gobject.signal_new("search-result", Pane, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, 
		gobject.TYPE_PYOBJECT))

class LeafPane (Pane, pretty.OutputMixin):
	__gtype_name__ = "LeafPane"

	def __init__(self):
		super(LeafPane, self).__init__()
		self.source_stack = []
		self.source = None

	def _load_source(self, src):
		"""Try to get a source from the SourceController,
		if it is already loaded we get it from there, else
		returns @src"""
		sc = GetSourceController()
		if src in sc:
			return sc[src]
		return src

	def get_source(self):
		return self.source

	def source_rebase(self, src):
		self.source_stack = []
		self.source = self._load_source(src)
		self.refresh_data()

	def push_source(self, src):
		self.source_stack.append(self.source)
		self.source = self._load_source(src)
		self.refresh_data()

	def pop_source(self):
		"""Return True if succeeded"""
		if not len(self.source_stack):
			return False
		self.source = self.source_stack.pop()
		return True

	def is_at_source_root(self):
		"""Return True if we have no source stack"""
		return not self.source_stack

	def get_can_enter_text_mode(self):
		return self.is_at_source_root()

	def refresh_data(self):
		self.emit("new-source", self.source)

	def browse_up(self):
		"""Try to browse up to previous sources, from current
		source"""
		succ = self.pop_source()
		if not succ:
			if self.source.has_parent():
				self.source_rebase(self.source.get_parent())
				succ = True
		if succ:
			self.refresh_data()
		return succ

	def browse_down(self, alternate=False):
		"""Browse into @leaf if it's possible
		and save away the previous sources in the stack
		if @alternate, use the Source's alternate method"""
		leaf = self.get_selection()
		if leaf and leaf.has_content():
			self.push_source(leaf.content_source(alternate=alternate))
			return True
		return False

	def reset(self):
		"""Pop all sources and go back to top level"""
		Pane.reset(self)
		while self.pop_source():
			pass
		self.refresh_data()

	def search(self, key=u"", context=None, text_mode=False):
		"""
		filter for action @item
		"""
		self.latest_key = key
		sources = [ self.get_source() ] if not text_mode else []
		if key and self.is_at_source_root():
			# Only use text sources when we are at root catalog
			sc = GetSourceController()
			textsrcs = sc.get_text_sources()
			sources.extend(textsrcs)

		decorator = lambda seq: dress_leaves(seq, action=None)
		match, match_iter = self.searcher.search(sources, key, score=bool(key),
				decorator=decorator)
		self.emit_search_result(match, match_iter, context)

gobject.signal_new("new-source", LeafPane, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

class PrimaryActionPane (Pane):
	def set_item(self, item):
		"""Set which @item we are currently listing actions for"""
		self.current_item = item

	def search(self, key=u"", context=None, text_mode=False):
		"""Search: Register the search method in the event loop

		using @key, promising to return
		@context in the notification about the result, having selected
		@item in SourcePane

		If we already have a call to search, we remove the "source"
		so that we always use the most recently requested search."""

		self.latest_key = key
		leaf = self.current_item
		actions = list(leaf.get_actions()) if leaf else []
		sc = GetSourceController()
		if leaf:
			for act in sc.get_actions_for_leaf(leaf):
				actions.append(act)

		actions = [a for a in actions if a.valid_for_item(self.current_item)]
		sources = (actions, )
		match, match_iter = self.searcher.search(sources, key)
		self.emit_search_result(match, match_iter, context)

class SecondaryObjectPane (LeafPane):
	__gtype_name__ = "SecondaryObjectPane"
	def __init__(self):
		LeafPane.__init__(self)
		self.current_item = None
		self.current_action = None
	def reset(self):
		self.source = None
		self.source_stack = None
		LeafPane.reset(self)
		self.searcher = Searcher()
	def set_item_and_action(self, item, act):
		self.current_item = item
		self.current_action = act
		if item and act:
			ownsrc = act.object_source(item)
			if ownsrc:
				self.source_rebase(ownsrc)
			else:
				sc = GetSourceController()
				self.source_rebase(sc.root_for_types(act.object_types()))
		else:
			self.reset()

	def get_can_enter_text_mode(self):
		"""Check if there are any reasonable text sources for this action"""
		atroot = self.is_at_source_root()
		types = tuple(self.current_action.object_types())
		sc = GetSourceController()
		textsrcs = sc.get_text_sources()
		return (atroot and
			any(sc.good_source_for_types(s, types) for s in textsrcs))

	def search(self, key=u"", context=None, text_mode=False):
		"""
		filter for action @item
		"""
		self.latest_key = key
		sources = []
		if not text_mode or isinstance(self.get_source(), objects.TextSource):
			sources.append(self.get_source())
		if key and self.is_at_source_root():
			# Only use text sources when we are at root catalog
			sc = GetSourceController()
			textsrcs = sc.get_text_sources()
			sources.extend(textsrcs)

		types = tuple(self.current_action.object_types())
		def type_obj_check(itms):
			valid_object = self.current_action.valid_object
			item = self.current_item
			for i in itms:
				if (isinstance(i, types) and valid_object(i, for_item=item)):
					yield i
		def type_check(itms):
			for i in itms:
				if isinstance(i, types):
					yield i

		if hasattr(self.current_action, "valid_object"):
			item_check = type_obj_check
		else:
			item_check = type_check

		decorator = lambda seq: dress_leaves(seq, action=self.current_action)

		match, match_iter = self.searcher.search(sources, key, score=True,
				item_check=item_check, decorator=decorator)
		self.emit_search_result(match, match_iter, context)

class DataController (gobject.GObject, pretty.OutputMixin):
	"""
	Sources <-> Actions controller

	The data controller must be created before main program commences,
	so it can register itself at the scheduler correctly.
	"""
	__gtype_name__ = "DataController"

	def __init__(self):
		super(DataController, self).__init__()

		self.source_pane = LeafPane()
		self.object_pane = SecondaryObjectPane()
		self.source_pane.connect("new-source", self._new_source)
		self.object_pane.connect("new-source", self._new_source)
		self.action_pane = PrimaryActionPane()
		self._panectl_table = {
			SourcePane : self.source_pane,
			ActionPane : self.action_pane,
			ObjectPane : self.object_pane,
			}
		for pane, ctl in self._panectl_table.items():
			ctl.connect("search-result", self._pane_search_result, pane)
		self.mode = None
		self._search_ids = itertools.count(1)
		self._task_runner = task.TaskRunner(end_on_finish=False)

		sch = scheduler.GetScheduler()
		sch.connect("load", self._load)
		sch.connect("finish", self._finish)

	def set_sources(self, S_sources, s_sources):
		"""Init the DataController with the given list of sources

		@S_sources are to be included directly in the catalog,
		@s_souces as just as subitems

		This should be run before main program commences.
		"""
		self.direct_sources = set(S_sources)
		self.other_sources = set(s_sources) - set(S_sources)

	def register_text_sources(self, srcs):
		"""Pass in text sources as @srcs

		we register text sources """
		sc = GetSourceController()
		sc.add_text_sources(srcs)
	
	def register_action_decorators(self, acts):
		# Keep a dictionary with Leaf type as key
		decorate_types = {}
		for act in acts:
			applies = act.item_types()
			for appl_type in applies:
				decorate_with = decorate_types.get(appl_type, [])
				decorate_with.append(act)
				decorate_types[appl_type] = decorate_with
		sc = GetSourceController()
		sc.set_action_decorators(decorate_types)
		self.output_debug("Action decorators:")
		for typ in decorate_types:
			self.output_debug(typ.__name__)
			for dec in decorate_types[typ]:
				self.output_debug(type(dec).__module__, type(dec).__name__,sep=".")

	def register_content_decorators(self, contents):
		# Keep a dictionary with Leaf type as key
		decorate_item_types = {}
		for c in contents:
			applies = c.decorates_type()
			decorate_with = decorate_item_types.get(applies, [])
			decorate_with.append(c)
			decorate_item_types[applies] = decorate_with
		sc = GetSourceController()
		sc.set_content_decorators(decorate_item_types)
		self.output_debug("Content decorators:")
		for typ in decorate_item_types:
			self.output_debug(typ.__name__)
			for dec in decorate_item_types[typ]:
				self.output_debug(dec.__module__, dec.__name__, sep=".")

	def _load(self, sched):
		"""Load data from persistent store"""
		self._setup_plugins()
		sc = GetSourceController()
		sc.add(self.direct_sources, toplevel=True)
		sc.add(self.other_sources, toplevel=False)
		self.source_pane.source_rebase(sc.root)
		learn.load()

	def _setup_plugins(self):
		from kupfer import settings, plugins
		from kupfer.plugins import (load_plugin_sources, sources_attribute,
				action_decorators_attribute, text_sources_attribute,
				content_decorators_attribute,
				initialize_plugin)

		s_sources = []
		S_sources = []

		def dir_source(opt):
			abs = os.path.abspath(os.path.expanduser(opt))
			return objects.DirectorySource(abs)

		def file_source(opt, depth=1):
			abs = os.path.abspath(os.path.expanduser(opt))
			return objects.FileSource((abs,), depth)

		setctl = settings.GetSettingsController()
		source_config = setctl.get_config

		text_sources = []
		action_decorators = []
		content_decorators = []

		for item in plugins.get_plugin_ids():
			if not setctl.get_plugin_enabled(item):
				continue
			initialize_plugin(item)
			text_sources.extend(load_plugin_sources(item, text_sources_attribute))
			action_decorators.extend(load_plugin_sources(item,
				action_decorators_attribute))
			content_decorators.extend(load_plugin_sources(item,
				content_decorators_attribute, instantiate=False))
			if setctl.get_plugin_is_toplevel(item):
				S_sources.extend(load_plugin_sources(item))
			else:
				s_sources.extend(load_plugin_sources(item))

		dir_depth = source_config("DeepDirectories", "Depth")

		for item in source_config("Directories", "Catalog"):
			s_sources.append(dir_source(item))
		for item in source_config("DeepDirectories","Catalog"):
			s_sources.append(file_source(item, dir_depth))
		for item in source_config("Directories", "Direct"):
			S_sources.append(dir_source(item))
		for item in source_config("DeepDirectories", "Direct"):
			S_sources.append(file_source(item, dir_depth))

		if not S_sources and not s_sources:
			pretty.print_info(__name__, "No sources found!")

		self.set_sources(S_sources, s_sources)
		self.register_text_sources(text_sources)
		self.register_action_decorators(action_decorators)
		self.register_content_decorators(content_decorators)

	def _finish(self, sched):
		self.output_info("Saving data...")
		learn.finish()
		self.output_info("Saving cache...")
		GetSourceController().finish()

	def _new_source(self, ctr, src):
		if ctr is self.source_pane:
			pane = SourcePane
		elif ctr is self.object_pane:
			pane = ObjectPane
		self.emit("source-changed", pane, src)

	def reset(self):
		self.source_pane.reset()
		self.action_pane.reset()

	def cancel_search(self, pane=None):
		"""Cancel any outstanding search, or the search for @pane"""
		panes = (pane, ) if pane else iter(self._panectl_table)
		for pane in panes:
			ctl = self._panectl_table[pane]
			if ctl.outstanding_search > 0:
				gobject.source_remove(ctl.outstanding_search)
				ctl.outstanding_search = -1

	def search(self, pane, key=u"", context=None, interactive=False, lazy=False,
			text_mode=False):
		"""Search: Register the search method in the event loop

		Will search in @pane's base using @key, promising to return
		@context in the notification about the result.

		if @interactive, the search result will return immediately
		if @lazy, will slow down search result reporting
		"""

		self.cancel_search(pane)
		ctl = self._panectl_table[pane]
		ctl.outstanding_search_id = self._search_ids.next()
		wrapcontext = (ctl.outstanding_search_id, context)
		if interactive:
			ctl.search(key, wrapcontext, text_mode)
		else:
			timeout = 300 if lazy else 0 if not key else 50/len(key)
			ctl.outstanding_search = gobject.timeout_add(timeout, ctl.search, 
					key, wrapcontext, text_mode)

	def _pane_search_result(self, panectl, match,match_iter, wrapcontext, pane):
		search_id, context = wrapcontext
		if not search_id is panectl.outstanding_search_id:
			self.output_debug("Skipping late search", match, context)
			return True
		self.emit("search-result", pane, match, match_iter, context)

	def select(self, pane, item):
		"""Select @item in @pane to self-update
		relevant places"""
		# If already selected, do nothing
		panectl = self._panectl_table[pane]
		if item is panectl.get_selection():
			return
		self.cancel_search()
		panectl.select(item)
		if pane is SourcePane:
			assert not item or isinstance(item, objects.Leaf), \
					"Selection in Source pane is not a Leaf!"
			# populate actions
			self.action_pane.set_item(item)
			self.search(ActionPane, interactive=True)
		elif pane is ActionPane:
			assert not item or isinstance(item, objects.Action), \
					"Selection in Source pane is not an Action!"
			if item and item.requires_object():
				newmode = SourceActionObjectMode
			else:
				newmode = SourceActionMode
			if newmode is not self.mode:
				self.mode = newmode
				self.emit("mode-changed", self.mode, item)
			if self.mode is SourceActionObjectMode:
				# populate third pane
				self.object_pane.set_item_and_action(self.source_pane.get_selection(), item)
				self.search(ObjectPane, lazy=True)
		elif pane is ObjectPane:
			assert not item or isinstance(item, objects.Leaf), \
					"Selection in Object pane is not a Leaf!"

	def get_can_enter_text_mode(self, pane):
		panectl = self._panectl_table[pane]
		return panectl.get_can_enter_text_mode()

	def validate(self):
		"""Check if all selected items are still valid
		(for example after being spawned again, old item
		still focused)

		This will trigger .select() with None if items
		are not valid..
		"""
		for paneenum, pane in ((SourcePane, self.source_pane),
				(ActionPane, self.action_pane)):
			sel = pane.get_selection()
			if not sel:
				break
			if hasattr(sel, "is_valid") and not sel.is_valid():
				self.emit("pane-reset", paneenum, None)
				self.select(paneenum, None)

	def browse_up(self, pane):
		"""Try to browse up to previous sources, from current
		source"""
		if pane is SourcePane:
			return self.source_pane.browse_up()
		if pane is ObjectPane:
			return self.object_pane.browse_up()
	
	def browse_down(self, pane, alternate=False):
		"""Browse into @leaf if it's possible
		and save away the previous sources in the stack
		if @alternate, use the Source's alternate method"""
		if pane is ActionPane:
			return
		# record used object if we browse down
		panectl = self._panectl_table[pane]
		sel, key = panectl.get_selection(), panectl.get_latest_key()
		if panectl.browse_down(alternate=alternate):
			learn.record_search_hit(sel, key)

	def activate(self):
		"""
		Activate current selection
		"""
		action = self.action_pane.get_selection()
		leaf = self.source_pane.get_selection()
		sobject = self.object_pane.get_selection()
		if not action or not leaf:
			self.output_info("There is no selection!")
			return
		if not sobject and self.mode is SourceActionObjectMode:
			self.output_info("There is no third object!")
			return
		if self.mode is SourceActionMode:
			ret = action.activate(leaf)
		elif self.mode is SourceActionObjectMode:
			ret = action.activate(leaf, sobject)

		# register search to learning database
		learn.record_search_hit(leaf, self.source_pane.get_latest_key())
		learn.record_search_hit(action, self.action_pane.get_latest_key())
		if sobject:
			learn.record_search_hit(sobject, self.object_pane.get_latest_key())

		# handle actions returning "new contexts"
		if action.is_factory() and ret:
			self.source_pane.push_source(ret)
			return
		if action.has_result() and ret:
			self.emit("pane-reset", SourcePane, search.wrap_rankable(ret))
			return
		elif action.is_async():
			self._task_runner.add_task(ret)
		self.emit("launched-action", SourceActionMode, leaf, action)

# pane cleared or set with new item
# pane, item
gobject.signal_new("pane-reset", DataController, gobject.SIGNAL_RUN_LAST,
	gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT,))

# pane, match, iter to matches, context
gobject.signal_new("search-result", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))

gobject.signal_new("source-changed", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT,))

# mode, None(?)
gobject.signal_new("mode-changed", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT,))

# mode, item, action
gobject.signal_new("launched-action", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))


