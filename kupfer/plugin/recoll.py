from __future__ import annotations

__kupfer_name__ = _("Recoll")
__kupfer_actions__ = ("Recoll", "OpenInRecoll")
__description__ = _("Search in Recoll full text search system")
__version__ = ""
__author__ = "KB"

import base64
import shutil
import subprocess
import typing as ty

from gi.repository import Gio

from kupfer import launch, plugin_support
from kupfer.obj import Action, FileLeaf, OperationError, Source, TextLeaf
from kupfer.obj.special import CommandNotAvailableLeaf

if ty.TYPE_CHECKING:
    from gettext import gettext as _

plugin_support.check_command_available("recoll")


class RecollLeaf(FileLeaf):
    def __init__(self, fpath: str, title: str, mtype: str):
        super().__init__(fpath)
        self._title = title
        self._mtype = mtype
        if title != fpath:
            self.kupfer_add_alias(title)

    def get_description(self) -> str | None:
        return self._title

    def get_content_type(self) -> str | None:
        return self._mtype or super().get_content_type()


class Recoll(Action):
    rank_adjust: int = -5

    def __init__(self):
        Action.__init__(self, _("Search in Recoll"))

    def is_factory(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        return RecollQuerySource(leaf.object)

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Search for text in Recoll database")

    def get_icon_name(self):
        return "find"


class OpenInRecoll(Action):
    rank_adjust: int = -4

    def __init__(self):
        Action.__init__(self, _("Open in Recoll"))

    def activate(self, leaf, iobj=None, ctx=None):
        try:
            launch.spawn_async_raise(["recoll", "-q", str(leaf)])
        except launch.SpawnError as exc:
            raise OperationError(exc) from exc

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Open Recoll and search for text")

    def get_icon_name(self):
        return "find"


class RecollQuerySource(Source):
    def __init__(self, query):
        Source.__init__(self, name=_('Results for "%s"') % query)
        self._query = query.strip()
        self._max_items = 100

    def repr_key(self):
        return f"recoll_query:{self._query}"

    def get_items(self):
        recoll_cmd = shutil.which("recoll")
        if not recoll_cmd:
            yield CommandNotAvailableLeaf(__name__, __kupfer_name__, "recoll")
            return

        if not self._query:
            return

        command = [
            recoll_cmd,
            "-t",
            "-n",
            str(self._max_items),
            "-F",
            "url filename title mtype",
            "-S",
            "relevancyrating",
            "-D",
            self._query,
        ]

        with subprocess.Popen(command, stdout=subprocess.PIPE) as proc:
            out, _error = proc.communicate()
            for line in out.splitlines():
                if line.startswith(b"Recoll") or b"results" in line:
                    continue

                uri, filename, title, mtype, *_dummy = tuple(
                    base64.b64decode(v).decode() for v in line.split(b" ")
                )

                try:
                    gfile = Gio.File.new_for_uri(uri)
                    fpath = gfile.get_path()
                    yield RecollLeaf(fpath, title or filename, mtype)
                except OSError:
                    pass

    def has_parent(self) -> bool:
        return False
