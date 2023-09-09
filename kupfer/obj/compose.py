"""
Object related to composited objects.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import typing as ty
from gettext import gettext as _
from gettext import ngettext

from kupfer import icons, puid
from kupfer.support import itertools, pretty, scheduler, textutils
from kupfer.core import commandexec
from kupfer.obj import actions, exceptions, objects
from kupfer.obj.base import Action, Leaf, Source


__all__ = (
    "TimedPerform",
    "ComposedLeaf",
    "MultipleLeaf",
)


class TimedPerform(actions.Perform):
    """A timed (delayed) version of Run (Perform)"""

    action_accelerator: str | None = None

    def __init__(self, name: str = _("Run after Delay...")) -> None:
        super().__init__(name)

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        assert isinstance(leaf, objects.RunnableLeaf)
        assert isinstance(iobj, objects.TextLeaf)
        # make a timer that will fire when Kupfer exits
        interval = textutils.parse_time_interval(iobj.object)
        pretty.print_debug(__name__, f"Run {leaf} in {interval} seconds")
        timer = scheduler.Timer(True)
        if leaf.wants_context():
            timer.set(interval, leaf.run, ctx)
        else:
            timer.set(interval, leaf.run)

        return None

    def requires_object(self) -> bool:
        return True

    def object_types(self) -> ty.Iterator[ty.Type[Leaf]]:
        yield objects.TextLeaf

    def valid_object(self, iobj: Leaf, for_item: Leaf | None = None) -> bool:
        return textutils.parse_time_interval(iobj.object) > 0

    def get_description(self) -> str:
        return _("Perform command after a specified time interval")


class ComposedLeaf(objects.RunnableLeaf):
    """Leaf that contains many other leaves, created by compose action.
    Represented object is tuple (object, action, action object).
    """

    serializable = 1

    def __init__(
        self, obj: Leaf, action: Action, iobj: Leaf | None = None
    ) -> None:
        object_ = (obj, action, iobj)
        # A slight hack: We remove trailing ellipsis and whitespace
        name = " → ".join(str(o).strip(".… ") for o in object_ if o is not None)
        objects.RunnableLeaf.__init__(self, object_, name)

    def __getstate__(self) -> dict[str, ty.Any]:
        state = dict(vars(self))
        state["object"] = [puid.get_unique_id(o) for o in self.object]
        return state

    def __setstate__(self, state: dict[str, ty.Any]) -> None:
        vars(self).update(state)
        objid, actid, iobjid = state["object"]
        obj = puid.resolve_unique_id(objid)
        assert isinstance(obj, Leaf)
        act = puid.resolve_action_id(actid, obj)
        iobj = puid.resolve_unique_id(iobjid)
        if (not obj or not act) or (iobj is None) != (iobjid is None):
            raise exceptions.InvalidDataError(f"Parts of {self} not restored")

        self.object[::] = [obj, act, iobj]

    def get_actions(self) -> ty.Iterator[Action]:
        yield actions.Perform()
        yield TimedPerform()

    def repr_key(self) -> ty.Any:
        return self

    def wants_context(self) -> bool:
        return True

    def run(self, ctx: commandexec.ExecutionToken | None = None) -> None:
        obj, action, iobj = self.object
        assert ctx and hasattr(ctx, "delegated_run")
        ctx.delegated_run(obj, action, iobj)

    def get_gicon(self) -> icons.GIcon | None:
        obj, action, _iobj = self.object
        return icons.ComposedIcon(obj.get_icon(), action.get_icon())


class _MultipleLeafContentSource(Source):
    def __init__(self, leaf: Leaf) -> None:
        Source.__init__(self, str(leaf))
        self.leaf = leaf

    def get_items(self) -> ty.Any:
        return self.leaf.object


class MultipleLeaf(Leaf):
    """A Leaf for the direct representation of many leaves. It is not
    a container or "source", it *is* the many leaves itself.

    The represented object is a sequence of Leaves."""

    serializable = 1

    def __init__(self, obj: ty.Any, name: str = _("Multiple Objects")) -> None:
        # modifying the list of objects is strictly forbidden
        robj = list(itertools.unique_iterator(obj))
        Leaf.__init__(self, robj, name)

    def get_multiple_leaf_representation(self) -> ty.Sequence[Leaf]:
        return ty.cast(ty.Sequence[Leaf], self.object)

    def __getstate__(self) -> dict[str, ty.Any]:
        state = dict(vars(self))
        state["object"] = [puid.get_unique_id(o) for o in self.object]
        return state

    def __setstate__(self, state: dict[str, ty.Any]) -> None:
        vars(self).update(state)
        objs = []
        for id_ in state["object"]:
            if (obj := puid.resolve_unique_id(id_)) is not None:
                objs.append(obj)
            else:
                raise exceptions.InvalidDataError(
                    f"{id_} could not be restored!"
                )

        self.object[::] = objs

    def has_content(self) -> bool:
        return True

    def content_source(self, alternate: bool = False) -> Source:
        return _MultipleLeafContentSource(self)

    def get_description(self) -> str:
        num = len(self.object)
        return ngettext("%s object", "%s objects", num) % (num,)

    def get_icon_name(self) -> str:
        return "kupfer-object-multiple"
