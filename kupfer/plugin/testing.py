"""
For testing purpose only.
"""
from __future__ import annotations

__kupfer_name__ = "Testing"
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_contents__ = ()
__kupfer_actions__ = ("TestAction", "TestAcyncAction")
__description__ = "Kupfer test plugin"
__version__ = "2023-05-01"
__author__ = "KB"


from kupfer.obj import Action, Leaf
from kupfer.core import commandexec


class TestAction(Action):
    rank_adjust = -50

    def __init__(self):
        Action.__init__(self, "test sync")

    def activate(self, leaf, iobj=None, ctx=None):
        return commandexec.ActionResultRefresh

    def item_types(self):
        yield Leaf


class TestAcyncAction(Action):
    rank_adjust = -50

    def __init__(self):
        Action.__init__(self, "test async")

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        ctx.register_late_result(commandexec.ActionResultRefresh)

    def item_types(self):
        yield Leaf
