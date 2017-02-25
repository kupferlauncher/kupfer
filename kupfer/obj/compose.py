# encoding: utf-8

from kupfer import icons
from kupfer import pretty
from kupfer import utils
from kupfer import datatools
from kupfer import puid

from kupfer.obj.base import Leaf, Action, Source, InvalidDataError
from kupfer.obj.objects import Perform, RunnableLeaf, TextLeaf

class TimedPerform (Perform):
    """A timed (delayed) version of Run (Perform) """
    action_accelerator = None
    def __init__(self):
        Action.__init__(self, _("Run after Delay..."))

    def activate(self, leaf, iobj, ctx):
        from kupfer import scheduler
        # make a timer that will fire when Kupfer exits
        interval = utils.parse_time_interval(iobj.object)
        pretty.print_debug(__name__, "Run %s in %s seconds" % (leaf, interval))
        timer = scheduler.Timer(True)
        args = (ctx,) if leaf.wants_context() else ()
        timer.set(interval, leaf.run, *args)

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
    serializable = 1
    def __init__(self, obj, action, iobj=None):
        object_ = (obj, action, iobj)
        # A slight hack: We remove trailing ellipsis and whitespace
        format = lambda o: str(o).strip(".… ")
        name = " → ".join([format(o) for o in object_ if o is not None])
        RunnableLeaf.__init__(self, object_, name)

    def __getstate__(self):
        state = dict(vars(self))
        state["object"] = [puid.get_unique_id(o) for o in self.object]
        return state

    def __setstate__(self, state):
        vars(self).update(state)
        objid, actid, iobjid = state["object"]
        obj = puid.resolve_unique_id(objid)
        act = puid.resolve_action_id(actid, obj)
        iobj = puid.resolve_unique_id(iobjid)
        if (not obj or not act) or (iobj is None) != (iobjid is None):
            raise InvalidDataError("Parts of %s not restored" % str(self))
        self.object[:] = [obj, act, iobj]

    def get_actions(self):
        yield Perform()
        yield TimedPerform()

    def repr_key(self):
        return self

    def wants_context(self):
        return True

    def run(self, ctx):
        obj, action, iobj = self.object
        return ctx.delegated_run(obj, action, iobj)

    def get_gicon(self):
        obj, action, iobj = self.object
        return icons.ComposedIcon(obj.get_icon(), action.get_icon())

class _MultipleLeafContentSource (Source):
    def __init__(self, leaf):
        Source.__init__(self, str(leaf))
        self.leaf = leaf
    def get_items(self):
        return self.leaf.object

class MultipleLeaf (Leaf):
    """
    A Leaf for the direct representation of many leaves. It is not
    a container or "source", it *is* the many leaves itself.

    The represented object is a sequence of Leaves
    """
    serializable = 1
    def __init__(self, obj, name=_("Multiple Objects")):
        # modifying the list of objects is strictly forbidden
        robj = list(datatools.UniqueIterator(obj))
        Leaf.__init__(self, robj, name)

    def get_multiple_leaf_representation(self):
        return self.object

    def __getstate__(self):
        state = dict(vars(self))
        state["object"] = [puid.get_unique_id(o) for o in self.object]
        return state

    def __setstate__(self, state):
        vars(self).update(state)
        objects = []
        for id_ in state["object"]:
            obj = puid.resolve_unique_id(id_)
            if obj is None:
                raise InvalidDataError("%s could not be restored!" % (id_, ))
            objects.append(obj)
        self.object[:] = objects

    def has_content(self):
        return True

    def content_source(self, alternate=False):
        return _MultipleLeafContentSource(self)

    def get_description(self):
        n = len(self.object)
        return ngettext("%s object", "%s objects", n) % (n, )
    def get_icon_name(self):
        return "kupfer-object-multiple"
