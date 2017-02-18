# -*- coding: UTF-8 -*-


__kupfer_name__ = _("Top")
__kupfer_sources__ = ("TaskSource", )
__description__ = _("Show running tasks and allow sending signals to them")
__version__ = "2009-11-24"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
import signal
import operator

from kupfer.objects import Action, Source, Leaf
from kupfer import scheduler
from kupfer import plugin_support
from kupfer import utils

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "sort_order",
        "label": _("Sort Order"),
        "type": str,
        "value": _("Commandline"),
        "alternatives": [_("Commandline"), _("CPU usage (descending)"),
                _("Memory usage (descending)") ]
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
        return 'applications-system'


class SendSignal(Action):
    def __init__(self):
        Action.__init__(self, _("Send Signal..."))

    def activate(self, leaf, iobj):
        os.kill(leaf.object, iobj.object)

    def requires_object(self):
        return True
    
    def object_types(self):
        yield _Signal

    def object_source(self, for_item=None):
        return _SignalsSource()


class _Signal(Leaf):
    def get_description(self):
        return "kill -%s ..." % self.object


# get all signals from signal package
_SIGNALS = [
    _Signal(getattr(signal, signame), signame[3:])
    for signame in sorted(dir(signal))
    if signame.startswith('SIG') and not signame.startswith('SIG_')
]


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

    def __init__(self, name=_("Running Tasks")):
        Source.__init__(self, name)
        self._cache = []
        self._version = 2

    def initialize(self):
        self._timer = scheduler.Timer()

    def finalize(self):
        self._timer = None
        self._cache = []

    def _async_top_finished(self, acommand, stdout, stderr):
        self._cache = []

        processes = parse_top_output(stdout)
        # sort processes (top don't allow to sort via cmd line)
        if __kupfer_settings__['sort_order'] == _("Memory usage (descending)"):
            processes = sorted(processes, key=operator.itemgetter(2),
                               reverse=True)
        elif __kupfer_settings__['sort_order'] == _("Commandline"):
            processes = sorted(processes, key=operator.itemgetter(4))
        # default: by cpu

        fields = _("pid: %(pid)s  cpu: %(cpu)g%%  mem: %(mem)g%%  time: %(time)s")
        for pid, cpu, mem, ptime, cmd in processes:
            description = fields % dict(pid=pid, cpu=cpu, mem=mem, time=ptime)
            self._cache.append(Task(pid, cmd, description))

        self.mark_for_update()

    def _async_top_start(self):
        uid = os.getuid()
        utils.AsyncCommand(["top", "-b", "-n", "1", "-u", "%d" % uid],
                           self._async_top_finished, 60, env=["LC_NUMERIC=C"])

    def get_items(self):
        for task in self._cache:
            yield task
        update_wait = self.task_update_interval_sec if self._cache else 0
        # update after a few seconds
        self._timer.set(update_wait, self._async_top_start)

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
    fields_map = None
    fields_count = 0
    header_read = False
    for line in out.split(b'\n'):
        line = line.decode("utf-8", "replace").strip()
        if line == '':
            header_read = True
            continue

        if not header_read:
            continue

        if line.startswith('PID'): # assume pid is first col
            fields_map = dict(((name, pos) for pos, name in enumerate(line.split())))
            fields_count = len(fields_map)
            continue    # skip header

        line_fields = line.split(None, fields_count-1)
        pid = line_fields[0]
        cpu = line_fields[fields_map['%CPU']]
        mem = line_fields[fields_map['%MEM']]
        ptime = line_fields[fields_map['TIME+']]
        cmd = line_fields[-1]

        # read command line
        proc_file = '/proc/%s/cmdline' % pid
        if os.path.isfile(proc_file): # also skip (finished) missing tasks
            with open(proc_file, 'rt') as f:
                cmd = f.readline().replace('\x00', ' ') or cmd

            yield (int(pid), float(cpu), float(mem), ptime, cmd)

