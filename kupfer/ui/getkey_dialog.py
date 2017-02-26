
from gi.repository import Gtk, Gdk

from kupfer import version, config


class GetKeyDialogController(object):
    def __init__(self, check_callback=None, previous_key=None,
                 screen=None, parent=None,
                 show_clear=True):
        '''
        check_callback: optional function to check is entered key is valid.
        previous_key - optional previous keybinding, press equal act like cancel
        screen: Screen to use
        parent: Parent toplevel window
        show_clear: Show the “clear” button
        '''
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
        buttonclear = builder.get_object('buttonclear')
        if not show_clear:
            buttonclear.hide()

        self.imagekeybindingaux.hide()
        self.labelkeybindingaux.hide()

        self._key = None
        self._check_callback = check_callback
        self._previous_key = previous_key
        self._press_time = None

        if screen:
            self.window.set_screen(screen)
        if parent:
            self.window.set_transient_for(parent)
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
        self.return_cancel()
        return True

    def on_buttonclear_activate(self, _widget):
        self.return_clear()
        return True

    def return_cancel(self):
        self._return(None)

    def return_clear(self):
        self._return("")

    def translate_keyboard_event(self, widget, event):
        keymap = Gdk.Keymap.get_for_display(widget.get_display())
        # translate keys properly
        _wasmapped, keyval, egroup, level, consumed = keymap.translate_keyboard_state(
                    event.hardware_keycode, event.get_state(), event.group)
        modifiers = Gtk.accelerator_get_default_mod_mask() & ~consumed

        state = event.get_state() & modifiers

        return keyval, state

    def update_accelerator_label(self, keyval, state):
        accel_label = Gtk.accelerator_get_label(keyval, state)
        self.labelaccelerator.set_text(accel_label)

    def on_dialoggetkey_key_press_event(self, widget, event):
        self.imagekeybindingaux.hide()
        self.labelkeybindingaux.hide()
        self._press_time = event.time

        keyval, state = self.translate_keyboard_event(widget, event)
        state = Gdk.ModifierType(state)
        keyname = Gtk.accelerator_name(keyval, state)
        if keyname == 'Escape':
            self.return_cancel()
        elif keyname == 'BackSpace':
            self.return_clear()
        self.update_accelerator_label(keyval, state)

    def on_dialoggetkey_key_release_event(self, widget, event):
        if not self._press_time:
            return
        keyval, state = self.translate_keyboard_event(widget, event)
        self.update_accelerator_label(0, 0)

        state = Gdk.ModifierType(state)
        if Gtk.accelerator_valid(keyval, state):
            key = Gtk.accelerator_name(keyval, state)
            if (self._previous_key is not None and
                    key == self._previous_key):
                self.return_cancel()
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


def ask_for_key(check_callback=None, previous_key=None, screen=None,
                parent=None, show_clear=True):
    dlg = GetKeyDialogController(check_callback, previous_key,
                                 screen=screen,
                                 parent=parent,
                                 show_clear=show_clear)
    result = dlg.run()
    return result
