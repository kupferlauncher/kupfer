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
from . import scheduler

# "Enums"
# Which pane
SourcePane, ActionPane, ObjectPane = (1,2,3)

# In two-pane or three-pane mode
SourceActionMode, SourceActionObjectMode = (1,2)


class SearchTask (pretty.OutputMixin):
	"""
	"""

	def __init__(self):
		self._source_cache = {}
		self._old_key = None

	def __call__(self, sender, pane, sources, key, signal, score=True,
			item=None, context=None):
		"""
		@sources is a dict listing the inputs and how they are ranked

		if @score, sort by score, else no sort
		if @item, check against it's (Action) object requriements
		and sort by it
		"""
		if not self._old_key or not key.startswith(self._old_key):
			self._source_cache.clear()
			self._old_key = ""
		self._old_key = key

		match_iters = []
		for src in sources:
			items = ()
			fixedrank = 0
			if isinstance(src, objects.Source):
				try:
					# rankables stored
					items = (r.object for r in self._source_cache[src])
				except KeyError:
					items = src.get_leaves()
					self.output_debug("Rereading items from", src)
			elif isinstance(src, objects.TextSource):
				# For text source, we pass a unicode string here
				items = src.get_items(key)
				fixedrank = src.get_rank()
			else:
				items = src

			# Check against secondary object action reqs
			if item:
				new_items = []
				types = tuple(item.object_types())
				for i in items:
					if isinstance(i, types) and item.valid_object(i):
						new_items.append(i)
				items = new_items

			if score:
				rankables = search.make_rankables(items)
			else:
				rankables = search.make_nosortrankables(items)

			if fixedrank:
				# we have a given rank
				matches = search.add_rank_objects(rankables, fixedrank)
			elif score:
				if key:
					rankables = search.score_objects(rankables, key)
				matches = search.bonus_objects(rankables, key)
				if isinstance(src, objects.Source):
					# we fork off a copy of the iterator
					matches, self._source_cache[src] = itertools.tee(matches)
			else:
				# we only want to list them
				matches = rankables

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

		matches = list(as_set_iter(itertools.chain(*match_iters)))
		matches.sort()

		if len(matches):
			match = matches[0]
		else:
			match = None
		gobject.idle_add(sender.emit, signal, pane, match, iter(matches), context)

class RescanThread (threading.Thread, pretty.OutputMixin):
	def __init__(self, source, sender, signal, context=None, **kwargs):
		super(RescanThread, self).__init__(**kwargs)
		self.source = source
		self.sender = sender
		self.signal = signal
		self.context = context

	def run(self):
		self.output_debug(repr(self.source))
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
	"""
	Singleton that should be accessed with
	GetSourcePickleService()
	"""
	pickle_version = 2
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
			self.output_debug("Reading %s from %s" % (source, pickle_file))
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
		self.output_debug("Saving %s to %s" % (source, pickle_file))
		output.write(pickle.dumps(source, pickle.HIGHEST_PROTOCOL))
		output.close()
		return True

_source_pickle_service = None
def GetSourcePickleService():
	global _source_pickle_service
	if _source_pickle_service is None:
		_source_pickle_service = SourcePickleService()
	return _source_pickle_service

class SourceController (pretty.OutputMixin):
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
		for s in self.sources:
			provides = list(s.provides())
			if not provides:
				self.output_debug("Adding source", s, "it provides ANYTHING")
				firstlevel.add(s)
			for t in provides:
				if issubclass(t, types):
					firstlevel.add(s)
					self.output_debug("Adding source", s, "for types", *types)
					break
		return objects.MultiSource(firstlevel)

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
				news = GetSourcePickleService().unpickle_source(source)
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
			GetSourcePickleService().pickle_source(source)

_source_controller = None
def GetSourceController():
	global _source_controller
	if _source_controller is None:
		_source_controller = SourceController()
	return _source_controller

class Pane (gobject.GObject):
	__gtype_name__ = "Pane"
	def __init__(self, which_pane):
		super(Pane, self).__init__()
		self.selection = None
		self.pane = which_pane

	def select(self, item):
		self.selection = item
	def get_selection(self):
		return self.selection
	def reset(self):
		self.selection = None

class LeafPane (Pane, pretty.OutputMixin):
	__gtype_name__ = "LeafPane"

	def __init__(self, which_pane):
		super(LeafPane, self).__init__(which_pane)
		self.source_stack = []
		self.source = None
		self.search_handle = -1
		self.source_search_task = SearchTask()

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

	def browse_down(self, alternate=False):
		"""Browse into @leaf if it's possible
		and save away the previous sources in the stack
		if @alternate, use the Source's alternate method"""
		leaf = self.get_selection()
		if not leaf or not leaf.has_content():
			return
		self.push_source(leaf.content_source(alternate=alternate))

	def reset(self):
		"""Pop all sources and go back to top level"""
		Pane.reset(self)
		while self.pop_source():
			pass
		self.refresh_data()

	def search(self, sender, key, score=True, item=None, context=None):
		"""
		filter for action @item
		"""
		self.search_handle = -1
		sources = [ self.get_source() ]
		if key and self.is_at_source_root():
			# Only use text sources when we are at root catalog
			sources.extend(self.text_sources)
		self.source_search_task(sender, self.pane, sources, key,
				"search-result",
				item=item,
				score=score,
				context=context)

