from __future__ import annotations

__kupfer_name__ = _("Clipboards")
__kupfer_sources__ = ("ClipboardSource",)
__kupfer_actions__ = ("ClearClipboards",)
__description__ = _("Recent clipboards and clipboard proxy objects")
__version__ = "2023-03-22"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import typing as ty
from collections import deque
from contextlib import suppress
from pathlib import Path

from gi.repository import Gdk, Gio, Gtk

from kupfer import plugin_support
from kupfer.obj import (
    Action,
    FileLeaf,
    Leaf,
    Source,
    SourceLeaf,
    TextLeaf,
    UrlLeaf,
)
from kupfer.obj.compose import MultipleLeaf
from kupfer.support import validators

if ty.TYPE_CHECKING:
    from gettext import gettext as _
    from gettext import ngettext


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "max",
        "label": _("Number of recent clipboards to remember"),
        "type": int,
        "value": 10,
    },
    {
        "key": "use_selection",
        "label": _("Include selected text in clipboard history"),
        "type": bool,
        "value": False,
    },
    {
        "key": "sync_selection",
        "label": _("Copy selected text to primary clipboard"),
        "type": bool,
        "value": False,
    },
)


class SelectedText(TextLeaf):
    qf_id = "selectedtext"

    def __init__(self, text):
        TextLeaf.__init__(self, text, _("Selected Text"))

    def __repr__(self):
        return f"<{__name__} {self.qf_id}>"


class SelectedFile(FileLeaf):
    qf_id = "selectedfile"

    def __init__(self, text):
        super().__init__(text, _("Selected File"))

    def __repr__(self):
        return f"<{__name__} {self.qf_id}>"


class SelectedUrl(UrlLeaf):
    qf_id = "selectedtext"

    def __init__(self, text):
        super().__init__(text, _("Selected URL"))

    def __repr__(self):
        return f"<{__name__} {self.qf_id}>"


def _new_selected_leaf(text: str | None) -> Leaf | None:
    if not text:
        return None

    if validators.is_url(text):
        return SelectedUrl(text)

    if validators.is_valid_file_path(text):
        path = Path(text).expanduser()
        if path.exists():
            return SelectedFile(path)

    return SelectedText(text)


class ClipboardText(TextLeaf):
    def get_description(self):
        numlines = self.object.count("\n") + 1
        desc = self.get_first_text_line(self.object)

        return ngettext(
            'Clipboard "%(desc)s"',
            'Clipboard with %(num)d lines "%(desc)s"',
            numlines,
        ) % {"num": numlines, "desc": desc}


class CurrentClipboardText(ClipboardText):
    qf_id = "clipboardtext"

    def __init__(self, text):
        ClipboardText.__init__(self, text, _("Clipboard Text"))

    def __repr__(self):
        return f"<{__name__} {self.qf_id}>"


class ClipboardUrl(UrlLeaf):
    def get_description(self):
        return _('Clipboard "%(desc)s"') % {"desc": self.object, "num": 1}


class ClipboardFile(FileLeaf):
    def get_description(self):
        return _('Clipboard "%(desc)s"') % {"desc": self.object, "num": 1}


class CurrentClipboardUrl(ClipboardUrl):
    qf_id = "clipboardtext"

    def __init__(self, text):
        super().__init__(text, _("Clipboard URL"))

    def __repr__(self):
        return f"<{__name__} {self.qf_id}>"


class CurrentClipboardFile(FileLeaf):
    "represents the *unique* current clipboard file"

    qf_id = "clipboardfile"

    def __init__(self, filepath):
        """@filepath is a filesystem byte string `str`"""
        FileLeaf.__init__(self, filepath, _("Clipboard File"))

    def __repr__(self):
        return f"<{__name__} {self.qf_id}>"


class CurrentClipboardFiles(MultipleLeaf):
    "represents the *unique* current clipboard if there are many files"

    qf_id = "clipboardfile"

    def __init__(self, paths):
        files = [FileLeaf(path) for path in paths]
        MultipleLeaf.__init__(self, files, _("Clipboard Files"))

    def __repr__(self):
        return f"<{__name__} {self.qf_id}>"


def _new_current_leaf(text: str | None) -> Leaf | None:
    if not text:
        return None

    if validators.is_url(text):
        return CurrentClipboardUrl(text)

    if validators.is_valid_file_path(text):
        path = Path(text).expanduser()
        with suppress(OSError):
            if path.exists():
                return CurrentClipboardFile(path)

    return CurrentClipboardText(text)


