import gobject
import pickle

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

class PeriodicRescanner (gobject.GObject):
	def __init__(self, catalog, period=10, startup=10):
		super(PeriodicRescanner, self).__init__()
		self.catalog = catalog
		self.period = period
		print self.catalog
		self.cur = iter(catalog)
		gobject.timeout_add_seconds(startup, self._startup)

	def _startup(self):
		gobject.timeout_add_seconds(self.period, self._periodic_rescan_helper)

	def _periodic_rescan_helper(self):
		try:
			next = self.cur.next()
		except StopIteration:
			self.cur = iter(self.catalog)
			return True
		gobject.idle_add(self.reload_source, next)
		return True

	def reload_source(self, source):
		"""Reload source"""
		if not source.is_dynamic():
			source.get_leaves(force_update=True)


class DataController (gobject.GObject):
	"""
	Sources <-> Actions controller

	This is a singleton, and should
	be inited using set_source
	"""
	__gtype_name__ = "DataController"

	pickle_file = "pickles.gz"
	pickle_version = 1

	def __call__(self):
		return self

	def __init__(self):
		super(DataController, self).__init__()
		self.source = None
		self.sources = None
		self.search_closure = None
		self.is_searching = False
		self.rescanner = None

	def set_sources(self, S_sources, s_sources):
		"""Init the DataController with the given list of sources

		@S_sources are to be included directly in the catalog,
		@s_souces as subitems
		"""
		self.sources = S_sources, s_sources

		if s_sources:
			S_sources.append(objects.SourcesSource(s_sources))
	
		if len(S_sources) == 1:
			root_catalog, = S_sources
		elif len(S_sources) > 1:
			root_catalog = objects.MultiSource(S_sources)
		print self.sources
		self.source_rebase(root_catalog)

	def load(self):
		"""
		Tell the DataController to "preload" its source
		asynchronously, either in a thread or in the main loop
		"""
		all_sources = []
		S, s = self.sources
		all_sources.extend(S)
		all_sources.extend(s)
		self.rescanner = PeriodicRescanner(all_sources, period=2, startup=0)

	def _unpickle_source(self, pickle_file):
		from gzip import GzipFile as file
		try:
			pfile = file(pickle_file, "rb")
		except IOError:
			return None
		print "Reading from", pfile
		unpickler = pickle.Unpickler(pfile)
		version = unpickler.load()
		print version
		source = unpickler.load()
		print source
		return source
	
	def _pickle_source(self, pickle_file, source):
		"""Before exit"""
		from gzip import GzipFile as file
		output = file(pickle_file, "wb")
		print "Pickling to", output
		pickler = pickle.Pickler(output, pickle.HIGHEST_PROTOCOL)
		pickler.dump(self.pickle_version)
		pickler.dump(source)
		output.close()
		return True

	def finish(self):
		pass

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
