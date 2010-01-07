import cPickle as pickle

from kupfer import pretty
from kupfer import config

mnemonics_filename = "mnemonics.pickle"

class Mnemonics (object):
	"""
	Class to describe a collection of mnemonics
	as well as the total count
	"""
	def __init__(self):
		self.mnemonics = dict()
		self.count = 0
	def __repr__(self):
		return "<%s %d %s>" % (self.__class__.__name__, self.count, "".join(["%s: %d, " % (m,c) for m,c in self.mnemonics.iteritems()]))
	def increment(self, mnemonic=None):
		if mnemonic:
			mcount = self.mnemonics.get(mnemonic, 0)
			self.mnemonics[mnemonic] = mcount + 1
		self.count += 1

	def decrement(self):
		"""Decrement total count and the least mnemonic"""
		if self.mnemonics:
			key = min(self.mnemonics, key=lambda k: self.mnemonics[k])
			if self.mnemonics[key] <= 1:
				del self.mnemonics[key]
			else:
				self.mnemonics[key] -= 1
		self.count = max(self.count -1, 0)

	def __nonzero__(self):
		return self.count
	def get_count(self):
		return self.count
	def get_mnemonics(self):
		return self.mnemonics

class Learning (object):
	@classmethod
	def _unpickle_register(cls, pickle_file):
		try:
			pfile = open(pickle_file, "rb")
		except IOError, e:
			return None
		try:
			source = pickle.loads(pfile.read())
			assert isinstance(source, dict), "Stored object not a dict"
			pretty.print_debug(__name__, "Reading from %s" % (pickle_file, ))
		except (pickle.PickleError, Exception), e:
			source = None
			pretty.print_error(__name__, "Error loading %s: %s" % (pickle_file, e))
		return source

	@classmethod
	def _pickle_register(self, reg, pickle_file):
		output = open(pickle_file, "wb")
		pretty.print_debug(__name__, "Saving to %s" % (pickle_file, ))
		output.write(pickle.dumps(reg, pickle.HIGHEST_PROTOCOL))
		output.close()
		return True

_register = {}
_favorites = set()

def record_search_hit(obj, key=u""):
	"""
	Record that KupferObject @obj was used, with the optional
	search term @key recording
	"""
	name = repr(obj)
	if name not in _register:
		_register[name] = Mnemonics()
	_register[name].increment(key)

def get_record_score(obj, key=u""):
	"""
	Get total score for KupferObject @obj,
	bonus score is given for @key matches
	"""
	name = repr(obj)
	fav = 20 * (name in _favorites)
	if name not in _register:
		return fav
	mns = _register[name]
	if not key:
		cnt = mns.get_count()
		return fav + 50 * (1 - 1.0/(cnt + 1))

	stats = mns.get_mnemonics()
	closescr = sum(stats[m] for m in stats if m.startswith(key))
	mnscore = 30 * (1 - 1.0/(closescr + 1))
	exact = stats.get(key, 0)
	mnscore += 50 * (1 - 1.0/(exact + 1))
	return fav + mnscore

def _prune_register():
	"""
	Remove items with chance (len/25000)

	Assuming homogenous records (all with score one) we keep:
	x_n+1 := x_n * (1 - chance)

	To this we have to add the expected number of added mnemonics per
	invocation, est. 10, and we can estimate a target number of saved mnemonics.
	"""
	import random
	random.seed()
	rand = random.random

	goalitems = 500
	flux = 10.0
	alpha = flux/goalitems**2

	chance = min(0.1, len(_register)*alpha)
	for leaf, mn in _register.items():
		if rand() > chance:
			continue
		mn.decrement()
		if not mn:
			del _register[leaf]

	l = len(_register)
	pretty.print_debug(__name__, "Pruned register (%d mnemonics)" % l)

def load():
	"""
	Load learning database
	"""
	global _register

	try:
		filepath = config.get_config_file(mnemonics_filename) or \
				config.get_data_file(mnemonics_filename)
	except config.ResourceLookupError, exc:
		pretty.print_debug(__name__, exc)
		return

	if filepath:
		_register = Learning._unpickle_register(filepath)
	if not _register:
		_register = {}

def finish():
	"""
	Close and save the learning record
	"""
	if not _register:
		pretty.print_debug(__name__, "Not writing empty register")
		return
	if len(_register) > 100:
		_prune_register()
	filepath = config.save_config_file(mnemonics_filename)
	Learning._pickle_register(_register, filepath)

def add_favorite(obj):
	_favorites.add(repr(obj))

def remove_favorite(obj):
	_favorites.discard(repr(obj))

def is_favorite(obj):
	return repr(obj) in _favorites
