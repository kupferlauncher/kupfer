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

import os.path
import subprocess
import typing as ty

from kupfer import config, icons, plugin_support
from kupfer.core.datactrl import DataController
from kupfer.obj import Action, FileLeaf, Leaf, Source, fileactions
from kupfer.obj.helplib import FilesystemWatchMixin

if ty.TYPE_CHECKING:
    from gettext import gettext as _


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

plugin_support.check_command_available("zoxide")


class LaunchRecorder:
    """Launch recorder listen for 'launched-action' signals after Open  action on
    FileLeaves and update zoxide about access to file folder."""

    def __init__(self):
        self._enabled = False
        self._cb_pointer = None

    def connect(self):
        data_controller = DataController.instance()
        self._cb_pointer = data_controller.connect(
            "launched-action", self._on_launched_action
        )
        __kupfer_settings__.connect(
            "plugin-setting-changed", self._on_setting_changed
        )
        self._enabled = __kupfer_settings__["record_enabled"]

    def disconnect(self):
        if self._cb_pointer:
            data_controller = DataController.instance()
            data_controller.disconnect(self._cb_pointer)
            self._cb_pointer = None

    def _on_launched_action(
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

        subprocess.run(["zoxide", "add", path], check=False)

    def _on_setting_changed(self, settings, key, value):
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
    """Load folders with score from zoxide."""
    cmd = ["zoxide", "query", "--list", "--score"]
    if not existing:
        cmd.append("--all")

    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
        stdout, _stderr = proc.communicate()
        lines = stdout.splitlines()

    for rownum, line in enumerate(lines):
        if rownum > max_items:
            return

        line = line.strip()  # noqa: PLW2901
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
    source_scan_interval: int = 3600
    rank_adjust = 20

    def __init__(self):
        super().__init__(name=_("Zoxide Directories"))
        self.monitor = None

    def initialize(self):
        zoxide_home = config.get_data_dirs("", "zoxide")
        self.monitor = self.monitor_directories(*zoxide_home)
        __kupfer_settings__.connect(
            "plugin-setting-changed", self._on_setting_changed
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

    def _on_setting_changed(self, settings, key, value):
        if key in ("exclude", "min_score"):
            self.mark_for_update()

    def get_gicon(self):
        return icons.ComposedIconSmall("folder", "emblem-favorite")
