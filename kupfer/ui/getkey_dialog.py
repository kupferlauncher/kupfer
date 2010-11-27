
from gi.repository import Gdk
from gi.repository import Gtk

from kupfer import version, config


class GetKeyDialogController(object):

	def __init__(self, check_callback=None, previous_key=None):
		'''@check_callback - optional function to check is entered key is valid.
		@previous_key - optional previous keybinding, press equal act like cancel'''
		builder = Gtk.Builder()
		builder.set_translation_domain(version.PACKAGE_NAME)

		ui_file = config.get_data_file("getkey_dialog.ui")
		builder.add_from_file(ui_file)
		builder.connect_signals(self)
		self.window = builder.get_object("dialoggetkey")
		self.labelkey = builder.get_object('labelkey')
		self.imagekeybindingaux = builder.get_object('imagekeybindingaux')
		self.labelkeybindingaux = builder.get_object('labelkeybindingaux')
		self.labelaccelerator = builder.get_object('labelaccelerator')

		self.imagekeybindingaux.hide()
		self.labelkeybindingaux.hide()

		self._key = None
		self._check_callback = check_callback
		self._previous_key = previous_key
		self._press_time = None

		self.window.connect("focus-in-event", self.on_window_focus_in)
		self.window.connect("focus-out-event", self.on_window_focus_out)

	def run(self):
		''' Run dialog, return key codes or None when user press cancel'''
		self.window.set_keep_above(True)
		self.window.run()
		self.window.destroy()
		return self._key

	def _return(self, key):
		" Finish dialog with @key as result"
		self._key = key
		self.window.hide()

	def on_buttoncancel_activate(self, _widget):
		self._return(None)

	def translate_keyboard_event(self, event):
		keymap = Gdk.keymap_get_default()
		# translate keys properly
		keyval, egroup, level, consumed = keymap.translate_keyboard_state(
					event.hardware_keycode, event.get_state(), event.group)
		modifiers = Gtk.accelerator_get_default_mod_mask() & ~consumed

		state = event.get_state() & modifiers

		return keyval, state

	def update_accelerator_label(self, keyval, state):
		accel_label = Gtk.accelerator_get_label(keyval, state)
		self.labelaccelerator.set_text(accel_label)

	def on_dialoggetkey_key_press_event(self, _widget, event):
		self.imagekeybindingaux.hide()
		self.labelkeybindingaux.hide()
		self._press_time = event.time

		keyval, state = self.translate_keyboard_event(event)
		keyname = Gtk.accelerator_name(keyval, state)
		if keyname == 'Escape':
			self._return(None)
		elif keyname == 'BackSpace':
			self._return('')
		self.update_accelerator_label(keyval, state)

	def on_dialoggetkey_key_release_event(self, widget, event):
		if not self._press_time:
			return
		keyval, state = self.translate_keyboard_event(event)
		self.update_accelerator_label(0, 0)

		if Gtk.accelerator_valid(keyval, state):
			key = Gtk.accelerator_name(keyval, state)
			if (self._previous_key is not None and
					key == self._previous_key):
				self._return(None)
				return
			if self._check_callback is None or self._check_callback(key):
				self._return(key)
			else:
				self.imagekeybindingaux.show()
				self.labelkeybindingaux.show()


	def on_window_focus_in(self, window, _event):
		pass

	def on_window_focus_out(self, _window, _event):
		pass


def ask_for_key(check_callback=None, previous_key=None):
	dlg = GetKeyDialogController(check_callback, previous_key)
	result = dlg.run()
	return result
