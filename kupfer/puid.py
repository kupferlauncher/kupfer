"""
Persistent Globally Unique Indentifiers for KupferObjects.
"""

try:
	import cPickle as pickle
except ImportError:
	import pickle

from kupfer import data
from kupfer import pretty
from kupfer import qfurl

SERIALIZABLE_ATTRIBUTE = "serilizable"

class SerializedObject (object):
	def __init__(self, obj):
		self.data = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)
	def __eq__(self, other):
		return isinstance(other, type(self)) and self.data == other.data
	def reconstruct(self):
		return pickle.loads(self.data)

def get_unique_id(obj):
	if obj is None:
		return None
	if hasattr(obj, "qf_id"):
		return str(qfurl.qfurl(obj))
	if hasattr(obj, SERIALIZABLE_ATTRIBUTE):
		return SerializedObject(obj)
	return repr(obj)

def is_reference(puid):
	"Return True if @puid is a reference-type ID"
	return not isinstance(puid, SerializedObject)

def _find_obj_in_catalog(puid, catalog, excluding=None):
	if puid.startswith(qfurl.QFURL_SCHEME):
		qfu = qfurl.qfurl(url=puid)
		return qfu.resolve_in_catalog(catalog)
	for src in catalog:
		if excluding is not None and src == excluding:
			continue
		for obj in src.get_leaves():
			if repr(obj) == puid:
				return obj
	return None

def resolve_unique_id(puid, excluding=None):
	"""
	Resolve unique id @puid inside @catalog
	"""
	if puid is None:
		return None
	if isinstance(puid, SerializedObject):
		try:
			return puid.reconstruct()
		except Exception, exc:
			pretty.print_debug(__name__, type(exc).__name__, exc)
			return None
	sc = data.GetSourceController()
	obj = _find_obj_in_catalog(puid, sc._pre_root, excluding=excluding)
	if obj is not None:
		pretty.print_debug(__name__, "Resolving %s to %s" % (puid, obj))
		return obj
	other_sources = set(sc.sources) - set(sc._pre_root)
	obj = _find_obj_in_catalog(puid, other_sources, excluding=excluding)
	pretty.print_debug(__name__, "Resolving %s to %s" % (puid, obj))
	return obj

