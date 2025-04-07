__kupfer_name__ = _("Send Keys")
__kupfer_actions__ = ("CopyAndPaste", "SendKeys", "TypeText")
__description__ = _("Send synthetic keyboard events using xautomation")
__version__ = ""
__author__ = ""

import typing as ty
from contextlib import suppress

from gi.repository import Gdk, Gtk

from kupfer import interface, launch
from kupfer.obj import Action, Leaf, OperationError, TextLeaf

if ty.TYPE_CHECKING:
    from gettext import gettext as _

# delay for first keypress and all following
_INIT_DELAY = "usleep 300000"
_INTER_DELAY = "usleep 50000"


class CopyAndPaste(Action):
    # rank down since it applies everywhere
    rank_adjust = -2

    def __init__(self):
        Action.__init__(self, _("Paste to Foreground Window"))

    def activate(self, leaf, iobj=None, ctx=None):
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        interface.copy_to_clipboard(leaf, clip)
        xte_paste_argv = [
            "xte",
            _INIT_DELAY,
            "keydown Control_L",
            "key v",
            "keyup Control_L",
        ]
        try:
            launch.spawn_async_raise(xte_paste_argv)
        except launch.SpawnError as exc:
            raise OperationError(exc) from exc

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        with suppress(AttributeError):
            return bool(interface.get_text_representation(leaf))

    def get_description(self):
        return _("Copy to clipboard and send Ctrl+V to foreground window")

    def get_icon_name(self):
        return "edit-paste"


class SendKeys(Action):
    def __init__(self):
        Action.__init__(self, _("Send Keys"))

    def activate(self, leaf, iobj=None, ctx=None):
        return self.activate_multiple((leaf,))

    def activate_multiple(self, objects):
        xte_sendkey_argv = ["xte", _INIT_DELAY]
        iterobjects = iter(objects)
        for obj in iterobjects:
            xte_sendkey_argv.extend(self.make_keystr_arguments(obj.object))
            break

        for obj in iterobjects:
            xte_sendkey_argv.append(_INTER_DELAY)
            xte_sendkey_argv.extend(self.make_keystr_arguments(obj.object))

        try:
            launch.spawn_async_raise(xte_sendkey_argv)
        except launch.SpawnError as exc:
            raise OperationError(exc) from exc

    def make_keystr_arguments(self, keystr):
        keys, orig_mods = Gtk.accelerator_parse(keystr)
        modifiers = {
            Gdk.ModifierType.SHIFT_MASK: "Shift_L",
            Gdk.ModifierType.CONTROL_MASK: "Control_L",
            Gdk.ModifierType.SUPER_MASK: "Super_L",
            Gdk.ModifierType.MOD1_MASK: "Alt_L",  # pylint: disable=no-member
        }
        mod_names = []
        mods = orig_mods
        for mod, value in modifiers.items():
            if mod & mods:
                mod_names.append(value)
                mods &= ~mod

        if mods != 0:
            label = Gtk.accelerator_get_label(keys, orig_mods)
            raise OperationError(f"Keys not yet implemented: {label}")

        mods_down = ["keydown " + n for n in mod_names]
        mods_up = ["keyup " + n for n in reversed(mod_names)]
        return [*mods_down, f"key {Gdk.keyval_name(keys)}", *mods_up]

    def item_types(self):
        yield TextLeaf

    def valid_for_item(self, leaf):
        text = leaf.object
        keys, _mods = Gtk.accelerator_parse(text)
        return bool(keys)

    def get_description(self):
        return _("Send keys to foreground window")


class TypeText(Action):
    rank_adjust = -2

    def __init__(self):
        Action.__init__(self, _("Type Text"))

    def activate(self, leaf, iobj=None, ctx=None):
        text = interface.get_text_representation(leaf)
        if not text:
            return

        xte_paste_argv = ["xte", "usleep 300000"]
        # replace all newlines with 'key Return'
        for line in text.splitlines(True):
            xte_paste_argv.append("str " + line.rstrip("\r\n"))
            if line.endswith("\n"):
                xte_paste_argv.append("key Return")

        try:
            launch.spawn_async_raise(xte_paste_argv)
        except launch.SpawnError as exc:
            raise OperationError(exc) from exc

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        with suppress(AttributeError):
            return bool(interface.get_text_representation(leaf))

    def get_description(self):
        return _("Type the text to foreground window")
