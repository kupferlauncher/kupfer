"""
Copyright 2007--2009 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import typing as ty
import zlib

from gi.repository import GdkPixbuf

from kupfer import icons
from kupfer.support import kupferstring

from .base import Action, Leaf, Source
from .files import OpenUrl
from .representation import TextRepresentation

if ty.TYPE_CHECKING:
    _ = str


class SourceLeaf(Leaf):
    def __init__(self, obj: Source, name: ty.Optional[str] = None) -> None:
        """Create SourceLeaf for source @obj"""
        Leaf.__init__(self, obj, name or str(obj))

    def has_content(self) -> bool:
        return True

    def repr_key(self) -> str:
        return repr(self.object)

    def content_source(self, alternate: bool = False) -> Source:
        return self.object  # type: ignore

    def get_description(self) -> ty.Optional[str]:
        return self.object.get_description()  # type: ignore

    # FIXME: property vs class field
    @property
    def fallback_icon_name(self) -> str:
        return self.object.fallback_icon_name  # type: ignore

    def get_gicon(self) -> GdkPixbuf.Pixbuf | None:
        return self.object.get_gicon()

    def get_icon_name(self) -> str:
        return self.object.get_icon_name()  # type: ignore


class UrlLeaf(Leaf, TextRepresentation):
    serializable = 1

    def __init__(self, obj: str, name: str | None) -> None:
        super().__init__(obj, name or obj)
        if obj != name:
            self.kupfer_add_alias(obj)

    def get_actions(self) -> ty.Iterator[Action]:
        yield OpenUrl()

    def get_description(self) -> ty.Optional[str]:
        return self.object  # type:ignore

    def get_icon_name(self) -> str:
        return "text-html"


class RunnableLeaf(Leaf):
    """Leaf where the Leaf is basically the action itself,
    for items such as Quit, Log out etc.
    """

    def __init__(self, obj: ty.Any = None, name: str = "") -> None:
        Leaf.__init__(self, obj, name)

    def get_actions(self) -> ty.Iterator[Action]:
        yield Perform()

    def run(self, ctx: ty.Any = None) -> None:
        raise NotImplementedError

    def wants_context(self) -> bool:
        """Return ``True`` if you want the actions' execution
        context passed as ctx= in RunnableLeaf.run
        """
        return False

    def repr_key(self) -> ty.Any:
        return ""

    def get_gicon(self) -> GdkPixbuf.Pixbuf | None:
        if iname := self.get_icon_name():
            return icons.get_gicon_with_fallbacks(None, (iname,))

        return icons.ComposedIcon("kupfer-object", "kupfer-execute")

    def get_icon_name(self) -> str:
        return ""


class Perform(Action):
    """Perform the action in a RunnableLeaf"""

    action_accelerator: ty.Optional[str] = "o"
    rank_adjust = 5

    def __init__(self, name: ty.Optional[str] = None):
        # TRANS: 'Run' as in Perform a (saved) command
        super().__init__(name=name or _("Run"))

    def wants_context(self) -> bool:
        return True

    def activate(
        self, leaf: ty.Any, iobj: ty.Any = None, ctx: ty.Any = None
    ) -> None:
        if leaf.wants_context():
            leaf.run(ctx=ctx)
            return

        leaf.run()

    def get_description(self) -> str:
        return _("Perform command")


class TextLeaf(Leaf, TextRepresentation):
    """Represent a text query
    The represented object is a unicode string
    """

    serializable = 1

    def __init__(self, text: str, name: ty.Optional[str] = None) -> None:
        """@text *must* be unicode or UTF-8 str"""
        # text = kupferstring.tounicode(text)  # type: ignore
        if not name:
            name = self.get_first_text_line(text)

        if len(text) == 0 or not name:
            name = _("(Empty Text)")

        assert name
        Leaf.__init__(self, text, name)

    def repr_key(self) -> ty.Any:
        return zlib.crc32(self.object.encode("utf-8", "surrogateescape"))

    @classmethod
    def get_first_text_line(cls, text: str) -> str:
        if not text:
            return text

        firstline, *_dummy = text.lstrip().partition("\n")
        return firstline

    def get_description(self) -> str:
        numlines = self.object.count("\n") + 1
        desc = self.get_first_text_line(self.object)

        # TRANS: This is description for a TextLeaf, a free-text search
        # TRANS: The plural parameter is the number of lines %(num)d
        return ngettext(  # type: ignore
            '"%(text)s"', '(%(num)d lines) "%(text)s"', numlines
        ) % {"num": numlines, "text": desc}

    def get_icon_name(self) -> str:
        return "edit-select-all"
