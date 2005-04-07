#!/usr/bin/python

import gtk

from kupfer import version, config


class GetKeyDialogController(object):

	def __init__(self, check_callback=None, previous_key=None):
		'''@check_callback - optional function to check is entered key is valid.
		@previous_key - optional previous keybinding, press equal act like cancel'''
		builder = gtk.Builder()
		builder.set_translation_domain(version.PACKAGE_NAME)

		ui_file = config.get_data_file("getkey_dialog.ui")
		builder.add_from_file(ui_file)
		builder.connect_signals(self)
		self.window = builder.get_object("dialoggetkey")
		self.labelkey = builder.get_object('labelkey')
		self.imagekeybindingaux = builder.get_object('imagekeybindingaux')
		self.labelkeybindingaux = builder.get_object('labelkeybindingaux')

		self.imagekeybindingaux.hide()
		self.labelkeybindingaux.hide()

		self._key = None
		self._check_callback = check_callback
		self._previous_key = previous_key

		self.window.connect("focus-in-event", self.on_window_focus_in)
		self.window.connect("focus-out-event", self.on_window_focus_out)

	def run(self):
		''' Run dialog, return key codes or None when user press cancel'''
		self.window.run()
		self.window.destroy()
		return self._key

	def on_buttoncancel_activate(self, _widget):
		self._key = None
		self.window.hide()

	def on_dialoggetkey_key_press_event(self, _widget, event):
		self.imagekeybindingaux.hide()
		self.labelkeybindingaux.hide()
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == 'Escape':
			self._key = None
			self.window.hide()
		elif keyname == 'BackSpace':
			self._key = ''
			self.window.hide()
		elif gtk.accelerator_valid(event.keyval, event.state):
			modifiers = gtk.accelerator_get_default_mod_mask()
			state = event.state & modifiers
			self._key = gtk.accelerator_name(event.keyval, state)
			if self._previous_key is not None and self._key == self._previous_key:
				self._key = None
				self.window.hide()
				return
			if self._check_callback is None:
				self.window.hide()
				return
			if self._check_callback(self._key):
				self.window.hide()
			else:
				self.imagekeybindingaux.show()
				self.labelkeybindingaux.show()
				self._key = None

	def on_dialoggetkey_key_release_event(self, widget, event):
		pass

	def on_window_focus_in(self, window, _event):
		pass

	def on_window_focus_out(self, _window, _event):
		pass


def ask_for_key(check_callback=None, previous_key=None):
	dlg = GetKeyDialogController(check_callback, previous_key)
	result = dlg.run()
	return result
