import gobject
import threading
import pickle

gobject.threads_init()

from . import kupfer
from . import objects

def SearchTask(sender, rankables, key, signal, context=None):
	sobj = kupfer.Search(rankables)
	matches = sobj.search_objects(key)

	if len(matches):
		match = matches[0]
	else:
		match = None
	gobject.idle_add(sender.emit, signal, match, iter(matches), context)

class OutputMixin (object):
	def output_info(self, *items, **kwargs):
		"""
		Output given items using @sep as separator,
		ending the line with @end
		"""
		sep = kwargs.get("sep", " ")
		end = kwargs.get("end", "\n")
		stritems = (str(it) for it in items)
		try:
			output = "[%s] %s: %s%s" % (type(self).__module__,
					type(self).__name__, sep.join(stritems), end)
		except Exception:
			output = sep.join(stritems) + end
		print output,

	def output_debug(self, *items, **kwargs):
		self.output_info(*items, **kwargs)

class RescanThread (threading.Thread, OutputMixin):
	def __init__(self, source, sender, signal, context=None, **kwargs):
		super(RescanThread, self).__init__(**kwargs)
		self.source = source
		self.sender = sender
		self.signal = signal
		self.context = context

	def start(self):
		self.output_info("Rescanning", self.source)
		items = self.source.get_leaves(force_update=True)
		if self.sender and self.signal:
			gobject.idle_add(self.sender.emit, self.signal, self.context)

class PeriodicRescanner (gobject.GObject, OutputMixin):
	"""
	Periodically rescan a @catalog of sources

	Do first rescan after @startup seconds, then
	followup with rescans in @period.

	Each campaign of rescans is separarated by @campaign
	seconds
	"""
	def __init__(self, catalog, period=5, startup=10, campaign=3600):
		super(PeriodicRescanner, self).__init__()
		self.period = period
		self.campaign=campaign
		self.set_catalog(catalog)
		gobject.timeout_add_seconds(startup, self._new_campaign)

	def set_catalog(self, catalog):
		self.catalog = catalog
		self.cur = iter(self.catalog)
	
	def _new_campaign(self):
		self.output_debug("Starting new campaign with rescans every", self.period)
		self.cur = iter(self.catalog)
		gobject.timeout_add_seconds(self.period, self._periodic_rescan_helper)

	def _periodic_rescan_helper(self):
		try:
			next = self.cur.next()
		except StopIteration:
			self.output_debug("Campaign finished, pausing", self.campaign)
			gobject.timeout_add_seconds(self.campaign, self._new_campaign)
			return False
		gobject.idle_add(self.reload_source, next)
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


