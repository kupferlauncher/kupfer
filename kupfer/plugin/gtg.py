__kupfer_name__ = _("Getting Things GNOME")
__kupfer_sources__ = ("TasksSource", )
__kupfer_actions__ = ("CreateNewTask", "CreateNewEmptyTask")
__description__ = _("Browse and create new tasks in GTG")
__version__ = "2017.2"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>, US"

'''
Changes:
    2012-06-21 Karol Będkowski:
        * support new dbus api introduced in GTG 0.2.9
'''

import os

import dbus

from kupfer import plugin_support
from kupfer import pretty
from kupfer import textutils
from kupfer.objects import Leaf, Action, Source
from kupfer.objects import TextLeaf, NotAvailableError, AppLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.weaklib import dbus_signal_connect_weakly

plugin_support.check_dbus_connection()

GTG_ID = "gtg"
_SERVICE_NAME2 = 'org.gnome.GTG'
_OBJECT_NAME2 = '/org/gnome/GTG'
_IFACE_NAME2 = 'org.gnome.GTG'

_STATUS_RANK = {s: i for i, s in enumerate(['Active', 'Postponed', 'Dismiss', 'Done']) }
_STATUS_RANK_DEFAULT = len(_STATUS_RANK)


def _create_dbus_connection_gtg(iface, obj, service, activate=False):
    ''' Create dbus connection to GTG
        @activate: if True, start program if not running
    '''
    interface = None
    sbus = dbus.SessionBus()
    try:
        proxy_obj = sbus.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus')
        dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
        if activate or dbus_iface.NameHasOwner(iface):
            obj = sbus.get_object(service, obj)
            if obj:
                interface = dbus.Interface(obj, iface)
    except dbus.exceptions.DBusException as err:
        pretty.print_debug(__name__, err)
    return interface


def _create_dbus_connection(activate=False):
    interface = _create_dbus_connection_gtg(_IFACE_NAME2,
            _OBJECT_NAME2, _SERVICE_NAME2, activate)
    if interface is None:
        pretty.print_error(__name__, 'Cannot connect to GTG via DBus')
        if activate:
            raise NotAvailableError(_("Getting Things GNOME"))
    return interface


def _truncate_long_text(text, maxlen=80):
    if len(text) > maxlen:
        return text[:maxlen - 1] + '…'
    return text


def _load_tasks(interface):
    ''' Load task by dbus interface '''
    tasks = interface.GetTasks()
    if not tasks:
        tasks = interface.GetTasksFiltered("")
    for task in tasks:
        title = task['title'].strip()
        if not title:
            title = task['text'].strip()
        title = _truncate_long_text(title)
        otask = Task(task['id'], title, task['status'])
        otask.duedate = task['duedate']
        otask.startdate = task['startdate']
        otask.tags = task['tags']
        yield otask


def _change_task_status(task_id, status):
    interface = _create_dbus_connection(True)
    task = interface.GetTask(task_id)
    task['status'] = status
    interface.ModifyTask(task_id, task)

class Task (Leaf):
    def __init__(self, task_id, title, status):
        Leaf.__init__(self, task_id, title)
        self.status = status
        self.tags = None
        self.duedate = None
        self.startdate = None

    def get_description(self):
        descr = [self.status]
        if self.duedate:
            descr.append(_("due: %s") % self.duedate)
        if self.startdate:
            descr.append(_("start: %s") % self.startdate)
        if self.tags:
            descr.append(_("tags: %s") % " ".join(self.tags))
        return "  ".join(descr)

    def get_icon_name(self):
        return 'gtg'

    def get_actions(self):
        yield OpenEditor()
        yield Delete()
        if self.status != 'Done':
            yield MarkDone()
        if self.status != 'Dismiss':
            yield Dismiss()

    def sort_key(self):
        return _STATUS_RANK.get(self.status, _STATUS_RANK_DEFAULT)

class OpenEditor (Action):
    rank_adjust = 1
    action_accelerator = "o"

    def __init__(self):
        Action.__init__(self, _("Open"))

    def activate(self, leaf):
        interface = _create_dbus_connection(True)
        interface.OpenTaskEditor(leaf.object)

    def get_icon_name(self):
        return 'document-open'

    def get_description(self):
        return _("Open task in Getting Things GNOME!")


class Delete (Action):
    rank_adjust = -10

    def __init__(self):
        Action.__init__(self, _("Delete"))

    def activate(self, leaf):
        interface = _create_dbus_connection(True)
        interface.DeleteTask(leaf.object)

    def get_icon_name(self):
        return 'edit-delete'

    def get_description(self):
        return _("Permanently remove this task")


class MarkDone (Action):
    action_accelerator = "d"
    def __init__(self):
        Action.__init__(self, _("Mark Done"))

    def activate(self, leaf):
        _change_task_status(leaf.object, 'Done')

    def get_icon_name(self):
        return 'gtk-yes'

    def get_description(self):
        return _("Mark this task as done")


class Dismiss (Action):
    action_accelerator = "i"
    def __init__(self):
        Action.__init__(self, _("Dismiss"))

    def activate(self, leaf):
        _change_task_status(leaf.object, 'Dismiss')

    def get_icon_name(self):
        return 'gtk-cancel'

    def get_description(self):
        return _("Mark this task as not to be done anymore")


class CreateNewTask (Action):
    def __init__(self):
        Action.__init__(self, _("Create Task"))

    def activate(self, leaf):
        interface = _create_dbus_connection(True)
        title, body = textutils.extract_title_body(leaf.object)
        interface.OpenNewTask(title, body)

    def item_types(self):
        yield TextLeaf

    def get_icon_name(self):
        return 'document-new'

    def get_description(self):
        return _("Create new task in Getting Things GNOME")

class CreateNewEmptyTask (Action):
    def __init__(self):
        Action.__init__(self, _("Create Task"))

    def activate(self, leaf):
        interface = _create_dbus_connection(True)
        interface.OpenNewTask("", "")

    def item_types(self):
        yield AppLeaf

    def valid_for_item(self, leaf):
        return leaf.get_id() == GTG_ID

    def get_icon_name(self):
        return 'document-new'

    def get_description(self):
        return _("Create new task in Getting Things GNOME")


class TasksSource (AppLeafContentMixin, Source):
    appleaf_content_id = GTG_ID

    def __init__(self, name=None):
        Source.__init__(self, name or __kupfer_name__)
        self._tasks = []
        self._version = 3

    def initialize(self):
        bus = dbus.SessionBus()
        dbus_signal_connect_weakly(bus, "TaskAdded", self._on_tasks_updated,
                                   dbus_interface=_IFACE_NAME2)
        dbus_signal_connect_weakly(bus, "TaskModified", self._on_tasks_updated,
                                   dbus_interface=_IFACE_NAME2)
        dbus_signal_connect_weakly(bus, "TaskDeleted", self._on_tasks_updated,
                                   dbus_interface=_IFACE_NAME2)
        dbus_signal_connect_weakly(bus, "NameOwnerChanged", self._name_owner_changed,
                                   dbus_interface="org.freedesktop.DBus",
                                   arg0=_SERVICE_NAME2)

    def _name_owner_changed(self, name, old, new):
        if new and not self._tasks:
            self.mark_for_update()

    def _on_tasks_updated(self, task_id):
        self.mark_for_update()

    def get_items(self):
        interface = _create_dbus_connection()
        if interface is not None:
            self._tasks = list(_load_tasks(interface))
            self._tasks.sort(key=Task.sort_key)
        return self._tasks

    def get_icon_name(self):
        return 'gtg'

    def provides(self):
        yield Task
