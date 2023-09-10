from __future__ import annotations

__kupfer_name__ = _("Screenshot")
__kupfer_sources__ = ("ScreenshotTools",)
__kupfer_text_sources__ = ()
__kupfer_actions__ = ()
__description__ = _("Take screenshot of screen using Scrot or Flameshot.")
__version__ = "2023.1"
__author__ = "KB"

import os
import tempfile
from pathlib import Path
import typing as ty
import shutil

from gi.repository import Gtk, Gdk

from kupfer import runtimehelper, launch, icons, plugin_support
from kupfer.obj import FileLeaf, Source, OperationError, RunnableLeaf
from kupfer.obj.special import CommandNotAvailableLeaf

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "tool",
        "label": _("Tool:"),
        "type": str,
        "value": "scrot",
        "alternatives": [
            "Scrot",
            "Flameshot",
        ],
    },
    {
        "key": "format",
        "label": _("Format:"),
        "type": str,
        "value": "jpg",
        "alternatives": [
            "JPG",
            "PNG",
        ],
    },
)


def _tool_cmd_path(tool: str) -> str | None:
    if tool == "Flameshot":
        return shutil.which("flameshot")

    if tool == "Scrot":
        return shutil.which("scrot")

    return None


class ScreenshotToFile(RunnableLeaf):
    def __init__(self, name=_("Take Screenshot To File")):
        super().__init__(name=name)

    def has_result(self):
        return True

    def wants_context(self):
        return True

    def run(self, ctx=None):
        assert ctx

        ext = __kupfer_settings__["format"].lower()

        # take temp file name
        file, path = tempfile.mkstemp(f".{ext}", prefix="screenshot")
        os.close(file)
        # file must be deleted
        Path(path).unlink()

        runtimehelper.register_async_file_result(ctx, path)

        tool = __kupfer_settings__["tool"]
        cmd = _tool_cmd_path(tool)
        if not cmd:
            return CommandNotAvailableLeaf(__name__, __kupfer_name__, tool)

        argv: tuple[str, ...]

        if tool == "Flameshot":
            argv = ("flameshot", "gui", "--path", path, "--delay", "1000")
        elif tool == "scrot":
            argv = ("scrot", "--file", path, "--delay", "1")
        else:
            return None

        try:
            launch.spawn_async_raise(argv)
        except launch.SpawnError as exc:
            raise OperationError(exc.args[0].message) from exc

        return FileLeaf(path)

    def item_types(self):
        yield FileLeaf

    def get_gicon(self):
        return icons.ComposedIcon(
            "video-display", "document-save", minimum_icon_size=16
        )


class _SSToClipboardNative(RunnableLeaf):
    """Take screenshot and put image to the clipboard using native method
    provided by tool."""

    def __init__(self, name=_("Take Screenshot to the Clipboard")):
        super().__init__(name=name)

    def wants_context(self):
        return True

    def run(self, ctx=None):
        assert ctx

        argv = ("flameshot", "gui", "--clipboard")

        try:
            launch.spawn_async_raise(argv)
        except launch.SpawnError as exc:
            raise OperationError(exc.args[0].message) from exc

    def get_gicon(self):
        return icons.ComposedIcon(
            "video-display", "document-save", minimum_icon_size=16
        )


class SSToClipboard(RunnableLeaf):
    """Take screenshot and put image to the clipboard for tools that not
    provided clipboard support. Take screenshot to file, read image from file and
    put it in the clipboard."""

    def __init__(self, name=_("Take Screenshot to the Clipboard")):
        super().__init__(name=name)

    def wants_context(self):
        return True

    def run(self, ctx=None):
        assert ctx

        # take temp file name
        file, path = tempfile.mkstemp(".png", prefix="screenshot")
        os.close(file)

        # for now only scrot
        argv = ["scrot", "--file", path, "--delay", "1", "--overwrite"]

        def finish_callback(acommand, stdout, stderr):
            if not acommand.exit_status:
                if pixbuf := icons.get_pixbuf_from_file(path):
                    clip = Gtk.Clipboard.get_default(Gdk.Display.get_default())
                    clip.set_image(pixbuf)

            Path(path).unlink()

        launch.AsyncCommand(argv, finish_callback, 10)

    def get_gicon(self):
        return icons.ComposedIcon(
            "video-display", "document-save", minimum_icon_size=16
        )


class ScreenshotTools(Source):
    serializable = None

    def __init__(self, name=_("Screenshot tools")):
        super().__init__(name)

    def is_dynamic(self):
        return True

    def get_items(self):
        yield ScreenshotToFile()
        tool = __kupfer_settings__["tool"]
        if not _tool_cmd_path(tool):
            yield CommandNotAvailableLeaf(__name__, __kupfer_name__, tool)
            return

        if tool == "Flameshot":
            yield _SSToClipboardNative()
        elif tool == "Scrot":
            yield SSToClipboard()

    def provides(self):
        yield RunnableLeaf

    def get_gicon(self):
        return icons.ComposedIcon(
            "video-display", "document-save", minimum_icon_size=16
        )
