import gobject
import threading
import cPickle as pickle
import itertools

gobject.threads_init()

from . import search
from . import objects
from . import config
from . import pretty
from . import learn

def SearchTask(sender, sources, key, signal, score=True, context=None):
	"""
	@sources is a dict listing the inputs and how they are ranked

	if @score, sort by score, else no sort
	"""

	match_iters = []
	for src in sources:
		items = ()
		rank = 0
		if isinstance(src, objects.Source):
			items = src.get_leaves()
		elif isinstance(src, objects.TextSource):
			items = src.get_items(key)
			rank = src.get_rank()
		else:
			items = src
		#raise Exception("No souce in SearchTask description")

		if score:
			rankables = search.make_rankables(items)
		else:
			rankables = search.make_nosortrankables(items)

		if not rank:
			scored = search.score_objects(rankables, key)
			matches = search.bonus_objects(scored, key)
		else:
			# we have a given rank
			matches = search.add_rank_objects(rankables, rank)

		match_iters.append(matches)
	
	def as_set_iter(seq):
		"""Generator with set semantics: Generate items on the fly,
		but no duplicates
		"""
		coll = set()
		getobj = lambda o: o.object if hasattr(o, "object") else None
		for obj in seq:
			if getobj(obj) not in coll:
				yield obj
				coll.add(getobj(obj))

	def itemranker(item):
		"""
		Sort key for the items.
		Sort first by rank, then by value (name)
		(but only sort by value if rank >= 0 to keep
		default ordering!)
		"""
		return (-item.rank, item.rank and item.value)
	matches = list(as_set_iter(itertools.chain(*match_iters)))
	matches.sort()

	if len(matches):
		match = matches[0]
	else:
		match = None
	gobject.idle_add(sender.emit, signal, match, iter(matches), context)

class RescanThread (threading.Thread, pretty.OutputMixin):
	def __init__(self, source, sender, signal, context=None, **kwargs):
		super(RescanThread, self).__init__(**kwargs)
		self.source = source
		self.sender = sender
		self.signal = signal
		self.context = context

	def run(self):
		self.output_info(repr(self.source))
		items = self.source.get_leaves(force_update=True)
		if self.sender and self.signal:
			gobject.idle_add(self.sender.emit, self.signal, self.context)

class PeriodicRescanner (gobject.GObject, pretty.OutputMixin):
	"""
	Periodically rescan a @catalog of sources

	Do first rescan after @startup seconds, then
	followup with rescans in @period.

	Each campaign of rescans is separarated by @campaign
	seconds
	"""
	def __init__(self, catalog, period=5, startup=10, campaign=3600):
		super(PeriodicRescanner, self).__init__()
		self.startup = startup
		self.period = period
		self.campaign=campaign
		self.cur_event = 0

	def set_catalog(self, catalog):
		self.catalog = catalog
		self.cur = iter(self.catalog)
		if self.cur_event:
			gobject.source_remove(self.cur_event)
		self.output_debug("Registering new campaign, in %d s" % self.startup)
		self.cur_event = gobject.timeout_add_seconds(self.startup, self._new_campaign)
	
	def _new_campaign(self):
		self.output_info("Starting new campaign, interval %d s" % self.period)
		self.cur = iter(self.catalog)
		self.cur_event = gobject.timeout_add_seconds(self.period, self._periodic_rescan_helper)

	def _periodic_rescan_helper(self):
		try:
			next = self.cur.next()
		except StopIteration:
			self.output_info("Campaign finished, pausing %d s" % self.campaign)
			self.cur_event = gobject.timeout_add_seconds(self.campaign, self._new_campaign)
			return False
		self.cur_event = gobject.idle_add(self.reload_source, next)
		return True

	def register_rescan(self, source, force=False):
		"""Register an object for rescan

		dynamic sources will only be rescanned if @force is True
		"""
		gobject.idle_add(self.reload_source, source, force)

	def reload_source(self, source, force=False):
		if force:
			source.get_leaves(force_update=True)
			self.emit("reloaded-source", source)
		elif not source.is_dynamic():
			rt = RescanThread(source, self, "reloaded-source", context=source)
			rt.start()

