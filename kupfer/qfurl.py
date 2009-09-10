from urlparse import urlparse, urlunparse

from kupfer import pretty

QFURL_SCHEME = "qpfer"

class QfurlError (Exception):
	pass

class qfurl (object):
	"""A qfurl is a URI to locate unique objects in kupfer's catalog.

	The qfurl is built up as follows:
	``qpfer://mother/qfid#module_and_type_hint``

	The mother part is a mother source identifier and is optional.
	The module_and_type_hint is optional.

	A short url looks like the following:
	``qpfer:identifier``

	This class provides methods to get the qfurl for an object,
	and resolve the object in a catalog.
	"""

	def __init__(self, obj=None, url=None):
		"""Create a new qfurl for object @obj"""
		if obj:
			typname = "%s.%s" % (type(obj).__module__, type(obj).__name__)
			try:
				qfid = obj.qf_id
			except AttributeError, err:
				raise QfurlError("%s has no qfurl" % obj)
			self.url = urlunparse((QFURL_SCHEME, "", qfid, "", "", typname))
		else:
			self.url = url

	def __str__(self):
		return self.url

	def __hash__(self):
		return hash(self.url)

	def __eq__(self, other):
		return self.reduce_url(self.url) == self.reduce_url(other.url)

	@classmethod
	def reduce_url(cls, url):
		split = url.rsplit("#", 1)
		if len(split) == 2:
			qfid, typname = split
			return qfid
		else:
			return url

	@classmethod
	def _parts_mother_id_typename(cls, url):
		scheme, mother, qfid, ignored, ignored2, typname = urlparse(url)
		if "#" in qfid:
			qfid, typname = qfid.rsplit("#", 1)
		else:
			typname = None
		if scheme != QFURL_SCHEME:
			raise QfurlError("Wrong scheme: %s" % scheme)
		return mother, qfid, typname

	def resolve_in_catalog(self, catalog):
		"""Resolve self in a catalog of sources"""
		mother, qfid, typname = self._parts_mother_id_typename(self.url)
		module, name = typname.rsplit(".", 1) if typname else (None, None)
		matches = []
		for src in catalog:
			if name:
				if name not in (t.__name__
						for pt in src.provides()
						for t in pt.__subclasses__()):
					continue
			for obj in src.get_leaves():
				if not hasattr(obj, "qf_id"):
					continue
				try:
					if self == qfurl(obj):
						matches.append(obj)
				except QfurlError:
					pass
		pretty.print_debug(__name__, "Found matches:", matches)
		pretty.print_debug(__name__, "For", self)
		return matches[0] if matches else None
