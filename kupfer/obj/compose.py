from __future__ import annotations

import typing as ty

from gi.repository import GdkPixbuf

from kupfer import icons, puid, utils
from kupfer.support import datatools, pretty, scheduler

from .base import Action, Leaf, Source
from .exceptions import InvalidDataError
from .objects import Perform, RunnableLeaf, TextLeaf

if ty.TYPE_CHECKING:
    from gettext import gettext as _, ngettext


class TimedPerform(Perform):
    """A timed (delayed) version of Run (Perform)"""

    action_accelerator: ty.Optional[str] = None

    def __init__(self) -> None:
        super().__init__(_("Run after Delay..."))

    def activate(
        self, leaf: ty.Any, iobj: ty.Any = None, ctx: ty.Any = None
    ) -> None:
        # make a timer that will fire when Kupfer exits
        interval = utils.parse_time_interval(iobj.object)
        pretty.print_debug(__name__, f"Run {leaf} in {interval} seconds")
        timer = scheduler.Timer(True)
        args = (ctx,) if leaf.wants_context() else ()
        timer.set(interval, leaf.run, *args)

    def requires_object(self) -> bool:
        return True

    def object_types(self) -> ty.Iterator[ty.Type[Leaf]]:
        yield TextLeaf

    def valid_object(
        self, iobj: Leaf, for_item: ty.Optional[Leaf] = None
    ) -> bool:
        interval = utils.parse_time_interval(iobj.object)
        return interval > 0

    def get_description(self) -> str:
        return _("Perform command after a specified time interval")


class ComposedLeaf(RunnableLeaf):
    serializable = 1

    def __init__(
        self, obj: ty.Any, action: Action, iobj: ty.Optional[Leaf] = None
    ) -> None:
        object_ = (obj, action, iobj)
        # A slight hack: We remove trailing ellipsis and whitespace
        name = " → ".join(str(o).strip(".… ") for o in object_ if o is not None)
        RunnableLeaf.__init__(self, object_, name)

    def __getstate__(self) -> ty.Dict[str, ty.Any]:
        state = dict(vars(self))
        state["object"] = [puid.get_unique_id(o) for o in self.object]
        return state

    def __setstate__(self, state: ty.Dict[str, ty.Any]) -> None:
        vars(self).update(state)
        objid, actid, iobjid = state["object"]
        obj = puid.resolve_unique_id(objid)
        act = puid.resolve_action_id(actid, obj)
        iobj = puid.resolve_unique_id(iobjid)
        if (not obj or not act) or (iobj is None) != (iobjid is None):
            raise InvalidDataError(f"Parts of {self} not restored")

        self.object[::] = [obj, act, iobj]

    def get_actions(self) -> ty.Iterator[Action]:
        yield Perform()
        yield TimedPerform()

    def repr_key(self) -> ty.Any:
        return self

    def wants_context(self) -> bool:
        return True

    def run(self, ctx: ty.Any = None) -> None:
        obj, action, iobj = self.object
        assert hasattr(ctx, "delegated_run")
        ctx.delegated_run(obj, action, iobj)

    def get_gicon(self) -> GdkPixbuf.Pixbuf | None:
        obj, action, _iobj = self.object
        return icons.ComposedIcon(obj.get_icon(), action.get_icon())


class _MultipleLeafContentSource(Source):
    def __init__(self, leaf: Leaf) -> None:
        Source.__init__(self, str(leaf))
        self.leaf = leaf

    def get_items(self) -> ty.Any:
        return self.leaf.object


class MultipleLeaf(Leaf):
    """
    A Leaf for the direct representation of many leaves. It is not
    a container or "source", it *is* the many leaves itself.

    The represented object is a sequence of Leaves
    """

    serializable = 1

    def __init__(self, obj: ty.Any, name: ty.Optional[str] = None) -> None:
        # modifying the list of objects is strictly forbidden
        robj = list(datatools.unique_iterator(obj))
        Leaf.__init__(self, robj, name or _("Multiple Objects"))

    def get_multiple_leaf_representation(self) -> ty.Iterable[Leaf]:
        return self.object  # type: ignore

    def __getstate__(self) -> ty.Dict[str, ty.Any]:
        state = dict(vars(self))
        state["object"] = [puid.get_unique_id(o) for o in self.object]
        return state

    def __setstate__(self, state: ty.Dict[str, ty.Any]) -> None:
        vars(self).update(state)
        objects = []
        for id_ in state["object"]:
            obj = puid.resolve_unique_id(id_)
            if obj is None:
                raise InvalidDataError(f"{id_} could not be restored!")

            objects.append(obj)

        self.object[::] = objects

    def has_content(self) -> bool:
        return True

    def content_source(self, alternate: bool = False) -> Source:
        return _MultipleLeafContentSource(self)

    def get_description(self) -> str:
        num = len(self.object)
        return ngettext("%s object", "%s objects", num) % (num,)

    def get_icon_name(self) -> str:
        return "kupfer-object-multiple"
