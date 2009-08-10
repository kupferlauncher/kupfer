import itertools
import os
import cPickle as pickle
import threading
import time

import gobject
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
			item=None, action=None, context=None):
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

		# Set up object and type checking for
		# action + secondary object
		item_check = lambda x: x
		if item and action:
			types = tuple(action.object_types())
			def type_obj_check(itms):
				for i in itms:
					if (isinstance(i, types) and
							action.valid_object(i, for_item=item)):
						yield i
			def type_check(itms):
				for i in itms:
					if isinstance(i, types):
						yield i

			if hasattr(action, "valid_object"):
				item_check = type_obj_check
			else:
				item_check = type_check

		match_iters = []
		for src in sources:
			items = ()
			fixedrank = 0
			if isinstance(src, objects.Source):
				try:
					# rankables stored
					items = (r.object for r in self._source_cache[src])
				except KeyError:
					# check uncached items
					items = item_check(src.get_leaves())
			elif isinstance(src, objects.TextSource):
				# For text source, we pass a unicode string here
				items = item_check(src.get_items(key))
				fixedrank = src.get_rank()
			else:
				items = item_check(src)

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

		# Check if the items are valid as the search
		# results are accessed
		def valid_check(seq):
			for itm in seq:
				obj = itm.object
				if (not hasattr(obj, "is_valid")) or obj.is_valid():
					yield itm
		def first(seq):
			"""Return first item in @seq or None"""
			for itm in seq:
				return itm
			return None
		match = first(valid_check(matches))
		match_iter = valid_check(matches)
		gobject.idle_add(sender.emit, signal, pane, match, match_iter, context)

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
		# Source -> time mapping
		self.latest_rescan_time = {}
		self._min_rescan_interval = campaign/10

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
		# Advance until we find a source that was not recently rescanned
		for next in self.cur:
			oldtime = self.latest_rescan_time.get(next, 0)
			if (time.time() - oldtime) > self._min_rescan_interval:
				break
		else:
			# else <=> break not reached in loop
			self.output_info("Campaign finished, pausing %d s" % self.campaign)
			self.cur_event = gobject.timeout_add_seconds(self.campaign,
					self._new_campaign)
			return False
		self.cur_event = gobject.idle_add(self.reload_source, next)
		return True

	def register_rescan(self, source, force=False):
		"""Register an object for rescan
		dynamic sources will only be rescanned if @force is True
		"""
		gobject.idle_add(self.reload_source, source, force)

	def reload_source(self, source, force=False):
		self.latest_rescan_time[source] = time.time()
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
		# Check if there are old cache files
		self._rm_old_cachefiles()

	def _rm_old_cachefiles(self):
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
				assert "kupfer" in os.path.basename(fpath)
				os.unlink(fpath)

	def get_filename(self, source):
		from os import path

		hashstr = "%010d" % abs(hash(source))
		filename = self.name_template % (hashstr, self.pickle_version)
		return path.join(config.get_cache_home(), filename)

	def unpickle_source(self, source):
		cached = self._unpickle_source(self.get_filename(source))
		if not cached:
			return None

		# check consistency
		if (type(source) == type(cached) and
			(hasattr(source, "version") == hasattr(cached, "version") and
			source.version == cached.version)):
			return cached
		else:
			self.output_debug("Source version changed to %s %s" %
					(source, source.version))
		return None
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
		self.text_sources = set()
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
	def add_text_sources(self, srcs):
		self.text_sources.update(srcs)
	def get_text_sources(self):
		return self.text_sources
	def set_content_decorators(self, decos):
		self.content_decorators = decos
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

	def get_content_for_leaf(self, leaf):
		for typ in self.content_decorators:
			if isinstance(leaf, typ):
				for content in self.content_decorators[typ]:
					if content.decorates_item(leaf):
						return content(leaf)
		return None

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
		self.latest_key = None

	def select(self, item):
		self.selection = item
	def get_selection(self):
		return self.selection
	def reset(self):
		self.selection = None
	def get_latest_key(self):
		return self.latest_key

