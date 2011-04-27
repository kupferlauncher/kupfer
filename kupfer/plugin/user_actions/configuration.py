# -*- coding: UTF-8 -*-
from __future__ import with_statement

__version__ = "2010-05-14"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import operator

import gtk

from kupfer import config, version
from kupfer.core.settings import ExtendedSetting

from . import actions


class PluginSettings(ExtendedSetting):
	''' Configuration - list of serives to show in browser.'''

	def __init__(self, confobj=None):
		pass

	def dialog(self, parent_widget):
		acts = list(actions.load_actions())
		dlg = DialogSelectActions(parent_widget)
		res = dlg.run(acts)
		if res:
			actions.save_actions(acts)
		return res


class DialogSelectActions:
	def __init__(self, parent_widget):
		self._create_dialog(parent_widget)

	def run(self, actions):
		self._actions = actions
		self._fill_actions_list()
		res = self.dlg.run() == gtk.RESPONSE_ACCEPT
		self.dlg.destroy()
		return res

	def on_btn_close_clicked(self, widget):
		self.dlg.response(gtk.RESPONSE_CLOSE)
		self.dlg.hide()

	def on_btn_saved_clicked(self, widget):
		self.dlg.response(gtk.RESPONSE_ACCEPT)
		self.dlg.hide()

	def on_btn_add_clicked(self, widget):
		act = actions.UserAction('', '')
		act.name = ''
		dlg = DialogEditAction(self.dlg)
		if dlg.run(act, self._actions):
			self._actions.append(act)
			self._fill_actions_list()

	def on_btn_edit_clicked(self, widget):
		selection = self.table.get_selection()
		model, it = selection.get_selected()
		if it:
			idx = self.store.get_value(it, 1)
			self._edit_action(idx)

	def on_btn_del_clicked(self, widget):
		selection = self.table.get_selection()
		model, it = selection.get_selected()
		if it:
			dialog = gtk.MessageDialog(self.dlg,
					gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
					gtk.MESSAGE_QUESTION)
			dialog.set_markup(_('<span weight="bold" size="larger">'
					'Are you sure you want to delete selected action?</span>\n\n'
					'All information will be deleted and can not be restored.'))
			dialog.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CLOSE,
					gtk.STOCK_DELETE, gtk.RESPONSE_ACCEPT)
			if dialog.run() == gtk.RESPONSE_ACCEPT:
				idx = self.store.get_value(it, 1)
				self._actions.pop(idx)
				self._fill_actions_list()
		dialog.destroy()

	def on_action_list_row_activated(self, widget, path, view_column):
		it = self.store.get_iter(path)
		idx = self.store.get_value(it, 1)
		self._edit_action(idx)

	def on_action_list_move_cursor(self, treeselection):
		record_selected = treeselection.count_selected_rows() > 0
		self._btn_del.set_sensitive(record_selected)
		self._btn_edit.set_sensitive(record_selected)

	def _create_dialog(self, parent_widget):
		builder = gtk.Builder()
		builder.set_translation_domain(version.PACKAGE_NAME)
		ui_file = config.get_plugin_data_file("user_actions",
				"user_actions_act_list.ui")
		builder.add_from_file(ui_file)
		builder.connect_signals(self)

		self.dlg = builder.get_object("dialog_actions_list")
		self.dlg.set_transient_for(parent_widget)
		actions_list_parent = builder.get_object('actions_list_parent')
		actions_list_parent.add(self._create_list())
		self._btn_edit = builder.get_object('btn_edit')
		self._btn_del = builder.get_object('btn_del')

	def _create_list(self):
		self.store = gtk.ListStore(str, int)
		self.table = table = gtk.TreeView(self.store)
		table.connect("row-activated", self.on_action_list_row_activated)
		table.get_selection().connect("changed", self.on_action_list_move_cursor)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn(_("Action"), cell)
		col.add_attribute(cell, "markup", 0)
		table.append_column(col)
		table.show()
		return table

	def _fill_actions_list(self):
		self.store.clear()
		self._actions.sort(key=operator.attrgetter('name'))
		for idx, action in enumerate(self._actions):
			self.store.append((action.name, idx))

	def _edit_action(self, idx):
		act = self._actions[idx]
		dlg = DialogEditAction(self.dlg)
		if dlg.run(act, self._actions):
			self._fill_actions_list()


