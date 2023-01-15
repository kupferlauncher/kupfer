from __future__ import annotations

import typing as ty

from gi.repository import Gdk, Gtk

from kupfer import config, version

CheckCallback = ty.Callable[[str], bool]


class GetKeyDialogController:
    def __init__(
        self,
        check_callback: CheckCallback | None = None,
        previous_key: str | None = None,
        screen: Gdk.Screen | None = None,
        parent: Gtk.Window | None = None,
        show_clear: bool = True,
    ):
        """
        check_callback: optional function to check is entered key is valid.
        previous_key - optional previous keybinding, press equal act like cancel
        screen: Screen to use
        parent: Parent toplevel window
        show_clear: Show the “clear” button
        """
        builder = Gtk.Builder()
        builder.set_translation_domain(version.PACKAGE_NAME)

        builder.add_from_file(config.get_data_file("getkey_dialog.ui"))
        builder.connect_signals(self)  # pylint: disable=no-member
        self.window = builder.get_object("dialoggetkey")
        # self.labelkey = builder.get_object("labelkey")
        self.imagekeybindingaux = builder.get_object("imagekeybindingaux")
        self.labelkeybindingaux = builder.get_object("labelkeybindingaux")
        self.labelaccelerator = builder.get_object("labelaccelerator")
        if not show_clear:
            buttonclear = builder.get_object("buttonclear")
            buttonclear.hide()

        self.imagekeybindingaux.hide()
        self.labelkeybindingaux.hide()

        self._key: str | None = None
        self._check_callback = check_callback
        self._previous_key = previous_key
        self._press_time = None

        if screen:
            self.window.set_screen(screen)

        if parent:
            self.window.set_transient_for(parent)

        self.window.connect("focus-in-event", self._on_window_focus_in)
        self.window.connect("focus-out-event", self._on_window_focus_out)

    def run(self) -> str | None:
        """Run dialog, return key codes or None when user press cancel"""
        self.window.set_keep_above(True)
        self.window.run()
        self.window.destroy()
        return self._key

    def _return(self, key: str | None) -> None:
        "Finish dialog with @key as result"
        self._key = key
        self.window.hide()

    def on_buttoncancel_activate(self, _widget: Gtk.Widget) -> bool:
        self._return_cancel()
        return True

    def on_buttonclear_activate(self, _widget: Gtk.Widget) -> bool:
        self._return_clear()
        return True

    def _return_cancel(self) -> None:
        self._return(None)

    def _return_clear(self) -> None:
        self._return("")

    def _translate_keyboard_event(
        self, widget: Gtk.Widget, event: Gdk.EventKey
    ) -> tuple[int, int]:
        keymap = Gdk.Keymap.get_for_display(widget.get_display())
        # translate keys properly
        (
            _wasmapped,
            keyval,
            _egroup,
            _level,
            consumed,
        ) = keymap.translate_keyboard_state(
            event.hardware_keycode, event.get_state(), event.group
        )
        modifiers = Gtk.accelerator_get_default_mod_mask() & ~consumed
        state = event.get_state() & modifiers

        return keyval, state

    def _update_accelerator_label(self, keyval: int, state: int) -> None:
        accel_label = Gtk.accelerator_get_label(keyval, state)
        self.labelaccelerator.set_text(accel_label)

    def on_dialoggetkey_key_press_event(
        self, widget: Gtk.Widget, event: Gdk.EventKey
    ) -> None:
        self.imagekeybindingaux.hide()
        self.labelkeybindingaux.hide()
        self._press_time = event.time

        keyval, state = self._translate_keyboard_event(widget, event)
        state = Gdk.ModifierType(state)
        keyname = Gtk.accelerator_name(keyval, state)
        if keyname == "Escape":
            self._return_cancel()
        elif keyname == "BackSpace":
            self._return_clear()

        self._update_accelerator_label(keyval, state)

    def on_dialoggetkey_key_release_event(
        self, widget: Gtk.Widget, event: Gdk.EventKey
    ) -> None:
        if not self._press_time:
            return

        keyval, state = self._translate_keyboard_event(widget, event)
        self._update_accelerator_label(0, 0)

        state = Gdk.ModifierType(state)
        if Gtk.accelerator_valid(keyval, state):
            key = Gtk.accelerator_name(keyval, state)
            if self._previous_key is not None and key == self._previous_key:
                self._return_cancel()
                return

            if self._check_callback is None or self._check_callback(key):
                self._return(key)
            else:
                self.imagekeybindingaux.show()
                self.labelkeybindingaux.show()

    def _on_window_focus_in(
        self, _window: Gtk.Window, _event: Gdk.EventFocus
    ) -> None:
        pass

    def _on_window_focus_out(
        self, _window: Gtk.Window, _event: Gdk.EventFocus
    ) -> None:
        pass


def ask_for_key(
    check_callback: CheckCallback | None = None,
    previous_key: str | None = None,
    screen: Gdk.Screen | None = None,
    parent: Gtk.Window | None = None,
    show_clear: bool = True,
) -> str | None:
    dlg = GetKeyDialogController(
        check_callback,
        previous_key,
        screen=screen,
        parent=parent,
        show_clear=show_clear,
    )
    result = dlg.run()
    return result
