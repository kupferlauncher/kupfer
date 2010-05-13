# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Getting Things GNOME")
__kupfer_sources__ = ("TasksSource", )
__kupfer_actions__ = ("CreateNewTask",)
__description__ = _("Browse and create new task in GTG")
__version__ = "2010-05-13"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


import os
import subprocess
from xml.etree import cElementTree as ElementTree

import dbus
import gio

from kupfer import plugin_support
from kupfer import pretty
from kupfer.obj.base import Leaf, Action, Source
from kupfer.obj.objects import TextLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import PicklingHelperMixin

plugin_support.check_dbus_connection()

_SERVICE_NAME = 'org.GTG'
_OBJECT_NAME = '/org/GTG'
_IFACE_NAME = 'org.GTG'
_GTG_INTERNAL_FILES = ('projects.xml', 'tags.xml')
_GTG_HOME = "~/.local/share/gtg/"


def _create_dbus_connection(activate=False):
	''' Create dbus connection to Gajim
		@activate: true=starts gajim if not running
	'''
	interface = None
	sbus = dbus.SessionBus()
	try:
		proxy_obj = sbus.get_object('org.freedesktop.DBus',
				'/org/freedesktop/DBus')
		dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
		if activate or dbus_iface.NameHasOwner(_IFACE_NAME):
			obj = sbus.get_object(_SERVICE_NAME, _OBJECT_NAME)
			if obj:
				interface = dbus.Interface(obj, _IFACE_NAME)
	except dbus.exceptions.DBusException, err:
		pretty.print_debug(err)
	return interface


def _load_tasks(interface):
	''' Load task by dbus interface '''
	for task in interface.get_tasks():
		title = task['title'].strip()
		if not title:
			title = task['text'].strip()
			if len(title) > 80:
				title = title[:79] + '…'
		otask = Task(task['id'], title, task['status'])
		otask.duedate = task['duedate']
		otask.startdate = task['startdate']
		otask.tags = task['tags']
		yield otask


def _load_task_from_xml():
	''' Load tasks by xml file (when no gtg running) '''
	gtg_local_dir = os.path.expanduser(_GTG_HOME)
	if not os.path.isdir(gtg_local_dir):
		return
	for fname in os.listdir(gtg_local_dir):
		if not fname.endswith('.xml') or fname in _GTG_INTERNAL_FILES:
			continue
		ffullpath = os.path.join(gtg_local_dir, fname)
		if not os.path.isfile(ffullpath):
			continue
		tree = ElementTree.parse(ffullpath)
		for task in tree.findall('task'):
			status = task.attrib['status']
			if status != 'Active':
				continue
			task_id = task.attrib['id']
			title = task.find('title').text.strip()
			if not title:
				content = task.find('content')
				if content is None:
					continue
				title = content.text.strip()
				if len(title) > 80:
					title = title[:79] + '…'
			otask = Task(task_id, title, status)
			tags = task.attrib['tags']
			if tags:
				otask.tags = tags.split(",")
			duedate_n = task.find('duedate')
			if duedate_n is not None:
				otask.duedate = duedate_n.text.strip()
			startdate_n = task.find('startdate')
			if startdate_n is not None:
				otask.startdate = startdate_n.text.strip()
			yield otask


def _change_task_status(task_id, status):
	interface = _create_dbus_connection()
	if interface is not None:
		task = interface.get_task(task_id)
		task['status'] = status
		interface.modify_task(task_id, task)


class Task(Leaf):
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
		yield OpenTaskEditor()
		yield DeleteTask()
		yield MarkTaskDone()
		yield DismissTask()


class OpenTaskEditor(Action):
	def __init__(self):
		Action.__init__(self, _("Open Task Editor"))

	def activate(self, leaf):
		interface = _create_dbus_connection()
		if interface is not None:
			interface.open_task_editor(leaf.object)

	def get_icon_name(self):
		return 'gtk-open'


class DeleteTask(Action):
	rank_adjust = -5

	def __init__(self):
		Action.__init__(self, _("Delete Task"))

	def activate(self, leaf):
		interface = _create_dbus_connection()
		if interface is not None:
			interface.delete_task(leaf.object)

	def get_icon_name(self):
		return 'gtk-delete'

	def get_description(self):
		return _("Permanently remove this task")


class MarkTaskDone(Action):
	def __init__(self):
		Action.__init__(self, _("Mark Task Done"))

	def activate(self, leaf):
		_change_task_status(leaf.object, 'Done')

	def get_icon_name(self):
		return 'gtk-yes'

	def get_description(self):
		return _("Mark this task as done")


class DismissTask (Action):
	def __init__(self):
		Action.__init__(self, _("Dismiss Task"))

	def activate(self, leaf):
		_change_task_status(leaf.object, 'Dismiss')

	def get_icon_name(self):
		return 'gtk-cancel'

	def get_description(self):
		return _("Mark this task as not to be done anymore")


class CreateNewTask(Action):
	def __init__(self):
		Action.__init__(self, _("Create New Task"))

	def activate(self, leaf):
		interface = _create_dbus_connection()
		if interface is not None:
			if '\n' in leaf.object:
				title, text = leaf.object.split('\n', 1)
				interface.open_new_task(title, text)
			else:
				interface.open_new_task(leaf.object, '')
		else:
			p = subprocess.Popen(["gtg_new_task", "-i"], stdin=subprocess.PIPE)
			p.communicate(leaf.object)

	def item_types(self):
		yield TextLeaf

	def get_icon_name(self):
		return 'gtk-new'

	def get_description(self):
		return _("Create new task in Getting Things GNOME")


class TasksSource(AppLeafContentMixin, Source, PicklingHelperMixin):
	appleaf_content_id = 'gtg'

	def __init__(self, name=_('GTG Tasks')):
		Source.__init__(self, name)
		self._tasks = []
		self._version = 2

	def initialize(self):
		gfile = gio.File(os.path.expanduser(_GTG_HOME))
		self.monitor = gfile.monitor_directory(gio.FILE_MONITOR_NONE, None)
		if self.monitor:
			self.monitor.connect("changed", self._changed)

	def pickle_prepare(self):
		self.monitor = None

	def get_items(self):
		interface = _create_dbus_connection()
		if interface is None:
			self._tasks = list(_load_task_from_xml())
		else:
			self._tasks = list(_load_tasks(interface))
		return self._tasks

	def get_icon_name(self):
		return 'gtg'

	def provides(self):
		return Task

	def _changed(self, _monitor, _file1, _file2, _evt_type):
		self.mark_for_update()