class _UpdateActionError(RuntimeError):
	pass


class DialogEditAction:
	def __init__(self, parent):
		self._create_dialog(parent)

	def run(self, action, all_actions):
		self._action = action
		self._all_actions = all_actions
		self._fill_fields(action)
		self.dlg.set_title((_("Action %s") % action.name) if action.name else
				_('New action'))
		res = self.dlg.run() == gtk.RESPONSE_ACCEPT
		self.dlg.destroy()
		return res

	def on_btn_close_pressed(self, widget):
		self.dlg.response(gtk.RESPONSE_CLOSE)
		self.dlg.hide()

	def on_btn_save_pressed(self, widget):
		try:
			self._update_action()
		except _UpdateActionError, err:
			dlgmsg = gtk.MessageDialog(self.dlg,
					gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
					gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
			dlgmsg.set_markup(_('<span weight="bold" size="larger">'
				'Cannot update action.</span>'))
			dlgmsg.format_secondary_text(str(err))
			dlgmsg.run()
			dlgmsg.hide()
		else:
			self.dlg.response(gtk.RESPONSE_ACCEPT)
			self.dlg.hide()

	def _create_dialog(self, parent):
		builder = gtk.Builder()
		builder.set_translation_domain(version.PACKAGE_NAME)
		ui_file = config.get_plugin_data_file("user_actions",
				"user_actions_act_edit.ui")
		builder.add_from_file(ui_file)
		builder.connect_signals(self)

		self.dlg = builder.get_object("dialog_user_actions")
		self.dlg.set_transient_for(parent)
		self.entry_name = builder.get_object('entry_name')
		self.entry_descr = builder.get_object('entry_descr')
		self.entry_command = builder.get_object('entry_command')
		self.cb_run_in_terminal = builder.get_object('cb_run_in_terminal')
		self.cb_objects = {\
				'text': builder.get_object('cb_obj_text'),
				'url': builder.get_object('cb_obj_url'),
				'file': builder.get_object('cb_obj_file'),
				'executable': builder.get_object('cb_obj_exec'),
				'dir': builder.get_object('cb_obj_dir')}
		self.entry_filter = builder.get_object('entry_filter')
		self.rb_result = {\
				'': builder.get_object('rb_result_none'),
				'text': builder.get_object('rb_result_text'),
				'one-text': builder.get_object('rb_result_onetext'),
				'url': builder.get_object('rb_result_url'),
				'file': builder.get_object('rb_result_file')}
		self.cb_actions = builder.get_object('cb_actions')
		self.btn_del_action = builder.get_object('btn_del_action')

	def _fill_fields(self, action):
		self.entry_name.set_text(action.name or '')
		self.entry_descr.set_text(action.description or '')
		self.entry_command.set_text(action.command or '')
		self.entry_filter.set_text(';'.join(action.objects_filter)
				if action.objects_filter else  '')
		if action.leaf_types:
			for type_name, widget in self.cb_objects.iteritems():
				widget.set_active(type_name in action.leaf_types)
		else:
			for type_name, widget in self.cb_objects.iteritems():
				widget.set_active(False)
		result = (action.gather_result or '').strip()
		self.rb_result[result].set_active(True)
		self.cb_run_in_terminal.set_active(action.launch_in_terminal)

	def _update_action(self):
		action = self._action
		actname = self.entry_name.get_text().strip()
		if not actname:
			raise _UpdateActionError(_('Missing action name'))
		if any(True for act in self._all_actions if act.name == actname and
				action != act):
			raise _UpdateActionError(_('Action with this name already exists'))
		action.command = self.entry_command.get_text().strip()
		if not action.command:
			raise _UpdateActionError(_('Missing command.'))
		action.name = self.entry_name.get_text().strip()
		action.description = self.entry_descr.get_text().strip()
		action.objects_filter = self.entry_filter.get_text().split(';')
		action.leaf_types = []
		for type_name, widget in self.cb_objects.iteritems():
			if widget.get_active():
				action.leaf_types.append(type_name)
		action.gather_result = None
		for result, widget in self.rb_result.iteritems():
			if widget.get_active():
				action.gather_result = result
				break
		action.launch_in_terminal = self.cb_run_in_terminal.get_active()
