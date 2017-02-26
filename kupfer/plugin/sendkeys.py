
__kupfer_name__ = _("Send Keys")
__kupfer_actions__ = (
    "CopyAndPaste",
    "SendKeys",
    "TypeText",
    )
__description__ = _("Send synthetic keyboard events using "
                    "xautomation")
__version__ = ""
__author__ = ""

from gi.repository import Gtk, Gdk

from kupfer.objects import Leaf, Action, TextLeaf
from kupfer.objects import OperationError
from kupfer import utils
from kupfer import interface

# delay for first keypress and all following
INIT_DELAY = 'usleep 300000'
INTER_DELAY = 'usleep 50000'

class CopyAndPaste (Action):
    # rank down since it applies everywhere
    rank_adjust = -2
    def __init__(self):
        Action.__init__(self, _("Paste to Foreground Window"))
    def activate(self, leaf):
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        interface.copy_to_clipboard(leaf, clip)
        xte_paste_argv = ['xte', INIT_DELAY, 'keydown Control_L',
                          'key v', 'keyup Control_L']
        try:
            utils.spawn_async_raise(xte_paste_argv)
        except utils.SpawnError as exc:
            raise OperationError(exc)
    def item_types(self):
        yield Leaf
    def valid_for_item(self, leaf):
        try:
            return bool(interface.get_text_representation(leaf))
        except AttributeError:
            pass
    def get_description(self):
        return _("Copy to clipboard and send Ctrl+V to foreground window")
    def get_icon_name(self):
        return "edit-paste"

class SendKeys (Action):
    def __init__(self):
        Action.__init__(self, _("Send Keys"))

    def activate(self, leaf):
        return self.activate_multiple((leaf, ))

    def activate_multiple(self, objects):
        xte_sendkey_argv = ['xte', INIT_DELAY]
        iterobjects = iter(objects)
        for obj in iterobjects:
            xte_sendkey_argv.extend(self.make_keystr_arguments(obj.object))
            break
        for obj in iterobjects:
            xte_sendkey_argv.append(INTER_DELAY)
            xte_sendkey_argv.extend(self.make_keystr_arguments(obj.object))

        try:
            utils.spawn_async_raise(xte_sendkey_argv)
        except utils.SpawnError as exc:
            raise OperationError(exc)

    def make_keystr_arguments(self, keystr):
        keys, orig_mods = Gtk.accelerator_parse(keystr)
        m = {
            Gdk.ModifierType.SHIFT_MASK: "Shift_L",
            Gdk.ModifierType.CONTROL_MASK: "Control_L",
            Gdk.ModifierType.SUPER_MASK: "Super_L",
            Gdk.ModifierType.MOD1_MASK: "Alt_L",
        }
        mod_names = []
        mods = orig_mods
        for mod in m:
            if mod & mods:
                mod_names.append(m[mod])
                mods &= ~mod
        if mods != 0:
            raise OperationError("Keys not yet implemented: %s" %
                    Gtk.accelerator_get_label(keys, orig_mods))
        key_arg = 'key %s' % (Gdk.keyval_name(keys), )
        mods_down = ['keydown ' + n for n in mod_names]
        mods_up = ['keyup ' + n for n in reversed(mod_names)]
        return mods_down + [key_arg] + mods_up

    def item_types(self):
        yield TextLeaf
    def valid_for_item(self, leaf):
        text = leaf.object
        keys, mods = Gtk.accelerator_parse(text)
        return keys
    def get_description(self):
        return _("Send keys to foreground window")

class TypeText (Action):
    rank_adjust = -2 
    def __init__(self):
        Action.__init__(self, _("Type Text"))
    def activate(self, leaf):
        text = interface.get_text_representation(leaf)
        xte_paste_argv = ['xte', 'usleep 300000']
        # replace all newlines with 'key Return'
        for line in text.splitlines(True):
            xte_paste_argv.append("str " + line.rstrip("\r\n"))
            if line.endswith("\n"):
                xte_paste_argv.append("key Return")
        try:
            utils.spawn_async_raise(xte_paste_argv)
        except utils.SpawnError as exc:
            raise OperationError(exc)
    def item_types(self):
        yield Leaf
    def valid_for_item(self, leaf):
        try:
            return bool(interface.get_text_representation(leaf))
        except AttributeError:
            pass
    def get_description(self):
        return _("Type the text to foreground window")

