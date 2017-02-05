__kupfer_name__ = _("URL Actions")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
        "DownloadAndOpen",
        "DownloadTo",
    )
__description__ = _("URL Actions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
import shutil
import urllib.request, urllib.parse, urllib.error

from kupfer.objects import Action, UrlLeaf, FileLeaf
from kupfer import utils, task

class DownloadTask (task.ThreadTask):
    def __init__(self, uri, destdir=None, tempfile=False, finish_callback=None):
        super(DownloadTask, self).__init__()
        self.uri = uri
        self.download_finish_callback = finish_callback
        self.destdir = destdir
        self.use_tempfile = tempfile

    def thread_do(self):
        self.response = urllib.request.urlopen(self.uri)

        def url_name(url):
            return os.path.basename(url.rstrip("/"))
        def header_name(headers):
            content_disp = headers.get("Content-Disposition", "")
            for part in content_disp.split(";"):
                if part.strip().lower().startswith("filename="):
                    return part.split("=", 1)[-1]
            return content_disp

        destname = (header_name(self.response.headers) or
                    url_name(self.response.url))

        if self.use_tempfile:
            (self.destfile, self.destpath) = utils.get_safe_tempfile()
        else:
            (self.destfile, self.destpath) = \
                utils.get_destfile_in_directory(self.destdir, destname)
        try:
            if not self.destfile:
                raise IOError("Could not write output file")

            shutil.copyfileobj(self.response, self.destfile)
        finally:
            self.destfile.close()
            self.response.close()

    def thread_finish(self):
        if self.download_finish_callback:
            self.download_finish_callback(self.destpath)

class DownloadAndOpen (Action):
    """Asynchronous action to download file and open it"""
    def __init__(self):
        Action.__init__(self, _("Download and Open"))

    def is_async(self):
        return True
    def wants_context(self):
        return True
    def activate(self, leaf, ctx):
        uri = leaf.object
        def finish_action(filename):
            utils.show_path(filename)
            ctx.register_late_result(FileLeaf(filename), show=False)
        return DownloadTask(uri, None, True, finish_action)

    def item_types(self):
        yield UrlLeaf
    def get_description(self):
        return None

class DownloadTo (Action):
    def __init__(self):
        Action.__init__(self, _("Download To..."))

    def is_async(self):
        return True
    def wants_context(self):
        return True
    def activate(self, leaf, obj, ctx):
        uri = leaf.object
        def finish_action(filename):
            ctx.register_late_result(FileLeaf(filename))
        return DownloadTask(uri, obj.object, False, finish_action)

    def item_types(self):
        yield UrlLeaf
    def requires_object(self):
        return True
    def object_types(self):
        yield FileLeaf
    def valid_object(self, obj, for_item=None):
        return utils.is_directory_writable(obj.object)
    def get_description(self):
        return _("Download URL to a chosen location")