def _new_clipboard_leaf(text: str) -> Leaf:
    if validators.is_url(text):
        return ClipboardUrl(text, None)

    if validators.is_valid_file_path(text):
        with suppress(OSError, RuntimeError):
            path = Path(text).expanduser()
            if path.exists():
                return ClipboardFile(path)

    return ClipboardText(text)


class ClearClipboards(Action):
    def __init__(self):
        Action.__init__(self, _("Clear"))

    def activate(self, leaf, iobj=None, ctx=None):
        leaf.object.clear()

    def item_types(self):
        yield SourceLeaf

    def valid_for_item(self, leaf):
        return isinstance(leaf.object, ClipboardSource)

    def get_description(self):
        return _("Remove all recent clipboards")

    def get_icon_name(self):
        return "edit-clear"


class ClipboardSource(Source):
    source_scan_interval: int = 3600

    selected_text: str | None
    clipboard_uris: list[str]
    clipboard_text: str | None

    def __init__(self):
        Source.__init__(self, _("Clipboards"))
        self.clipboards: deque[str] = deque()

    # pylint: disable=attribute-defined-outside-init
    def initialize(self):
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self._sig_id1 = clip.connect(
            "owner-change", self._on_clipboard_changed
        )
        clip = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        self._sig_id2 = clip.connect(
            "owner-change", self._on_clipboard_changed
        )
        self.clipboard_uris = []
        self.clipboard_text = None
        self.selected_text = None

    def finalize(self):
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clip.disconnect(self._sig_id1)
        clip = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        clip.disconnect(self._sig_id2)
        self._sig_id1 = None
        self._sig_id2 = None
        self.clipboard_uris = []
        self.clipboard_text = None
        self.selected_text = None
        self.mark_for_update()

    def _on_clipboard_changed(self, clip, event, *args):
        is_selection = event.selection == Gdk.SELECTION_PRIMARY
        clip.request_text(self._on_text_for_change, is_selection)
        if not is_selection:
            clip.request_uris(self._on_uris_for_change)

    def _on_text_for_change(self, clip, text, is_selection):
        if text is None:
            return

        max_len = __kupfer_settings__["max"]
        is_valid = bool(text and text.strip())
        is_sync_selection = (
            is_selection and __kupfer_settings__["sync_selection"]
        )

        if (
            not is_selection or __kupfer_settings__["use_selection"]
        ) and is_valid:
            self._add_to_history(text, is_selection)

        if is_sync_selection and is_valid:
            Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(text, -1)

        if is_selection:
            self.selected_text = text

        if not is_selection or is_sync_selection:
            self.clipboard_text = text

        self._prune_to_length(max_len)
        self.mark_for_update()

    def _on_uris_for_change(self, clip, uris):
        self.clipboard_uris = uris if uris is not None else []
        self.mark_for_update()

    def _add_to_history(self, cliptext, is_selection):
        if cliptext in self.clipboards:
            self.clipboards.remove(cliptext)
        # if the previous text is a prefix of the new selection, supersede it
        if (
            is_selection
            and self.clipboards
            and (
                cliptext.startswith(self.clipboards[-1])
                or cliptext.endswith(self.clipboards[-1])
            )
        ):
            self.clipboards.pop()

        self.clipboards.append(cliptext)

    def _prune_to_length(self, max_len):
        while len(self.clipboards) > max_len:
            self.clipboards.popleft()

    def get_items(self):
        # selected text
        if leaf := _new_selected_leaf(self.selected_text):
            yield leaf

        # produce the current clipboard files if any
        paths: list[str] = list(
            filter(
                None,
                (
                    Gio.File.new_for_uri(uri).get_path()
                    for uri in self.clipboard_uris
                ),
            )
        )

        if len(paths) == 1:
            yield CurrentClipboardFile(paths[0])
        elif len(paths) > 1:
            yield CurrentClipboardFiles(paths)

        # put out the current clipboard text
        if leaf := _new_current_leaf(self.clipboard_text):
            yield leaf

        # put out the clipboard history
        yield from map(_new_clipboard_leaf, reversed(self.clipboards))

    def get_description(self):
        return __description__

    def get_icon_name(self):
        return "edit-paste"

    def provides(self):
        yield TextLeaf
        yield FileLeaf
        yield MultipleLeaf

    def clear(self):
        self.clipboards.clear()
        self.mark_for_update()
