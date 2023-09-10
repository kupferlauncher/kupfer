from __future__ import annotations

__kupfer_name__ = _("URL Actions")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = ("DownloadAndOpen", "DownloadTo")
__description__ = _("URL Actions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
import shutil
import typing as ty
import urllib.error
import urllib.parse
import urllib.request
import http.client

from kupfer import launch
from kupfer.obj import Action, FileLeaf, UrlLeaf
from kupfer.support import fileutils, task

if ty.TYPE_CHECKING:
    from gettext import gettext as _


def get_dest_name(response: http.client.HTTPResponse) -> str:
    headers = response.headers

    # try get filename from content-disposition header
    content_disp = headers.get("Content-Disposition", "")
    for part in content_disp.split(";"):
        key, _sep, val = part.strip().partition("=")
        if key.lower() == "filename":
            return val

    name = "index"
    # try get filename from url
    url = urllib.parse.urlparse(response.url)  # type: ignore
    if url.path not in ("", "/"):
        name = os.path.basename(url.path.rstrip("/"))
        # if name have extension - return it
        if os.path.splitext(name)[1]:
            return name

    # if name not contain extension, try guess it from content-type.
    # only basic types
    content_type = headers.get("Content-Type", "")
    content_type = content_type.split(";", 1)[0].strip()
    if content_type == "text/html":
        return f"{name}.html"

    if content_type == "text/plain":
        return f"{name}.txt"

    return name


class DownloadTask(task.ThreadTask):
    def __init__(self, uri, destdir=None, tempfile=False, finish_callback=None):
        super().__init__()
        self.uri = uri
        self.download_finish_callback = finish_callback
        self.destdir = destdir
        self.use_tempfile = tempfile
        self.destpath = None

    def _get_dst_file(
        self, destname: str
    ) -> tuple[ty.BinaryIO | None, str | None]:
        if self.use_tempfile:
            return fileutils.get_safe_tempfile()

        return fileutils.get_destfile_in_directory(self.destdir, destname)

    def thread_do(self):
        with urllib.request.urlopen(self.uri) as response:
            if response.status >= 300 or response.status < 200:
                raise RuntimeError(
                    f"Could not download file; status: {response.status}"
                )

            destname = get_dest_name(response)
            destfile, self.destpath = self._get_dst_file(destname)
            if not destfile:
                raise OSError("Could not write output file")

            try:
                shutil.copyfileobj(response, destfile)
            finally:
                destfile.close()

    def thread_finish(self):
        if self.download_finish_callback:
            self.download_finish_callback(self.destpath)


class DownloadAndOpen(Action):
    """Asynchronous action to download file and open it"""

    def __init__(self):
        Action.__init__(self, _("Download and Open"))

    def is_async(self):
        return True

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx

        def finish_action(filename):
            launch.show_path(filename)
            ctx.register_late_result(FileLeaf(filename), show=False)

        uri = leaf.object
        return DownloadTask(uri, None, True, finish_action)

    def item_types(self):
        yield UrlLeaf

    def get_description(self):
        return None


class DownloadTo(Action):
    def __init__(self):
        Action.__init__(self, _("Download To..."))

    def is_async(self):
        return True

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        assert iobj

        def finish_action(filename):
            ctx.register_late_result(FileLeaf(filename))

        uri = leaf.object
        return DownloadTask(uri, iobj.object, False, finish_action)

    def item_types(self):
        yield UrlLeaf

    def requires_object(self):
        return True

    def object_types(self):
        yield FileLeaf

    def valid_object(self, obj, for_item=None):
        return fileutils.is_directory_writable(obj.object)

    def get_description(self):
        return _("Download URL to a chosen location")
