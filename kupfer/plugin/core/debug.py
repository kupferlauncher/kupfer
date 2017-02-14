"""
This module contains internal and / or experimental Kupfer features.

These are not meant to be useful to "normal" users of Kupfer -- if they are,
they can be tested here before they migrate to a fitting plugin.
"""

from kupfer.obj.base import Action, Leaf, Source
from kupfer.obj.compose import ComposedLeaf
from kupfer import pretty

__kupfer_sources__ = ()
__kupfer_contents__ = (
        "ComposedSource",
    )
__kupfer_actions__ = (
        "DebugInfo",
        "Forget",
    )
__description__ = __doc__
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


class DebugInfo (Action):
    """ Print debug info to terminal """
    rank_adjust = -50
    def __init__(self):
        Action.__init__(self, "Debug Info")

    def activate(self, leaf):
        import io
        # NOTE: Core imports
        from kupfer.core import qfurl
        from kupfer import uiutils
        from kupfer import puid

        output = io.StringIO()
        def print_func(*args):
            print(" ".join(str(a) for a in args), file=output)
            pretty.print_debug("debug", *args)

        print_func("Debug info about", leaf)
        print_func(leaf, repr(leaf))
        def get_qfurl(leaf):
            try:
                return qfurl.qfurl(leaf)
            except qfurl.QfurlError:
                pass
        def get_object_fields(leaf):
            return {
                "repr" : leaf,
                "description": leaf.get_description(),
                "thumb" : leaf.get_thumbnail(32, 32),
                "gicon" : leaf.get_gicon(),
                "icon" : leaf.get_icon(),
                "icon-name": leaf.get_icon_name(),
                "type" : type(leaf),
                "module" : leaf.__module__,
                "aliases" : getattr(leaf, "name_aliases", None),
                "qfurl" : get_qfurl(leaf),
                "puid" : puid.get_unique_id(leaf),
                }
        def get_leaf_fields(leaf):
            base = get_object_fields(leaf)
            base.update( {
                "object" : leaf.object,
                "object-type" : type(leaf.object),
                "content" : leaf.content_source(),
                "content-alt" : leaf.content_source(alternate=True),
                "builtin-actions": list(leaf.get_actions()),
                } )
            return base
        def get_source_fields(src):
            base = get_object_fields(src)
            base.update({
                "dynamic" : src.is_dynamic(),
                "sort" : src.should_sort_lexically(),
                "parent" : src.get_parent(),
                "leaf" : src.get_leaf_repr(),
                "provides" : list(src.provides()),
                "cached_items": type(src.cached_items),
                "len": isinstance(src.cached_items, list) and len(src.cached_items),
                } )
            return base

        def print_fields(fields):
            for field in sorted(fields):
                val = fields[field]
                rep = repr(val)
                print_func("%-15s:" % field, rep)
                if str(val) not in rep:
                    print_func("%-15s:" % field, val)
        leafinfo = get_leaf_fields(leaf)
        print_fields(leafinfo)
        if leafinfo["content"]:
            print_func("Content ============")
            print_fields(get_source_fields(leafinfo["content"]))
        if leafinfo["content"] != leafinfo["content-alt"]:
            print_func("Content-Alt ========")
            print_fields(get_source_fields(leafinfo["content-alt"]))
        uiutils.show_text_result(output.getvalue())

    def get_description(self):
        return "Print debug output (for interal kupfer use)"
    def get_icon_name(self):
        return "emblem-system"
    def item_types(self):
        yield Leaf

class Forget (Action):
    rank_adjust = -10
    def __init__(self):
        Action.__init__(self, "Forget")

    def activate(self, leaf):
        # NOTE: Core imports
        from kupfer.core import learn

        # FIXME: This is a large, total, utter HACK
        if isinstance(leaf, ComposedLeaf):
            for o in leaf.object:
                learn._register.pop(repr(o), None)
        if isinstance(leaf, ActionLeaf):
            learn._register.pop(repr(leaf.object), None)
        else:
            learn._register.pop(repr(leaf), None)

    def item_types(self):
        yield Leaf

    def get_description(self):
        return "Let Kupfer forget about this object"

class ActionLeaf (Leaf):
    def __init__(self, action):
        Leaf.__init__(self, action, str(action))

    def get_actions(self):
        act = self.object
        if not (hasattr(act, "requires_object") and act.requires_object()):
            yield Apply(act)

    def get_description(self):
        return self.object.get_description()
    def get_icon_name(self):
        return self.object.get_icon_name()

class Apply (Action):
    rank_adjust = 5
    def __init__(self, action):
        Action.__init__(self, "Apply To...")
        self.action = action

    def is_factory(self):
        return self.action.is_factory()
    def has_result(self):
        return self.action.has_result()
    def is_async(self):
        return self.action.is_async()
    def requires_object(self):
        return True
    def object_types(self):
        return self.action.item_types()
    def valid_object(self, obj, for_item=None):
        return self.action.valid_for_item(obj)

    def wants_context(self):
        return self.action.wants_context()

    def activate(self, leaf, iobj, **kwargs):
        return self.action.activate(iobj, **kwargs)

class ComposedSource (Source):
    """
    Decorated ComposedLeaf with a Source that shows the contents of
    Composed Commands
    """
    def __init__(self, leaf):
        Source.__init__(self, "Composed Command")
        self.leaf = leaf

    def get_items(self):
        obj = self.leaf.object
        yield self.leaf.object[0]
        yield ActionLeaf(obj[1])
        if self.leaf.object[2] is not None:
            yield self.leaf.object[2]

    def repr_key(self):
        return self.leaf.repr_key()

    @classmethod
    def decorates_type(cls):
        return ComposedLeaf

    @classmethod
    def decorate_item(cls, leaf):
        return cls(leaf)
