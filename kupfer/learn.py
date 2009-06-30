import cPickle as pickle

from . import pretty
from . import config

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
	def get_count(self):
		return self.count
	def get_mnemonics(self):
		return self.mnemonics

class Learning (pretty.OutputMixin, object):
	def _unpickle_register(self, pickle_file):
		try:
			pfile = open(pickle_file, "rb")
		except IOError, e:
			return None
		try:
			source = pickle.loads(pfile.read())
			assert isinstance(source, dict), "Stored object not a dict"
			self.output_info("Reading from %s" % (pickle_file, ))
		except (pickle.PickleError, Exception), e:
			source = None
			self.output_debug("Error loading %s: %s" % (pickle_file, e))
		return source

	def _pickle_register(self, reg, pickle_file):
		output = open(pickle_file, "wb")
		self.output_info("Saving to %s" % (pickle_file, ))
		output.write(pickle.dumps(reg, pickle.HIGHEST_PROTOCOL))
		output.close()
		return True

Learning = Learning()
_register = {}

def record_search_hit(name, key=u""):
	"""
	Record that item @name was used, with the optional
	search term @key recording
	"""
	if name not in _register:
		_register[name] = Mnemonics()
	_register[name].increment(key)

def get_record_score(name, key=u""):
	"""
	Get total score for item @name,
	bonus score is given for @key matches
	"""
	if name not in _register:
		return 0
	mns = _register[name]
	if not key:
		cnt = mns.get_count()
		return 50 * (1 - 1.0/(cnt + 1))

	stats = mns.get_mnemonics()
	closescr = sum(stats[m] for m in stats if m.startswith(key))
	mnscore = 30 * (1 - 1.0/(closescr + 1))
	exact = stats.get(key, 0)
	mnscore += 50 * (1 - 1.0/(exact + 1))
	return mnscore

def load():
	"""
	Load learning database
	"""
	global _register

	filepath = config.get_data_file(mnemonics_filename)

	if filepath:
		_register = Learning._unpickle_register(filepath)
	if not _register:
		_register = {}

def finish():
	"""
	Close and save the learning record
	"""
	filepath = config.save_data_file(mnemonics_filename)
	Learning._pickle_register(_register, filepath)