gobject.signal_new("reloaded-source", PeriodicRescanner, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

class SourcePickleService (pretty.OutputMixin, object):
	pickle_version = 1
	name_template = "kupfer-%s-v%d.pickle.gz"

	def __call__(self):
		return self
	def __init__(self):
		import gzip
		self.open = lambda f,mode: gzip.open(f, mode, compresslevel=3)

	def get_filename(self, source):
		from os import path

		hashstr = "%010d" % abs(hash(source))
		filename = self.name_template % (hashstr, self.pickle_version)
		return path.join(config.get_cache_home(), filename)

	def unpickle_source(self, source):
		return self._unpickle_source(self.get_filename(source))
	def _unpickle_source(self, pickle_file):
		try:
			pfile = self.open(pickle_file, "rb")
		except IOError, e:
			return None
		try:
			source = pickle.loads(pfile.read())
			assert isinstance(source, objects.Source), "Stored object not a Source"
			self.output_info("Reading %s from %s" % (source, pickle_file))
		except (pickle.PickleError, Exception), e:
			source = None
			self.output_debug("Error loading %s: %s" % (pickle_file, e))
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
		self.output_info("Saving %s to %s" % (source, pickle_file))
		output.write(pickle.dumps(source, pickle.HIGHEST_PROTOCOL))
		output.close()
		return True

SourcePickleService = SourcePickleService()

class SourceController (object):
	"""Control sources; loading, pickling, rescanning"""
	def __init__(self, pickle=True):
		self.rescanner = PeriodicRescanner([])
		self.sources = set()
		self.toplevel_sources = set()
		self.pickle = pickle
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
		"""Get the root source"""
		if len(self.sources) == 1:
			root_catalog, = self.sources
		elif len(self.sources) > 1:
			firstlevel = set(self.toplevel_sources)
			sourceindex = set(self.sources)
			kupfer_sources = objects.SourcesSource(self.sources)
			sourceindex.add(kupfer_sources)
			firstlevel.add(objects.SourcesSource(sourceindex))
			root_catalog = objects.MultiSource(firstlevel)
		else:
			root_catalog = None
		return root_catalog

	def finish(self):
		self._pickle_sources(self.sources)
	def _unpickle_or_rescan(self, sources, rescan=True):
		"""
		Try to unpickle the source that is equivalent to the
		"dummy" instance @source, if it doesn't succeed,
		the "dummy" becomes live and is rescanned if @rescan
		"""
		for source in list(sources):
			if self.pickle:
				news = SourcePickleService().unpickle_source(source)
			else:
				news = None
			if news:
				sources.remove(source)
				sources.add(news)
			elif rescan:
				self.rescanner.register_rescan(source, force=True)

	def _pickle_sources(self, sources):
		if not self.pickle:
			return
		for source in sources:
			if source.is_dynamic():
				continue
			SourcePickleService().pickle_source(source)


class DataController (gobject.GObject, pretty.OutputMixin):
	"""
	Sources <-> Actions controller

	This is a singleton, and should
	be inited using set_sources
	"""
	__gtype_name__ = "DataController"

	def __call__(self):
		return self

	def __init__(self):
		super(DataController, self).__init__()
		self.source = None
		self.sc = SourceController()
		self.search_handle = -1

		self.latest_item_key = None
		self.latest_action_key = None
		self.text_sources = []
		self.decorate_types = {}

	def set_sources(self, S_sources, s_sources):
		"""Init the DataController with the given list of sources

		@S_sources are to be included directly in the catalog,
		@s_souces as just as subitems

		Must be followed by a call to DataController.load()
		"""
		self.direct_sources = set(S_sources)
		self.other_sources = set(s_sources) - set(S_sources)

	def register_text_sources(self, srcs):
		"""Pass in text sources as @srcs

		we register text sources """
		print "Got text sources", srcs
		self.text_sources.extend(srcs)
	
	def register_action_decorators(self, acts):
		# assume none are dynamic for now
		# Keep a dictionary with Leaf type as key
		# and value actions to add
		for act in acts:
			applies = act.applies_to()
			for appl_type in applies:
				decorate_with = self.decorate_types.get(appl_type, [])
				decorate_with.extend(act.get_actions())
				self.decorate_types[appl_type] = decorate_with
		print self.decorate_types

	def load(self):
		"""Load data from persistent store"""
		self.sc.add(self.direct_sources, toplevel=True)
		self.sc.add(self.other_sources, toplevel=False)
		self.source_rebase(self.sc.root)
		learn.load()

	def finish(self):
		self.sc.finish()
		learn.finish()

	def get_source(self):
		return self.source

	def get_base(self):
		"""
		Return iterable to searched base
		"""
		return ((leaf.name, leaf) for leaf in self.source.get_leaves())

	def do_search(self, source, key, score=True, context=None):
		self.search_handle = -1
		sources = [ source ]
		if key:
			sources.extend(self.text_sources)
		SearchTask(self, sources, key, "search-result", score=score,
				context=context)

	def search(self, key=u"", context=None):
		"""Search: Register the search method in the event loop

		Will search the base using @key, promising to return
		@context in the notification about the result

		If we already have a call to search, we remove the "source"
		so that we always use the most recently requested search."""

		self.latest_item_key = key
		if self.search_handle > 0:
			gobject.source_remove(self.search_handle)
		# @score only with nonempty key, else alphabethic
		self.search_handle = gobject.idle_add(self.do_search, self.source,
				key, bool(key), context)

	def do_predicate_search(self, leaf, key=u"", context=None):
		actions = leaf.get_actions() if leaf else []
		sources = (actions, )
		SearchTask(self, sources, key, "predicate-result", context=context)

	def search_predicate(self, item, key=u"", context=None):
		self.do_predicate_search(item, key, context)
		self.latest_action_key = key

	def _load_source(self, src):
		"""Try to get a source from the SourceController,
		if it is already loaded we get it from there, else
		returns @src"""
		if src in self.sc:
			return self.sc[src]
		return src

	def source_rebase(self, src):
		self.source_stack = []
		self.source = self._load_source(src)
		self.refresh_data()
	
	def push_source(self, src):
		self.source_stack.append(self.source)
		self.source = self._load_source(src)
	
	def pop_source(self):
		if not len(self.source_stack):
			raise Exception
		else:
			self.source = self.source_stack.pop()
	
	def refresh_data(self):
		self.emit("new-source", self.source)
		self.latest_item_key = None
		self.latest_action_key = None
	
	def browse_up(self):
		"""Try to browse up to previous sources, from current
		source"""
		try:
			self.pop_source()
		except:
			if self.source.has_parent():
				self.source_rebase(self.source.get_parent())
		self.refresh_data()
	
	def browse_down(self, leaf):
		"""Browse into @leaf if it's possible
		and save away the previous sources in the stack"""
		if not leaf.has_content():
			return
		self.push_source(leaf.content_source())
		self.refresh_data()

	def reset(self):
		"""Pop all sources and go back to top level"""
		try:
			while True:
				self.pop_source()
		except:
			self.refresh_data()

	def _activate(self, controller, leaf, action):
		self.eval_action(leaf, action)
	
	def eval_action(self, leaf, action):
		"""
		Evaluate an @action with the given @leaf
		"""
		if not action or not leaf:
			return
		new_source = action.activate(leaf)

		# register search to learning database
		if self.latest_item_key:
			learn.record_search_hit(unicode(leaf), self.latest_item_key)
		if self.latest_action_key:
			learn.record_search_hit(unicode(action), self.latest_action_key)

		# handle actions returning "new contexts"
		if action.is_factory() and new_source:
			self.push_source(new_source)
			self.refresh_data()
		else:
			self.emit("launched-action", leaf, action)

gobject.type_register(DataController)
gobject.signal_new("search-result", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))
gobject.signal_new("predicate-result", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT ))
gobject.signal_new("new-source", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))
gobject.signal_new("launched-action", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))

# Create singleton object shadowing main class!
DataController = DataController()
