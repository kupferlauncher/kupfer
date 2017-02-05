__kupfer_name__ = _("Higher-order Actions")
__kupfer_actions__ = (
    "Select",
    "TakeResult",
    "DiscardResult",
)
__description__ = _("Tools to work with commands as objects")
__version__ = "2010-01-11"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from kupfer.objects import Action, Leaf
from kupfer.obj.compose import ComposedLeaf, MultipleLeaf
from kupfer.core import commandexec
from kupfer import pretty


class Select (Action):
    rank_adjust = -15
    def __init__(self):
        Action.__init__(self, _("Select in Kupfer"))

    def has_result(self):
        return True
    def activate(self, leaf):
        return leaf
    def item_types(self):
        yield Leaf

def _exec_no_show_result(composedleaf):
    pretty.print_debug(__name__, "Evaluating command", composedleaf)
    obj, action, iobj = composedleaf.object
    ret = commandexec.activate_action(None, *composedleaf.object)
    result_type = commandexec.parse_action_result(action, ret)
    if result_type == commandexec.RESULT_OBJECT:
        return ret
    if result_type == commandexec.RESULT_SOURCE:
        leaves = list(ret.get_leaves())
        if not leaves:
            return
        if len(leaves) == 1:
            return leaves[0]
        else:
            return MultipleLeaf(leaves)


def _save_result(cleaf):
    # Save the result of @cleaf into a ResultObject
    # When the ResultObject is to be restored from serialized state,
    # @cleaf is executed again.
    # NOTE: This will have unintended consequences outside Trigger use.
    leaf = _exec_no_show_result(cleaf)
    if leaf is None:
        return None
    class ResultObject (Leaf):
        serializable = 1
        def __init__(self, leaf, cleaf):
            Leaf.__init__(self, leaf.object, str(leaf))
            vars(self).update(vars(leaf))
            self.name = _("Result of %s (%s)") % (cleaf, self)
            self.__composed_leaf = cleaf
            self.__class__.__bases__ = (leaf.__class__, Leaf)

        def get_gicon(self):
            return None
        def get_icon_name(self):
            return Leaf.get_icon_name(self)

        def __reduce__(self):
            return (_save_result, (self.__composed_leaf, ))
    return ResultObject(leaf, cleaf)


class TakeResult (Action):
    def __init__(self):
        Action.__init__(self, _("Run (Take Result)"))

    def has_result(self):
        return True
    def activate(self, leaf):
        return _save_result(leaf)

    def item_types(self):
        yield ComposedLeaf
    def valid_for_item(self, leaf):
        action = leaf.object[1]
        return ((action.has_result() or
                 action.is_factory()) and
                 not action.wants_context())
    def get_description(self):
        return _("Take the command result as a proxy object")

class DiscardResult (Action):
    """Run ComposedLeaf without showing the result"""
    def __init__(self):
        Action.__init__(self, _("Run (Discard Result)"))

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        commandexec.activate_action(ctx, *leaf.object)
    def item_types(self):
        yield ComposedLeaf
    def valid_for_item(self, leaf):
        action = leaf.object[1]
        return action.has_result() or action.is_factory()
    def get_description(self):
        return None

