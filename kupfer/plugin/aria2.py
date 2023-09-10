from __future__ import annotations

__kupfer_name__ = _("Aria2")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = ("Download",)
__description__ = _("Download files using remote instance of Aria2")
__version__ = "2023-05-14"
__author__ = "KB"

import urllib.request
import json
import time
import typing as ty

from kupfer import plugin_support
from kupfer.obj import Action, UrlLeaf, OperationError
from kupfer.ui import uiutils

if ty.TYPE_CHECKING:
    from gettext import gettext as _


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "aria2_url",
        "label": _("Aria2 URL"),
        "type": str,
        "value": "",
        "tooltip": _(
            "Base URL for remote Aria2 instance ie. http://localhost:6800/"
        ),
    },
    {
        "key": "aria2_token",
        "label": _("Secret token"),
        "type": str,
        "value": "",
        "tooltip": _(
            "Enter the Aria2 RPC secret token (leave empty if "
            "authentication is not enabled) "
        ),
    },
)


class Download(Action):
    """Action to download file"""

    def __init__(self):
        Action.__init__(self, _("Remote Download"))

    def activate(self, leaf, iobj=None, ctx=None):
        aria2url = __kupfer_settings__["aria2_url"]
        if not aria2url:
            return

        params: list[str | list[str]] = []

        if token := __kupfer_settings__["aria2_token"]:
            params.append(f"token:{token}")

        params.append([str(leaf.object)])

        jsonreq = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": f"kupfer-{time.time()}",
                "method": "aria2.addUri",
                "params": params,
            }
        )

        data = jsonreq.encode("ascii")

        with urllib.request.urlopen(aria2url, data) as response:
            if response.status == 200:
                uiutils.show_notification("Kupfer", _("Download started"))
                return

            if res := response.read():
                err = res.decode()
            else:
                err = str(response.status)

            raise OperationError(f"Request failed: {err}")

    def item_types(self):
        yield UrlLeaf

    def get_description(self):
        return _("Download using remote instance of Aria2")