gobject.signal_new("new-source", LeafPane, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

class DataController (gobject.GObject, pretty.OutputMixin):
	"""
	Sources <-> Actions controller

	This is a singleton, and should
	be inited using set_sources

	The data controller must be created before main program commences,
	so it can register itself at the scheduler correctly.
	"""
	__gtype_name__ = "DataController"

	def __call__(self):
		return self

	def __init__(self):
		super(DataController, self).__init__()
		self.search_handle = -1

		self.latest_item_key = None
		self.latest_action_key = None
		self.latest_object_key = None
		self.text_sources = []
		self.decorate_types = {}
		self.source_pane = LeafPane(SourcePane)
		self.object_pane = LeafPane(ObjectPane)
		self.source_pane.connect("new-source", self._new_source)
		self.object_pane.connect("new-source", self._new_source)
		self.action_pane = Pane(ActionPane)
		self._panectl_table = {
			SourcePane : self.source_pane,
			ActionPane : self.action_pane,
			ObjectPane : self.object_pane,
			}
		self.mode = None

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

	def _load(self, sched):
		"""Load data from persistent store"""
		sc = GetSourceController()
		sc.add(self.direct_sources, toplevel=True)
		sc.add(self.other_sources, toplevel=False)
		self.source_pane.source_rebase(sc.root)
		learn.load()

	def _finish(self, sched):
		GetSourceController().finish()
		learn.finish()

	def _new_source(self, ctr, src):
		if ctr is self.source_pane:
			pane = SourcePane
		elif ctr is self.object_pane:
			pane = ObjectPane
		self.emit("source-changed", pane, src)
		print "Source changed", pane, src

	def reset(self):
		self.source_pane.reset()
		self.action_pane.reset()

	def cancel_search(self):
		"""Cancel any outstanding search"""
		if self.search_handle > 0:
			gobject.source_remove(self.search_handle)
		self.search_handle = -1

	def search(self, pane, key=u"", context=None):
		"""Search: Register the search method in the event loop

		Will search in @pane's base using @key, promising to return
		@context in the notification about the result, having selected
		@item in SourcePane

		If we already have a call to search, we remove the "source"
		so that we always use the most recently requested search."""

		self.source_pane.text_sources = self.text_sources
		if pane is SourcePane:
			self.latest_item_key = key
			item = None
			# @score only with nonempty key, else alphabethic
			self.search_handle = gobject.idle_add(self.source_pane.search,
					self,
					key, bool(key), item, context)
		elif pane is ActionPane:
			self.latest_action_key = key
			item = self.source_pane.get_selection()
			self.do_predicate_search(item, key, context)
		elif pane is ObjectPane:
			self.latest_object_key = key
			# @score only with nonempty key, else alphabethic
			asel = self.action_pane.get_selection()
			self.object_pane.text_sources = self.text_sources
			# Always score
			self.search_handle = gobject.idle_add(self.object_pane.search,
					self,
					key, True, asel, context)

	def do_predicate_search(self, leaf, key=u"", context=None):
		actions = list(leaf.get_actions()) if leaf else []
		if leaf and type(leaf) in self.decorate_types:
			# FIXME: We ignore subclasses for now ("in" above)
			actions.extend(self.decorate_types[type(leaf)])

		sources = (actions, )
		stask = SearchTask()
		stask(self, ActionPane, sources, key, "search-result", context=context)

	def select(self, pane, item):
		"""Select @item in @pane to self-update
		relevant places"""
		# If already selected, do nothing
		panectl = self._panectl_table[pane]
		if item is panectl.get_selection():
			return
		print "Selecting", item, "in", pane
		panectl.select(item)
		if pane is SourcePane:
			assert not item or isinstance(item, objects.Leaf), "Selection in Source pane is not a Leaf!"
			# populate actions
			self.search(ActionPane)
		elif pane is ActionPane:
			assert not item or isinstance(item, objects.Action), "Selection in Source pane is not an Action!"
			if item and item.requires_object():
				newmode = SourceActionObjectMode
			else:
				newmode = SourceActionMode
			if newmode is not self.mode:
				self.mode = newmode
				self.emit("mode-changed", self.mode, item)
			if self.mode is SourceActionObjectMode:
				# populate third pane
				sc = GetSourceController()
				self.object_pane.source_rebase(sc.root_for_types(item.object_types()))
				self.search(ObjectPane)
		elif pane is ObjectPane:
			assert not item or isinstance(item, objects.Leaf), "Selection in Object pane is not a Leaf!"

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
				self.emit("pane-reset", paneenum, sel)
				self.select(paneenum, None)

	def browse_up(self, pane):
		"""Try to browse up to previous sources, from current
		source"""
		if pane is SourcePane:
			self.source_pane.browse_up()
		if pane is ObjectPane:
			self.object_pane.browse_up()
	
	def browse_down(self, pane, alternate=False):
		"""Browse into @leaf if it's possible
		and save away the previous sources in the stack
		if @alternate, use the Source's alternate method"""
		if pane is SourcePane:
			self.source_pane.browse_down(alternate=alternate)
		if pane is ObjectPane:
			self.object_pane.browse_down(alternate=alternate)

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
			new_source = action.activate(leaf)
		elif self.mode is SourceActionObjectMode:
			new_source = action.activate(leaf, sobject)

		# register search to learning database
		learn.record_search_hit(unicode(leaf), self.latest_item_key)
		learn.record_search_hit(unicode(action), self.latest_action_key)
		if sobject:
			learn.record_search_hit(unicode(sobject), self.latest_object_key)

		# handle actions returning "new contexts"
		if action.is_factory() and new_source:
			self.source_pane.push_source(new_source)
		else:
			self.emit("launched-action", SourceActionMode, leaf, action)

gobject.type_register(DataController)

# pane cleared (invalid item) item was invalid
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

# Create singleton object shadowing main class!
DataController = DataController()

