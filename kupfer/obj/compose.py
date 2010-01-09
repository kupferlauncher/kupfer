# encoding: utf-8

from kupfer import icons
from kupfer import pretty
from kupfer import utils

from kupfer.obj.base import Leaf, Action, Source, InvalidDataError
from kupfer.obj.objects import Perform, RunnableLeaf, TextLeaf

class TimedPerform (Perform):
	"""A timed proxy version of Perform

	Proxy factory/result/async from a delegate action
	Delay action by a couple of seconds
	"""
	def __init__(self):
		Action.__init__(self, _("Run After Delay..."))

	def activate(self, leaf, iobj=None):
		from kupfer import scheduler
		# make a timer that will fire when Kupfer exits
		interval = utils.parse_time_interval(iobj.object)
		pretty.print_debug(__name__, "Run %s in %s seconds" % (leaf, interval))
		timer = scheduler.Timer(True)
		timer.set(interval, leaf.run)

	def requires_object(self):
		return True
	def object_types(self):
		yield TextLeaf

	def valid_object(self, iobj, for_item=None):
		interval = utils.parse_time_interval(iobj.object)
		return interval > 0

	def get_description(self):
		return _("Perform command after a specified time interval")

class ComposedLeaf (RunnableLeaf):
	serilizable = True
	def __init__(self, obj, action, iobj=None):
		object_ = (obj, action, iobj)
		# A slight hack: We remove trailing ellipsis and whitespace
		format = lambda o: unicode(o).strip(".… ")
		name = u" → ".join([format(o) for o in object_ if o is not None])
		RunnableLeaf.__init__(self, object_, name)

	def __getstate__(self):
		from kupfer import puid
		state = dict(vars(self))
		state["object"] = [puid.get_unique_id(o) for o in self.object]
		return state

	def __setstate__(self, state):
		from kupfer import puid
		vars(self).update(state)
		objid, actid, iobjid = state["object"]
		obj = puid.resolve_unique_id(objid)
		act = puid.resolve_action_id(actid, obj)
		iobj = puid.resolve_unique_id(iobjid)
		if (not obj or not act) or (iobj is None) != (iobjid is None):
			raise InvalidDataError("Parts of %s not restored" % unicode(self))
		self.object[:] = [obj, act, iobj]

	def get_actions(self):
		yield Perform()
		yield TimedPerform()

	def repr_key(self):
		return self

	def run(self):
		from kupfer import commandexec
		ctx = commandexec.DefaultActionExecutionContext()
		obj, action, iobj = self.object
		return ctx.run(obj, action, iobj, delegate=True)

	def get_gicon(self):
		obj, action, iobj = self.object
		return icons.ComposedIcon(obj.get_icon(), action.get_icon())

class _MultipleLeafContentSource (Source):
	def __init__(self, leaf):
		Source.__init__(self, unicode(leaf))
		self.leaf = leaf
	def get_items(self):
		return self.leaf.object

class MultipleLeaf (Leaf):
	"""
	A Leaf representing a collection of leaves.

	The represented object is a frozenset of the contained Leaves
	"""
	def __init__(self, obj, name):
		Leaf.__init__(self, frozenset(obj), name)

	def has_content(self):
		return True

	def content_source(self, alternate=False):
		return _MultipleLeafContentSource(self)

	def get_description(self):
		n = len(self.object)
		return ngettext("%s object", "%s objects", n) % (n, )
	def get_gicon(self):
		pass
