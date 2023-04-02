#! /usr/bin/env python3
"""
Plugin generate recent opened files for vim/gvim.
"""
__kupfer_name__ = _("Vim")
__kupfer_sources__ = ("VimRecentsSource",)
__description__ = _("Load recent files edited in VIM/GVIM")
__version__ = "2023-04-02"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import typing as ty
from pathlib import Path

from gi.repository import Gio

from kupfer.obj import FileLeaf, Source
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin


def _load_recent_files(viminfo: Path) -> ty.Iterable[FileLeaf]:
    with viminfo.open("rt", encoding="UTF-8", errors="replace") as fin:
        for line in fin:
            if not line.startswith("> "):
                continue

            *_dummy, filepath = line.strip().partition(" ")
            if filepath:
                yield FileLeaf(Path(filepath).expanduser())


class VimRecentsSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = ("vim", "gvim")

    _viminfo_file = "~/.viminfo"

    def __init__(self, name=None):
        super().__init__(name=_("Vim Recent Documents"))

    def initialize(self):
        viminfo = Path(self._viminfo_file).expanduser()
        self.monitor_token = self.monitor_files(viminfo)

    def finalize(self):
        self.stop_monitor_fs_changes(self.monitor_token)

    def monitor_include_file(self, gfile: Gio.File) -> bool:
        return bool(gfile)

    def get_items(self):
        viminfo = Path(self._viminfo_file).expanduser()
        if not viminfo.exists():
            self.output_debug("Viminfo not found at", viminfo)
            return

        try:
            yield from _load_recent_files(viminfo)
        except EnvironmentError:
            self.output_exc()
            return

    def get_icon_name(self):
        return "document-open-recent"

    def provides(self):
        yield FileLeaf
