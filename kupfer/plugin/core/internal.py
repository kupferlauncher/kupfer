import typing as ty

from kupfer.core import commandexec
from kupfer.obj import Leaf, RunnableLeaf, Source

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__kupfer_sources__ = ("KupferInterals", "CommandResults")
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


class LastCommand(RunnableLeaf):
    """Represented object is the command tuple to run"""

    qf_id = "lastcommand"

    def __init__(self, obj):
        RunnableLeaf.__init__(self, obj, _("Last Command"))

    def wants_context(self):
        return True

    def run(self, ctx=None):
        assert ctx
        obj, action, iobj = self.object
        return ctx.delegated_run(obj, action, iobj)


class KupferInterals(Source):
    def __init__(self):
        Source.__init__(self, _("Internal Kupfer Objects"))

    def is_dynamic(self):
        return True

    def get_items(self):
        ctx = commandexec.default_action_execution_context()
        if ctx.last_command is not None:
            yield LastCommand(ctx.last_command)

    def provides(self):
        yield LastCommand


class LastResultObject(Leaf):
    "dummy superclass"

    def __init__(self, leaf):
        super().__init__(leaf.object, _("Last Result"))


def _make_first_result_object(leaf):
    #    global LastResultObject

    class _LastResultObject(LastResultObject):
        qf_id = "lastresult"

        def __init__(self, leaf):
            super().__init__(leaf)
            vars(self).update(vars(leaf))
            self.name = _("Last Result")
            self.__orignal_leaf = leaf
            self.__class__.__bases__ = (leaf.__class__, Leaf)

        def get_gicon(self):
            return None

        def get_icon_name(self):
            return Leaf.get_icon_name(self)

        def get_thumbnail(self, width, height):
            return None

        def get_description(self):
            return str(self.__orignal_leaf)

    return _LastResultObject(leaf)


class CommandResults(Source):
    def __init__(self):
        Source.__init__(self, _("Command Results"))

    def is_dynamic(self):
        return True

    def get_items(self):
        ctx = commandexec.default_action_execution_context()
        yield from reversed(ctx.last_results)
        try:
            leaf = ctx.last_results[-1]
        except IndexError:
            return

        yield _make_first_result_object(leaf)

    def provides(self):
        yield Leaf
        yield LastResultObject
