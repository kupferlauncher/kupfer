from kupfer import datatools
from kupfer import icons
from kupfer import pretty
from kupfer.utils import locale_sort
from kupfer.kupferstring import tounicode, toutf8, tofolded

__all__ = [
	"InvalidDataError", "KupferObject", "Leaf", "Action", "Source", "TextSource"
]

class Error (Exception):
	pass

class InvalidDataError (Error):
	"""The data is wrong for the given Leaf"""
	pass

class InvalidLeafError (Error):
	"""The Leaf passed to an Action is invalid"""
	pass

_builtin_modules = frozenset([
	"kupfer.obj.objects",
	"kupfer.obj.base",
	"kupfer.obj.sources",
	"kupfer.obj.fileactions",
])

class _BuiltinObject (type):
	def __new__(mcls, name, bases, dict):
		dict["_is_builtin"] = dict["__module__"] in _builtin_modules
		return type.__new__(mcls, name, bases, dict)


class KupferObject (object):
	"""
	Base class for kupfer data model

	This class provides a way to get at an object's:

	* icon with get_thumbnail, get_pixbuf and get_icon
	* name with unicode() or str()
	* description with get_description

	@rank_adjust should be used _very_ sparingly:
		Default actions should have +5 or +1
		Destructive (dangerous) actions should have -5 or -10
	"""
	__metaclass__ = _BuiltinObject
	rank_adjust = 0
	def __init__(self, name=None):
		""" Init kupfer object with, where
		@name *should* be a unicode object but *may* be
		a UTF-8 encoded `str`
		"""
		if not name:
			name = self.__class__.__name__
		self.name = tounicode(name)
		folded_name = tofolded(self.name)
		self.name_aliases = set()
		if folded_name != self.name:
			self.name_aliases.add(folded_name)

	def __str__(self):
		return toutf8(self.name)

	def __unicode__(self):
		"""Return a `unicode` representation of @self """
		return self.name

	def __repr__(self):
		key = self.repr_key()
		if self._is_builtin:
			return "".join(("<builtin.", self.__class__.__name__,
				((" %s" % (key,)) if key else ""), ">"))
		return "".join(("<", self.__module__, ".", self.__class__.__name__,
			((" %s" % (key,)) if key else ""), ">"))

	def repr_key(self):
		"""
		Return an object whose str() will be used in the __repr__,
		self is returned by default.
		This value is used to recognize objects, for example learning commonly
		used objects.
		"""
		return self

	def get_description(self):
		"""Return a description of the specific item
		which *should* be a unicode object
		"""
		return None

	def get_thumbnail(self, width, height):
		"""Return pixbuf of size @width x @height if available
		Most objects will not implement this
		"""
		return None

	def get_pixbuf(self, icon_size):
		"""
		Returns an icon in pixbuf format with dimension @icon_size

		Subclasses should implement: get_gicon and get_icon_name,
		if they make sense.
		The methods are tried in that order.
		"""
		gicon = self.get_gicon()
		if gicon:
			pbuf = icons.get_icon_for_gicon(gicon, icon_size)
			if pbuf:
				return pbuf
		icon_name = self.get_icon_name()
		if icon_name:
			icon = icons.get_icon_for_name(icon_name, icon_size)
			if icon: return icon
		return icons.get_icon_for_name(KupferObject.get_icon_name(self), icon_size)

	def get_icon(self):
		"""
		Returns an icon in GIcon format

		Subclasses should implement: get_gicon and get_icon_name,
		if they make sense.
		The methods are tried in that order.
		"""
		return icons.get_gicon_with_fallbacks(self.get_gicon(),
				(self.get_icon_name(), KupferObject.get_icon_name(self)))

	def get_gicon(self):
		"""Return GIcon, if there is one"""
		return None
	
	def get_icon_name(self):
		"""Return icon name. All items should have at least
		a generic icon name to return.
		"""
		return "kupfer-object"

def aslist(seq):
	"""Return a list out of @seq, or seq if it is a list"""
	if not isinstance(seq, type([])) and not isinstance(seq, type(())):
		seq = list(seq)
	return seq

class _NonpersistentToken (object):
	"Goes None when pickled"
	__slots__ = "object"
	def __init__(self, object_):
		self.object = object_
	def __nonzero__(self):
		return bool(self.object)
	def __reduce__(self):
		return (eval, ("None", ))

class Leaf (KupferObject):
	"""
	Base class for objects

	Leaf.object is the represented object (data)
	All Leaves should be hashable (__hash__ and __eq__)
	"""
	def __init__(self, obj, name):
		"""Represented object @obj and its @name"""
		super(Leaf, self).__init__(name)
		self.object = obj
		self._content_source = None
	
	def __hash__(self):
		return hash(unicode(self))

	def __eq__(self, other):
		return (type(self) == type(other) and self.object == other.object)

	def add_content(self, content):
		"""Register content source @content with Leaf"""
		self._content_source = _NonpersistentToken(content)

	def has_content(self):
		return self._content_source

	def content_source(self, alternate=False):
		"""Content of leaf. it MAY alter behavior with @alternate,
		as easter egg/extra mode"""
		return self._content_source and self._content_source.object

	def get_actions(self):
		"""Default (builtin) actions for this Leaf"""
		return ()

