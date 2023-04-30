#! /usr/bin/env python3
"""
Plugin generate recent opened files for vim/gvim.
"""
from __future__ import annotations

__kupfer_name__ = _("Vim")
__kupfer_sources__ = ("VimRecentsSource", "VimWikiSource")
__description__ = _("Load recent files edited in VIM/GVIM")
__version__ = "2023-04-02"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
import typing as ty
from pathlib import Path

from gi.repository import Gio

from kupfer import plugin_support, launch, icons
from kupfer.obj import FileLeaf, Source, SourceLeaf, Action
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin, FileMonitorToken
from kupfer.support.datatools import simple_cache

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "wikis",
        "label": _("VimWiki directories:"),
        "type": list,
        "value": [],
        "helper": "choose_directory",
    },
    {
        "key": "limit",
        "label": _("Max recent documents:"),
        "type": int,
        "value": 25,
        "min": 1,
        "max": 100,
    },
)


@simple_cache
def _load_recent_files(viminfo: Path, limit: int, stamp: float) -> list[Path]:
    # stamp is file modification timestamp used to evict old cache items
    files = []
    with viminfo.open("rt", encoding="UTF-8", errors="replace") as fin:
        for line in fin:
            if not line.startswith("> "):
                continue

            if filepath := line[2:].strip():
                files.append(Path(filepath).expanduser())
                limit -= 1
                if not limit:
                    break

    return files


class VimRecentsSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = ("vim", "gvim")
    source_scan_interval: int = 3600

    def __init__(self, name=None):
        super().__init__(name=_("Vim Recent Documents"))
        self._monitor_token: FileMonitorToken | None = None
        self._viminfo = Path("~/.viminfo").expanduser()

    def initialize(self):
        self._monitor_token = self.monitor_files(self._viminfo)

    def finalize(self):
        self.stop_monitor_fs_changes(self._monitor_token)

    def monitor_include_file(self, gfile: Gio.File) -> bool:
        return bool(gfile) and gfile.get_basename() == ".viminfo"

    def get_items_forced(self):
        try:
            _load_recent_files.cache_clear()
        except AttributeError:
            _load_recent_files.__wrapped__.cache_clear()  # type:ignore

        return self.get_items()

    def get_items(self):
        viminfo = self._viminfo
        if not viminfo.exists():
            self.output_debug("Viminfo not found at", viminfo)
            return ()

        limit = __kupfer_settings__["limit"]
        try:
            return map(
                FileLeaf,
                _load_recent_files(viminfo, limit, viminfo.stat().st_mtime),
            )
        except OSError:
            self.output_exc()

        return ()

    def get_icon_name(self):
        return "document-open-recent"

    def provides(self):
        yield FileLeaf


class VimWikiFile(FileLeaf):
    def __init__(self, path: Path, name: str) -> None:
        super().__init__(path, name)

    def get_actions(self):
        yield OpenVimWiki()


class VimWiki(SourceLeaf):
    def __init__(self, source: VimWikiFilesSource, name: str) -> None:
        super().__init__(source, name)

    def get_gicon(self):
        return icons.ComposedIconSmall("gvim", "emblem-documents")

    def get_description(self):
        return _("VimWiki in %s") % self.object.wikipath


class VimWikiSource(Source):
    def __init__(self):
        super().__init__(name=_("VimWiki Wikis"))

    def get_items(self):
        existing_wiki = []
        for path in __kupfer_settings__["wikis"] or ():
            filepath = Path(path).expanduser().resolve()
            if filepath.is_dir():
                name = filepath.name
                # make names unique (simple and not perfect)
                if name in existing_wiki:
                    name = f"{name} ({filepath.parent.name})"

                existing_wiki.append(name)
                yield VimWiki(VimWikiFilesSource(filepath), name)

    def provides(self):
        yield VimWiki

    def get_gicon(self):
        return icons.ComposedIconSmall("gvim", "emblem-documents")


class VimWikiFilesSource(Source, FilesystemWatchMixin):
    source_scan_interval: int = 3600

    def __init__(self, wikipath: Path) -> None:
        super().__init__(wikipath.name)
        self.wikipath = wikipath
        self._viminfo = Path("~/.viminfo").expanduser()
        self._monitor_token: FileMonitorToken | None = None

    def initialize(self):
        self._monitor_token = self.monitor_files(self._viminfo)

    def finalize(self):
        self.stop_monitor_fs_changes(self._monitor_token)

    def monitor_include_file(self, gfile: Gio.File) -> bool:
        if not gfile or gfile.get_basename() != ".viminfo":
            return False

        viminfo = self._viminfo
        if not viminfo.exists():
            return False

        # check is last modified files in vim belong do this wiki
        limit = __kupfer_settings__["limit"]
        for fname in _load_recent_files(
            viminfo, limit, viminfo.stat().st_mtime
        ):
            if fname.is_relative_to(self.wikipath):
                return True

        return False

    def repr_key(self) -> str:
        return str(self.wikipath)

    def get_items(self) -> ty.Iterable[VimWikiFile]:
        # wiki can keep various files (txt, md, etc). Instead of read index
        # and guess extension - load add files in wiki
        wikipath = self.wikipath
        for dirname, dirs, files in os.walk(wikipath):
            dirp = Path(dirname)
            # skip hidden directories
            if dirp.name[0] == ".":
                dirs.clear()
                continue

            for file in files:
                # skip hidden files
                if file[0] == ".":
                    continue

                filepath = dirp.joinpath(file)
                yield VimWikiFile(filepath, str(filepath.relative_to(wikipath)))

    def provides(self):
        yield VimWikiFile

    def should_sort_lexically(self):
        return True


class OpenVimWiki(Action):
    rank_adjust = 20

    def __init__(self):
        super().__init__(name=_("Open in GVim"))

    def activate(self, leaf, iobj=None, ctx=None):
        launch.spawn_async(["gvim", leaf.object])

    def get_icon_name(self) -> str:
        return "gvim"
