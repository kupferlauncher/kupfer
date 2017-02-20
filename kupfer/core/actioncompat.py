
def _get_leaf_members(leaf):
    """
    Return an iterator to members of @leaf, if it is a multiple leaf
    """
    try:
        return leaf.get_multiple_leaf_representation()
    except AttributeError:
        return (leaf, )

def action_valid_for_item(action, leaf):
    return all(action.valid_for_item(L) for L in _get_leaf_members(leaf))

def actions_for_item(leaf, sourcecontroller):
    if leaf is None:
        return []
    actions = None
    for L in _get_leaf_members(leaf):
        l_actions = set(L.get_actions())
        l_actions.update(sourcecontroller.get_actions_for_leaf(L))
        if actions is None:
            actions = l_actions
        else:
            actions.intersection_update(l_actions)
    return actions

def iobject_source_for_action(action, for_item):
    """
    Return (src, use_catalog)

    where
    src: object source or None,
    use_catalog: True to use catalog in addition.
    """
    for leaf in _get_leaf_members(for_item):
        return action.object_source(leaf), action.object_source_and_catalog(leaf)

def iobjects_valid_for_action(action, for_item):
    """
    Return a filtering *function* that will let through
    those leaves that are good iobjects for @action and @for_item.
    """
    def valid_object(leaf, for_item):
        _valid_object = action.valid_object
        for L in _get_leaf_members(leaf):
            for I in _get_leaf_members(for_item):
                if not _valid_object(L, for_item=I):
                    return False
        return True

    types = tuple(action.object_types())
    def type_obj_check(iobjs):
        for i in iobjs:
            if (isinstance(i, types) and valid_object(i, for_item=for_item)):
                yield i
    def type_check(itms):
        for i in itms:
            if isinstance(i, types):
                yield i

    if hasattr(action, "valid_object"):
        return type_obj_check
    else:
        return type_check

