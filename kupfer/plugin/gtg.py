# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Getting Things GNOME")
__kupfer_sources__ = ("TasksSource", )
__kupfer_actions__ = ("CreateNewTask",)
__description__ = _("Browse and create new tasks in GTG")
__version__ = "2010-05-27"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


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
from kupfer.obj.base import Leaf, Action, Source
from kupfer.obj.objects import TextLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin

plugin_support.check_dbus_connection()

_SERVICE_NAME = 'org.GTG'
_OBJECT_NAME = '/org/GTG'
_IFACE_NAME = 'org.GTG'
_GTG_HOME = "~/.local/share/gtg/"
_SERVICE_NAME2 = 'org.gnome.GTG'
_OBJECT_NAME2 = '/org/gnome/GTG'
_IFACE_NAME2 = 'org.gnome.GTG'


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
	except dbus.exceptions.DBusException, err:
		pretty.print_debug(err)
	return interface


def _create_dbus_connection(activate=False):
	interface, apiver = _create_dbus_connection_gtg(_IFACE_NAME, _OBJECT_NAME,
			_SERVICE_NAME, activate), 1
	if interface is None:
		interface, apiver = _create_dbus_connection_gtg(_IFACE_NAME2,
				_OBJECT_NAME2, _SERVICE_NAME2, activate), 2
	if interface is None:
		pretty.print_error('Cannot connect to GTG via DBus')
	return interface, apiver


def _truncate_long_text(text, maxlen=80):
	if len(text) > maxlen:
		return text[:maxlen - 1] + u'…'
	return text


def _load_tasks(interface, apiver):
	''' Load task by dbus interface '''
	if apiver == 1:
		tasks = interface.get_tasks()
	else:
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
	interface, apiver = _create_dbus_connection(True)
	task = interface.get_task(task_id)
	task['status'] = status
	if apiver == 1:
		interface.modify_task(task_id, task)
	else:
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
		yield MarkDone()
		yield Dismiss()


class OpenEditor (Action):
	rank_adjust = 1

	def __init__(self):
		Action.__init__(self, _("Open"))

	def activate(self, leaf):
		interface, apiver = _create_dbus_connection(True)
		if apiver == 1:
			interface.open_task_editor(leaf.object)
		else:
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
		interface, apiver = _create_dbus_connection(True)
		if apiver:
			interface.delete_task(leaf.object)
		else:
			interface.DeleteTask(leaf.object)

	def get_icon_name(self):
		return 'edit-delete'

	def get_description(self):
		return _("Permanently remove this task")


class MarkDone (Action):
	def __init__(self):
		Action.__init__(self, _("Mark Done"))

	def activate(self, leaf):
		_change_task_status(leaf.object, 'Done')

	def get_icon_name(self):
		return 'gtk-yes'

	def get_description(self):
		return _("Mark this task as done")


class Dismiss (Action):
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
		interface, apiver = _create_dbus_connection(True)
		title, body = textutils.extract_title_body(leaf.object)
		if apiver == 1:
			interface.open_new_task(title, body)
		else:
			interface.OpenNewTask(title, body)

	def item_types(self):
		yield TextLeaf

	def get_icon_name(self):
		return 'document-new'

	def get_description(self):
		return _("Create new task in Getting Things GNOME")


class TasksSource (AppLeafContentMixin, Source, FilesystemWatchMixin):
	appleaf_content_id = 'gtg'

	def __init__(self, name=None):
		Source.__init__(self, name or __kupfer_name__)
		self._tasks = []
		self._version = 2

	def initialize(self):
		self.monitor_token = \
			self.monitor_directories(os.path.expanduser(_GTG_HOME))
		bus = dbus.Bus()
		self._signal_new_task = bus.add_signal_receiver(self._on_tasks_updated,
				signal_name="TaskAdded", dbus_interface=_IFACE_NAME2)
		self._signal_task_deleted = bus.add_signal_receiver(self._on_tasks_updated,
				signal_name="TaskDeleted", dbus_interface=_IFACE_NAME2)
		self._signal_task_modified = bus.add_signal_receiver(self._on_tasks_updated,
				signal_name="TaskModified", dbus_interface=_IFACE_NAME2)

	def finalize(self):
		bus = dbus.Bus()
		if self._signal_new_task is not None:
			bus.remove_signal_receiver(self._on_tasks_updated,
					signal_name="TaskAdded", dbus_interface=_IFACE_NAME2)
			bus.remove_signal_receiver(self._on_tasks_updated,
					signal_name="TaskDeleted", dbus_interface=_IFACE_NAME2)
			bus.remove_signal_receiver(self._on_tasks_updated,
					signal_name="TaskModified", dbus_interface=_IFACE_NAME2)

	def get_items(self):
		interface, apiver = _create_dbus_connection()
		if interface is not None:
			self._tasks = list(_load_tasks(interface, apiver))
		return self._tasks

	def get_icon_name(self):
		return 'gtg'

	def provides(self):
		yield Task

	def _on_tasks_updated(self, *argv, **kwarg):
		self.mark_for_update()
