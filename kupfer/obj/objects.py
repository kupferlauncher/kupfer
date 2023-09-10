"""
Copyright 2007--2009 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import typing as ty
import zlib

from kupfer import icons
from kupfer.obj import actions
from kupfer.obj.base import Action, Leaf, Source
from kupfer.obj.representation import TextRepresentation
from kupfer.core import commandexec

if ty.TYPE_CHECKING:
    from gettext import gettext as _, ngettext


__all__ = (
    "SourceLeaf",
    "UrlLeaf",
    "RunnableLeaf",
    "TextLeaf",
)


class SourceLeaf(Leaf):
    def __init__(self, obj: Source, name: str | None = None) -> None:
        """Create SourceLeaf for source @obj.
        Represented object is source."""
        Leaf.__init__(self, obj, name or str(obj))

    def has_content(self) -> bool:
        return True

    def repr_key(self) -> str:
        return repr(self.object)

    def content_source(self, alternate: bool = False) -> Source:
        assert isinstance(self.object, Source)
        return self.object

    def get_description(self) -> str | None:
        assert isinstance(self.object, Source)
        return self.object.get_description()

    @property
    def fallback_icon_name(self) -> str:  # type: ignore
        assert isinstance(self.object, Source)
        return self.object.fallback_icon_name

    def get_gicon(self) -> icons.GIcon | None:
        return self.object.get_gicon()

    def get_icon_name(self) -> str:
        assert isinstance(self.object, Source)
        return self.object.get_icon_name()


class UrlLeaf(Leaf, TextRepresentation):
    serializable = 1

    def __init__(self, obj: str, name: str | None) -> None:
        super().__init__(obj, name or obj)
        if obj != name:
            self.kupfer_add_alias(obj)

    def get_actions(self) -> ty.Iterator[Action]:
        yield actions.OpenUrl()

    def get_description(self) -> str:
        return self.object  # type:ignore

    def get_icon_name(self) -> str:
        return "text-html"


class RunnableLeaf(Leaf):
    """Leaf where the Leaf is basically the action itself, for items such
    as Quit, Log out etc."""

    def __init__(self, obj: ty.Any = None, name: str = "") -> None:
        Leaf.__init__(self, obj, name)

    def get_actions(self) -> ty.Iterator[Action]:
        yield actions.Perform(
            has_result=self.has_result(), item_types=tuple(self.item_types())
        )

    def has_result(self) -> bool:
        return False

    def item_types(self) -> ty.Iterable[Leaf]:
        return ()

    def run(self, ctx: commandexec.ExecutionToken | None = None) -> ty.Any:
        raise NotImplementedError

    def wants_context(self) -> bool:
        """Return ``True`` if you want the actions' execution
        context passed as ctx= in RunnableLeaf.run."""
        return False

    def repr_key(self) -> ty.Any:
        return None

    def get_gicon(self) -> icons.GIcon | None:
        if iname := self.get_icon_name():
            return icons.get_gicon_with_fallbacks(None, (iname,))

        return icons.ComposedIcon("kupfer-object", "kupfer-execute")

    def get_icon_name(self) -> str:
        return ""


class TextLeaf(Leaf, TextRepresentation):
    """Represent a text query.
    The represented object is a string"""

    serializable = 1

    def __init__(self, text: str, name: str | None = None) -> None:
        """@text *must* be unicode or UTF-8 str"""
        if not name:
            name = self.get_first_text_line(text)

        if not text or not name:
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
        return ngettext(
            '"%(text)s"', '(%(num)d lines) "%(text)s"', numlines
        ) % {"num": numlines, "text": desc}

    def get_icon_name(self) -> str:
        return "edit-select-all"
