__kupfer_name__ = _("Top")
__kupfer_sources__ = ("TaskSource",)
__description__ = _("Show running tasks and allow sending signals to them")
__version__ = "2023-04-29"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import operator
import os
import signal
from pathlib import Path
import subprocess
import typing as ty

from kupfer import plugin_support
from kupfer.obj import Action, Leaf, Source

if ty.TYPE_CHECKING:
    from gettext import gettext as _


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "sort_order",
        "label": _("Sort Order"),
        "type": str,
        "value": _("Commandline"),
        "alternatives": [
            _("Commandline"),
            _("CPU usage (descending)"),
            _("Memory usage (descending)"),
        ],
    },
)


class Task(Leaf):
    def __init__(self, path, name, description=None):
        Leaf.__init__(self, path, name)
        self._description = description

    def get_description(self):
        return self._description

    def get_actions(self):
        yield SendSignal()

    def get_icon_name(self):
        return "applications-system"


class SendSignal(Action):
    def __init__(self):
        Action.__init__(self, _("Send Signal..."))

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        os.kill(leaf.object, iobj.object)

    def requires_object(self):
        return True

    def object_types(self):
        yield _Signal

    def object_source(self, for_item=None):
        return _SignalsSource()


class _Signal(Leaf):
    def get_description(self):
        return f"kill -{self.object} ..."


# get all signals from signal package
_SIGNALS = tuple(
    _Signal(getattr(signal, signame), signame[3:])
    for signame in sorted(dir(signal))
    if signame.startswith("SIG") and not signame.startswith("SIG_")
)


class _SignalsSource(Source):
    def __init__(self):
        Source.__init__(self, _("Signals"))

    def get_items(self):
        return _SIGNALS

    def provides(self):
        yield _Signal


class TaskSource(Source):
    task_update_interval_sec = 5
    source_use_cache = False
    source_prefer_sublevel = True

    def __init__(self, name=_("Running Tasks")):
        Source.__init__(self, name)
        self._version = 3

    def is_dynamic(self):
        return True

    def get_items(self):
        uid = os.getuid()
        with subprocess.Popen(
            ["top", "-b", "-n", "1", "-u", str(uid)],
            stdout=subprocess.PIPE,
            env={"LC_NUMERIC": "C"},
        ) as proc:
            if proc.stdout:
                content = proc.stdout.read()
            else:
                return

        processes = parse_top_output(content)
        sort_order = __kupfer_settings__["sort_order"]
        if sort_order == _("Memory usage (descending)"):
            processes = sorted(
                processes, key=operator.itemgetter(2), reverse=True
            )
        elif sort_order == _("Commandline"):
            processes = sorted(processes, key=operator.itemgetter(4))
        # default: by cpu

        fields = _(
            "pid: %(pid)s  cpu: %(cpu)g%%  mem: %(mem)g%%  time: %(time)s"
        )
        for pid, cpu, mem, ptime, cmd in processes:
            description = fields % {
                "pid": pid,
                "cpu": cpu,
                "mem": mem,
                "time": ptime,
            }
            yield Task(pid, cmd, description)

    def get_description(self):
        return _("Running tasks for current user")

    def get_icon_name(self):
        return "system"

    def provides(self):
        yield Task


def parse_top_output(out):
    """
    Yield tuples of (pid, cpu, mem, ptime, cmd)
    """
    # Assuming UTF-8 output
    fields_map = {}
    fields_count = 0
    header_read = False
    for line in out.split(b"\n"):
        line = line.decode("utf-8", "replace").strip()
        if line == "":
            header_read = True
            continue

        if not header_read:
            continue

        if line.startswith("PID"):  # assume pid is first col
            fields_map = {name: pos for pos, name in enumerate(line.split())}
            fields_count = len(fields_map)
            continue  # skip header

        line_fields = line.split(None, fields_count - 1)
        pid = line_fields[0]
        cpu = line_fields[fields_map["%CPU"]]
        mem = line_fields[fields_map["%MEM"]]
        ptime = line_fields[fields_map["TIME+"]]
        cmd = line_fields[-1]

        # read command line
        proc_file = Path(f"/proc/{pid}/cmdline")
        if proc_file.is_file():  # also skip (finished) missing tasks
            cmd = proc_file.read_text(encoding="UTF=8").replace("\x00", " ")
            yield (int(pid), float(cpu), float(mem), ptime, cmd)
