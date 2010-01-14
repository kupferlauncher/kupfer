"""
Persistent Globally Unique Indentifiers for KupferObjects.
"""

from __future__ import with_statement

import contextlib

try:
	import cPickle as pickle
except ImportError:
	import pickle

from kupfer import pretty

from kupfer import commandexec
from kupfer.core import qfurl
from kupfer.core.sources import GetSourceController

SERIALIZABLE_ATTRIBUTE = "serilizable"

class SerializedObject (object):
	# treat the serilizable attribute as a version number, defined on the class
	def __init__(self, obj):
		self.data = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)
		self.version = getattr(obj, SERIALIZABLE_ATTRIBUTE)
	def __eq__(self, other):
		return (isinstance(other, type(self)) and self.data == other.data and
		        self.version == other.version)
	def reconstruct(self):
		obj = pickle.loads(self.data)
		if self.version != getattr(obj, SERIALIZABLE_ATTRIBUTE):
			raise ValueError("Version mismatch for reconstructed %s" % obj)
		return obj

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
	sc = GetSourceController()
	obj = _find_obj_in_catalog(puid, sc._firstlevel)
	if obj is not None:
		return obj
	other_sources = set(sc.sources) - set(sc._firstlevel)
	obj = _find_obj_in_catalog(puid, other_sources)
	return obj

def resolve_action_id(puid, for_item=None):
	if puid is None:
		return None
	if isinstance(puid, SerializedObject):
		return resolve_unique_id(puid)
	get_action_id = repr
	sc = GetSourceController()
	if for_item is not None:
		for action in commandexec.actions_for_item(for_item, sc):
			if get_unique_id(action) == puid:
				return action
	for item_type, actions in sc.action_decorators.iteritems():
		for action in actions:
			if get_action_id(action) == puid:
				return action
	pretty.print_debug(__name__, "Unable to resolve %s (%s)" % (puid, for_item))
	return None
