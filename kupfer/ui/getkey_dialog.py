
import gtk

from kupfer import version, config


class GetKeyDialogController(object):
    def __init__(self, check_callback=None, previous_key=None, screen=None, parent=None):
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
        self.labelaccelerator = builder.get_object('labelaccelerator')

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
        self._return(None)

    def translate_keyboard_event(self, widget, event):
        keymap = gtk.gdk.Keymap.get_for_display(widget.get_display())
        # translate keys properly
        _wasmapped, keyval, egroup, level, consumed = keymap.translate_keyboard_state(
                    event.hardware_keycode, event.state, event.group)
        modifiers = gtk.accelerator_get_default_mod_mask() & ~consumed

        state = event.state & modifiers

        return keyval, state

    def update_accelerator_label(self, keyval, state):
        accel_label = gtk.accelerator_get_label(keyval, state)
        self.labelaccelerator.set_text(accel_label)

    def on_dialoggetkey_key_press_event(self, widget, event):
        self.imagekeybindingaux.hide()
        self.labelkeybindingaux.hide()
        self._press_time = event.time

        keyval, state = self.translate_keyboard_event(widget, event)
        state = gtk.gdk.ModifierType(state)
        keyname = gtk.accelerator_name(keyval, state)
        print("on_dialoggetkey_key_press_event", keyval, state)
        if keyname == 'Escape':
            self._return(None)
        elif keyname == 'BackSpace':
            self._return('')
        self.update_accelerator_label(keyval, state)

    def on_dialoggetkey_key_release_event(self, widget, event):
        if not self._press_time:
            return
        keyval, state = self.translate_keyboard_event(widget, event)
        print("on_dialoggetkey_key_release_event", keyval, state)
        self.update_accelerator_label(0, 0)

        state = gtk.gdk.ModifierType(state)
        if gtk.accelerator_valid(keyval, state):
            key = gtk.accelerator_name(keyval, state)
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


def ask_for_key(check_callback=None, previous_key=None, screen=None, parent=None):
    dlg = GetKeyDialogController(check_callback, previous_key, screen, parent)
    result = dlg.run()
    return result
