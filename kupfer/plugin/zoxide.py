"""
Load directories from zoxide (https://github.com/ajeetdsouza/zoxide)
with configured, minimal score.

Optionally, some directories can be excluded (by path) and only existing
files may be presented (this may slowdown loading when turned on).
"""

__kupfer_name__ = _("Zoxide Directories")
__kupfer_sources__ = ("ZoxideDirSource",)
__description__ = _("Load top directories from zoxide database")
__version__ = "2023-04-02"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import subprocess
import typing as ty
import os.path

from kupfer import config, plugin_support, icons
from kupfer.obj import FileLeaf, Source, Action, Leaf
from kupfer.obj import fileactions
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.core.datactrl import DataController

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "exclude",
        "label": _("Exclude directories:"),
        "type": list,
        "value": [],
        "helper": "choose_directory",
    },
    {
        "key": "min_score",
        "label": _("Minimal score:"),
        "type": int,
        "value": 1,
        "min": 1,
        "tooltip": _(
            "Load only directories that score is equal "
            "or higher than configured minimum"
        ),
    },
    {
        "key": "max_items",
        "label": _("Load limit:"),
        "type": int,
        "value": 50,
        "min": 1,
        "tooltip": _("Maximal number of directories to load"),
    },
    {
        "key": "existing",
        "label": _("Show only existing directories"),
        "type": bool,
        "value": True,
    },
    {
        "key": "record_enabled",
        "label": _("Update database after activate"),
        "type": bool,
        "value": False,
        "tooltip": _(
            "When enabled open files and directories will update zoxide database"
        ),
    },
)

if ty.TYPE_CHECKING:
    _ = str


class LaunchRecorder:
    def __init__(self):
        self._enabled = False
        self._cb_pointer = None

    def connect(self):
        data_controller = DataController.instance()
        self._cb_pointer = data_controller.connect(
            "launched-action", self._launch_callback
        )
        __kupfer_settings__.connect(
            "plugin-setting-changed", self._setting_changed
        )
        self._enabled = __kupfer_settings__["record_enabled"]

    def disconnect(self):
        if self._cb_pointer:
            data_controller = DataController.instance()
            data_controller.disconnect(self._cb_pointer)
            self._cb_pointer = None

    def _launch_callback(
        self, sender: ty.Any, leaf: Leaf, action: Action, *_args: ty.Any
    ) -> None:
        if not self._enabled:
            return

        if not isinstance(leaf, FileLeaf):
            return

        if not isinstance(action, fileactions.Open):
            return

        path = leaf.object
        if not leaf.is_dir():
            path = os.path.dirname(path)

        # check is path is excluded
        if any(map(path.startswith, __kupfer_settings__["exclude"])):
            return

        subprocess.run(["zoxide", "add", path])

    def _setting_changed(self, settings, key, value):
        if key == "record_enabled":
            self._enabled = bool(value)


_RECORDER = LaunchRecorder()


def initialize_plugin(plugin_name: str) -> None:
    _RECORDER.connect()


def finalize_plugin(plugin_name: str) -> None:
    _RECORDER.disconnect()


def _get_dirs(
    exclude: list[str], min_score: int, existing: bool, max_items: int
) -> ty.Iterator[str]:
    cmd = ["zoxide", "query", "--list", "--score"]
    if not existing:
        cmd.append("--all")

    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
        stdout, _stderr = proc.communicate()
        for rownum, line in enumerate(stdout.splitlines()):
            if rownum > max_items:
                return

            line = line.strip()
            score, _dummy, dirpath = line.partition(b" ")
            if not dirpath:
                continue

            if float(score) < min_score:
                return

            path = dirpath.decode()
            # zoxide query not support multiple --exclude; so filter it here
            if any(map(path.startswith, exclude)):
                continue

            yield path


class ZoxideDirSource(Source, FilesystemWatchMixin):
    def __init__(self):
        super().__init__(name=_("Zoxide Directories"))
        self.monitor = None

    def initialize(self):
        zoxide_home = config.get_data_dirs("", "zoxide")
        self.monitor = self.monitor_directories(*zoxide_home)
        __kupfer_settings__.connect(
            "plugin-setting-changed", self._setting_changed
        )

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == "zo.db"

    def get_items(self):
        for dirname in _get_dirs(
            __kupfer_settings__["exclude"],
            __kupfer_settings__["min_score"],
            __kupfer_settings__["existing"],
            __kupfer_settings__["max_items"],
        ):
            yield FileLeaf(dirname)

    def _setting_changed(self, settings, key, value):
        if key in ("exclude", "min_score"):
            self.mark_for_update()

    def get_gicon(self):
        return icons.ComposedIconSmall("folder", "emblem-favorite")
