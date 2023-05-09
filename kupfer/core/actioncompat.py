from __future__ import annotations

import typing as ty

from kupfer.obj import Action, KupferObject, Leaf, Source

from ._support import get_leaf_members
from .sources import SourceController


def action_valid_for_item(action: Action, leaf: Leaf) -> bool:
    """Check is `action` is valid for all `leaf` representation.

    Note: valid_for_item MUST return bool.
    """
    return all(action.valid_for_item(L) for L in get_leaf_members(leaf))


def actions_for_item(
    leaf: Leaf | None, sourcecontroller: SourceController
) -> set[Action]:
    """Get list of actions for `leaf` from `sourcecontroller`."""

    if leaf is None:
        return set()

    actions: set[Action] | None = None

    for member in get_leaf_members(leaf):
        l_actions = set(member.get_actions())
        l_actions.update(sourcecontroller.get_actions_for_leaf(member))
        if actions is None:
            actions = l_actions
        else:
            actions.intersection_update(l_actions)

    return actions or set()


def iobject_source_for_action(
    action: Action, for_item: Leaf
) -> tuple[Source | None, bool]:
    """Get iobjects source for `action` for `for_item`.

    Simply call `Action.object_source` and 'Action.object_source_and_catalog`
    for first representation of `for_item`.

    Return (src, use_catalog)

    where
    src: object source or None,
    use_catalog: True to use catalog in addition.
    """
    leaf, *_rest = get_leaf_members(for_item)
    if not leaf:
        return None, False

    return action.object_source(leaf), action.object_source_and_catalog(leaf)


FilteringFunction = ty.Callable[
    [ty.Iterable[KupferObject]], ty.Iterable[ty.Union[Action, Leaf]]
]


def iobjects_valid_for_action(
    action: Action, for_item: Leaf
) -> FilteringFunction:
    """Return a filtering *function* that will let through
    those leaves that are good iobjects for @action and @for_item.
    """
    types = tuple(action.object_types())

    if not hasattr(action, "valid_object"):

        def type_check(itms):
            return (i for i in itms if isinstance(i, types))

        return type_check

    _valid_object = action.valid_object  # type: ignore

    def type_obj_check(iobjs):
        return (
            i
            for i in iobjs
            if isinstance(i, types)
            and all(
                _valid_object(leaf, for_item=item)
                for leaf in get_leaf_members(i)
                for item in get_leaf_members(for_item)
            )
        )

    return type_obj_check