class DataController (gobject.GObject, OutputMixin):
	"""
	Sources <-> Actions controller

	This is a singleton, and should
	be inited using set_source
	"""
	__gtype_name__ = "DataController"
	pickle_version = 1

	def __call__(self):
		return self

	def __init__(self):
		super(DataController, self).__init__()
		self.source = None
		self.sources = None
		self.search_closure = None
		self.is_searching = False
		self.rescanner = PeriodicRescanner([])

	def set_sources(self, S_sources, s_sources):
		"""Init the DataController with the given list of sources

		@S_sources are to be included directly in the catalog,
		@s_souces as just as subitems
		"""
		S_sources = set(S_sources)
		s_sources = set(s_sources)
		self._unpickle_or_rescan(S_sources)
		self._unpickle_or_rescan(s_sources)

		self.direct_sources = set(S_sources)
		self.sources = set(self.direct_sources)
		self.sources.update(s_sources)

		if self.sources == 1:
			root_catalog = self.sources[0]
		elif len(self.sources) > 1:
			firstlevel = set(self.direct_sources)
			sourceindex = set(self.sources)
			kupfer_sources = objects.SourcesSource(self.sources)
			sourceindex.add(kupfer_sources)
			firstlevel.add(objects.SourcesSource(sourceindex))
			root_catalog = objects.MultiSource(firstlevel)
	
		self.source_rebase(root_catalog)

		# Setup PeriodicRescanner
		self.rescanner.set_catalog(self.sources)

		print "Setting up %s with" % self
		for s in self.sources:
			print "\t%s %d" % (repr(s), id(s))

	def load(self):
		"""
		Tell the DataController to "preload" its source
		asynchronously, either in a thread or in the main loop
		"""
		#self._unpickle_or_rescan(self.sources)

	def _unpickle_or_rescan(self, sources, rescan=True):
		# immediately rescan main collection
		for source in sources:
			name = "kupfer-%s.pickle" % str(abs(hash(repr(source))))
			news = self._unpickle_source(name)
			if news:
				sources.remove(source)
				sources.add(news)
			elif rescan:
				self.rescanner.register_rescan(source, force=True)

	def _unpickle_source(self, pickle_file):
		try:
			pfile = file(pickle_file, "rb")
		except IOError, e:
			return None
		unpickler = pickle.Unpickler(pfile)
		version = unpickler.load()
		source = unpickler.load()
		# DEBUG: Mark pickle-loaded objects
		# source.name+=" +"
		self.output_info("Reading %s from %s" % (source, pickle_file))
		return source
	
	def _pickle_source(self, pickle_file, source):
		output = file(pickle_file, "wb")
		self.output_info("Saving %s to %s" % (source, pickle_file))
		pickler = pickle.Pickler(output, pickle.HIGHEST_PROTOCOL)
		pickler.dump(self.pickle_version)
		pickler.dump(source)
		output.close()
		return True

	def _pickle_sources(self, sources):
		for source in sources:
			if source.is_dynamic():
				continue
			# nice row of builtins
			name = "kupfer-%s.pickle" % str(abs(hash(repr(source))))
			self._pickle_source(name, source)

	def finish(self):
		self._pickle_sources(self.sources)

	def get_source(self):
		return self.source

	def get_base(self):
		"""
		Return iterable to searched base
		"""
		return ((leaf.value, leaf) for leaf in self.source.get_leaves())

	def do_search(self, source, key, context):
		#print "%s: Searching items for %s" % (self, key)
		rankables = ((leaf.value, leaf) for leaf in source.get_leaves())
		SearchTask(self, rankables, key, "search-result", context=context)
		self.is_searching = False

	def do_closure(self):
		"""Call self.search_closure if and then set it to None"""
		self.search_closure()
		self.search_closure = None

	def search(self, key, context=None):
		"""Search: Register the search method in the event loop

		Will search the base using @key, promising to return
		@context in the notification about the result

		If we already have a call to search, we simply update the 
		self.search_closure, so that we always use the most recently
		requested search."""

		self.search_closure = lambda : self.do_search(self.source, key, context)
		if self.is_searching:
			return
		gobject.idle_add(self.do_closure)
		self.is_searching = True

	def do_predicate_search(self, leaf, key=None, context=None):
		if leaf:
			leaves = leaf.get_actions()
		else:
			leaves = []
		if not key:
			matches = [kupfer.Rankable(leaf.name, leaf) for leaf in leaves]
			try:
				match = matches[0]
			except IndexError: match = None
			self.emit("predicate-result", match, iter(matches), context)
		else:
			leaves = [(leaf.name, leaf) for leaf in leaves]
			SearchTask(self, leaves, key, "predicate-result", context)

	def search_predicate(self, item, key=None, context=None):
		self.do_predicate_search(item, key, context)

	def source_rebase(self, src):
		self.source_stack = []
		self.source = src
		self.refresh_data()
	
	def push_source(self, src):
		self.source_stack.append(self.source)
		self.source = src
	
	def pop_source(self):
		if not len(self.source_stack):
			raise Exception
		else:
			self.source = self.source_stack.pop()
	
	def refresh_data(self):
		self.emit("new-source", self.source)
	
	def refresh_actions(self, leaf):
		"""
		Updates the Actions widget, given a selected leaf object

		leaf can be none
		"""
		if not leaf:
			sobj = None
		else:
			actions = leaf.get_actions()
			sobj = kupfer.Search(((str(act), act) for act in actions))
		self.action_search.set_search_object(sobj)

	def _cursor_changed(self, widget, leaf):
		"""
		Selected item changed in Leaves widget
		"""
		self.refresh_actions(leaf)
	
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
			print "No action", (action, leaf)
			return
		new_source = action.activate(leaf)
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