class LeafPane (Pane, pretty.OutputMixin):
	__gtype_name__ = "LeafPane"

	def __init__(self, which_pane):
		super(LeafPane, self).__init__(which_pane)
		self.source_stack = []
		self.source = None
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
		if not leaf:
			return
		if leaf.has_content():
			self.push_source(leaf.content_source(alternate=alternate))
			return
		sc = GetSourceController()
		content = sc.get_content_for_leaf(leaf)
		if content:
			self.push_source(content)

	def reset(self):
		"""Pop all sources and go back to top level"""
		Pane.reset(self)
		while self.pop_source():
			pass
		self.refresh_data()

	def search(self, sender, key=u"", context=None):
		"""
		filter for action @item
		"""
		self.latest_key = key
		sources = [ self.get_source() ]
		if key and self.is_at_source_root():
			# Only use text sources when we are at root catalog
			sc = GetSourceController()
			textsrcs = sc.get_text_sources()
			sources.extend(textsrcs)
		self.source_search_task(sender, self.pane, sources, key,
				"search-result",
				score=bool(key),
				context=context)
gobject.signal_new("new-source", LeafPane, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

class PrimaryActionPane (Pane):
	def set_item(self, item):
		"""Set which @item we are currently listing actions for"""
		self.current_item = item

	def search(self, sender, key=u"", context=None):
		"""Search: Register the search method in the event loop

		using @key, promising to return
		@context in the notification about the result, having selected
		@item in SourcePane

		If we already have a call to search, we remove the "source"
		so that we always use the most recently requested search."""

		self.latest_key = key
		leaf = self.current_item
		actions = list(leaf.get_actions()) if leaf else []
		if leaf and type(leaf) in self.decorate_types:
			# FIXME: We ignore subclasses for now ("in" above)
			actions.extend(self.decorate_types[type(leaf)])

		actions = [a for a in actions if a.valid_for_item(self.current_item)]
		sources = (actions, )
		stask = SearchTask()
		stask(sender, ActionPane, sources, key, "search-result", context=context)

class SecondaryObjectPane (LeafPane):
	__gtype_name__ = "SecondaryObjectPane"
	def __init__(self, pane):
		LeafPane.__init__(self, pane)
		self.current_item = None
		self.current_action = None
	def reset(self):
		self.source = None
		self.source_stack = None
		LeafPane.reset(self)
		self.source_search_task = SearchTask()
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
	def search(self, sender, key=u"", context=None):
		"""
		filter for action @item
		"""
		self.latest_key = key
		sources = [ self.get_source() ]
		if key and self.is_at_source_root():
			# Only use text sources when we are at root catalog
			sc = GetSourceController()
			textsrcs = sc.get_text_sources()
			sources.extend(textsrcs)
		self.source_search_task(sender, self.pane, sources, key,
				"search-result",
				item=self.current_item,
				action=self.current_action,
				score=True,
				context=context)

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

		self.decorate_types = {}
		self.source_pane = LeafPane(SourcePane)
		self.object_pane = SecondaryObjectPane(ObjectPane)
		self.source_pane.connect("new-source", self._new_source)
		self.object_pane.connect("new-source", self._new_source)
		self.action_pane = PrimaryActionPane(ActionPane)
		self.action_pane.decorate_types = self.decorate_types
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
		sc = GetSourceController()
		sc.add_text_sources(srcs)
	
	def register_action_decorators(self, acts):
		# Keep a dictionary with Leaf type as key
		for act in acts:
			applies = act.item_types()
			for appl_type in applies:
				decorate_with = self.decorate_types.get(appl_type, [])
				decorate_with.append(act)
				self.decorate_types[appl_type] = decorate_with
		self.output_debug("Decorators", self.decorate_types)

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
		self.output_debug("Content decorators", decorate_item_types)

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

	def reset(self):
		self.source_pane.reset()
		self.action_pane.reset()

	def cancel_search(self):
		"""Cancel any outstanding search"""
		if self.search_handle > 0:
			gobject.source_remove(self.search_handle)
		self.search_handle = -1

	def search(self, pane, key=u"", context=None, direct=True):
		"""Search: Register the search method in the event loop

		Will search in @pane's base using @key, promising to return
		@context in the notification about the result, having selected
		@item in SourcePane

		If we already have a call to search, we remove the "source"
		so that we always use the most recently requested search."""

		ctl = self._panectl_table[pane]
		if direct:
			ctl.search(self,key, context)
		else:
			self.search_handle = gobject.idle_add(ctl.search,self,key,context)

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
			assert not item or isinstance(item, objects.Leaf), "Selection in Source pane is not a Leaf!"
			# populate actions
			self.action_pane.set_item(item)
			self.search(ActionPane, direct=True)
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
				self.object_pane.set_item_and_action(self.source_pane.get_selection(), item)
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
		learn.record_search_hit(leaf, self.source_pane.get_latest_key())
		learn.record_search_hit(action, self.action_pane.get_latest_key())
		if sobject:
			learn.record_search_hit(sobject, self.object_pane.get_latest_key())

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