class Action (KupferObject):
	'''
	Base class for all actions

	Implicit interface:
	  valid_object will be called once for each (secondary) object
	  to see if it applies. If it is not defined, all objects are
	  assumed ok (within the other type/source constraints)

	def valid_object(self, obj, for_item):
		"""Whether @obj is good for secondary obj,
		where @for_item is passed in as a hint for
		which it should be applied to
		"""
		return True
	'''

	def repr_key(self):
		"""by default, actions of one type are all the same"""
		return ""

	def activate(self, leaf, obj=None):
		"""Use this action with @leaf and @obj

		@leaf: the object (Leaf)
		@obj: an indirect object (Leaf), if self.requires_object
		"""
		pass

	def is_factory(self):
		"""Return whether action may return a result collection as a Source"""
		return False

	def has_result(self):
		"""Return whether action may return a result item as a Leaf"""
		return False

	def is_async(self):
		"""If this action runs asynchronously, return True.

		Then activate(..) must return an object from the kupfer.task module,
		which will be queued to run by Kupfer's task scheduler.
		"""
		return False

	def item_types(self):
		"""Yield types this action may apply to. This is used only
		when this action is specified in __kupfer_actions__ to "decorate"
		"""
		return ()

	def valid_for_item(self, item):
		"""Whether action can be used with exactly @item"""
		return True

	def requires_object(self):
		"""If this action requires a secondary object
		to complete is action, return True
		"""
		return False

	def object_source(self, for_item=None):
		"""Source to use for object or None,
		to use the catalog (flat and filtered for @object_types)
		"""
		return None

	def object_types(self):
		"""Yield types this action may use as indirect objects, if the action
		requrires it.
		"""
		return ()

	def get_icon_name(self):
		return "gtk-execute"

class Source (KupferObject, pretty.OutputMixin):
	"""
	Source: Data provider for a kupfer browser

	All Sources should be hashable and treated as equal if
	their @repr are equal!

	"""
	def __init__(self, name):
		KupferObject.__init__(self, name)
		self.cached_items = None
		self._version = 1

	@property
	def version(self):
		"""version is for pickling (save and restore from cache),
		subclasses should increase self._version when changing"""
		return self._version

	def __eq__(self, other):
		return (type(self) == type(other) and repr(self) == repr(other) and
		        self.version == other.version)

	def __hash__(self ):
		return hash(repr(self))

	def toplevel_source(self):
		return self

	def initialize(self):
		"""
		Called when a Source enters Kupfer's system for real

		This method is called at least once for any "real" Source. A Source
		must be able to return an icon name for get_icon_name as well as a
		description for get_description, even if this method was never called.
		"""
		pass

	def repr_key(self):
		return ""

	def get_items(self):
		"""
		Internal method to compute and return the needed items

		Subclasses should use this method to return a sequence or
		iterator to the leaves it contains
		"""
		return []

	def is_dynamic(self):
		"""
		Whether to recompute contents each time it is accessed
		"""
		return False

	def mark_for_update(self):
		"""
		Mark source as changed

		it should be reloaded on next used (if normally cached)
		"""
		self.cached_items = None

	def should_sort_lexically(self):
		"""
		Sources should return items by most relevant order (most
		relevant first). If this is True, Source will sort items
		from get_item() in locale lexical order
		"""
		return False

	def get_leaves(self, force_update=False):
		"""
		Return a list of all leaves.

		Subclasses should implement get_items, so that Source
		can handle sorting and caching.
		if @force_update, ignore cache, print number of items loaded
		"""
		if self.should_sort_lexically():
			# sort in locale order
			sort_func = locale_sort
		else:
			sort_func = lambda x: x

		if self.is_dynamic():
			return sort_func(self.get_items())
		
		if self.cached_items is None or force_update:
			cache_type = aslist if force_update else datatools.SavedIterable
			self.cached_items = cache_type(sort_func(self.get_items()))
			if force_update:
				self.output_info("Loaded %d items" % len(self.cached_items))
			else:
				self.output_debug("Loaded items")
		return self.cached_items

	def has_parent(self):
		return False

	def get_parent(self):
		return None

	def get_leaf_repr(self):
		"""Return, if appicable, another object
		to take the source's place as Leaf"""
		return None

	def provides(self):
		"""A seq of the types of items it provides;
		empty is taken as anything -- however most sources
		should set this to exactly the type they yield
		"""
		return ()

class TextSource (KupferObject):
	"""TextSource base class implementation,

	this is a psedo Source"""
	def __init__(self, name=None):
		if not name:
			name = _("Text Matches")
		KupferObject.__init__(self, name)

	def __eq__(self, other):
		return (type(self) == type(other) and repr(self).__eq__(repr(other)))

	def __hash__(self ):
		return hash(repr(self))

	def initialize(self):
		pass

	def get_rank(self):
		"""All items are given this rank"""
		return 20

	def get_items(self, text):
		"""Get leaves for unicode string @text"""
		return ()

	def has_parent(self):
		return False

	def provides(self):
		"""A seq of the types of items it provides"""
		yield Leaf

