"""
Persistent Globally Unique Indentifiers for KupferObjects.
"""

from __future__ import with_statement

import contextlib

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
		try:
			return SerializedObject(obj)
		except pickle.PicklingError, exc:
			pretty.print_error(__name__, type(exc).__name__, exc)
			return None
	return repr(obj)

def is_reference(puid):
	"Return True if @puid is a reference-type ID"
	return not isinstance(puid, SerializedObject)

# A Context manager to block recursion when seeking inside a
# catalog; we have a stack (@_excluding) of the sources we
# are visiting, and nested context with the _exclusion
# context manager

_excluding = []
@contextlib.contextmanager
def _exclusion(src):
	try:
		_excluding.append(src)
		yield
	finally:
		_excluding.pop()

def _is_currently_excluding(src):
	return src is not None and src in _excluding

def _find_obj_in_catalog(puid, catalog):
	if puid.startswith(qfurl.QFURL_SCHEME):
		qfu = qfurl.qfurl(url=puid)
		return qfu.resolve_in_catalog(catalog)
	for src in catalog:
		if _is_currently_excluding(src):
			continue
		with _exclusion(src):
			for obj in src.get_leaves():
				if repr(obj) == puid:
					return obj
	return None

def resolve_unique_id(puid, excluding=None):
	"""
	Resolve unique id @puid

	The caller (if a Source) should pass itself as @excluding,
	so that recursion into itself is avoided.
	"""
	if excluding is not None:
		with _exclusion(excluding):
			return resolve_unique_id(puid, None)

	if puid is None:
		return None
	if isinstance(puid, SerializedObject):
		try:
			return puid.reconstruct()
		except Exception, exc:
			pretty.print_debug(__name__, type(exc).__name__, exc)
			return None
	sc = data.GetSourceController()
	obj = _find_obj_in_catalog(puid, sc._pre_root)
	if obj is not None:
		pretty.print_debug(__name__, "Resolving %s to %s" % (puid, obj))
		return obj
	other_sources = set(sc.sources) - set(sc._pre_root)
	obj = _find_obj_in_catalog(puid, other_sources)
	pretty.print_debug(__name__, "Resolving %s to %s" % (puid, obj))
	return obj

