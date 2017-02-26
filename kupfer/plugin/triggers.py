__kupfer_name__ = _("Triggers")
__kupfer_sources__ = ("Triggers", )
__kupfer_actions__ = (
    "AddTrigger",
)
__description__ = _("Assign global keybindings (triggers) to objects created "
                    "with 'Compose Command'.")
__version__ = "2009-12-30"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from gi.repository import Gtk, GLib

from kupfer.objects import Action, Source
from kupfer.objects import RunnableLeaf
from kupfer.objects import OperationError
from kupfer.obj.compose import ComposedLeaf
from kupfer import puid
from kupfer import kupferstring
from kupfer import task

from kupfer.ui import keybindings
from kupfer.ui import uievents
from kupfer.ui import getkey_dialog
from kupfer.core import commandexec
from kupfer import plugin_support

plugin_support.check_keybinding_support()

class Trigger (RunnableLeaf):
    def get_actions(self):
        for act in RunnableLeaf.get_actions(self):
            yield act
        yield RemoveTrigger()
    def wants_context(self):
        return True
    def is_valid(self):
        return Triggers.has_trigger(self.object)
    def run(self, ctx):
        return Triggers.perform_trigger(ctx, self.object)
    def repr_key(self):
        return self.object

class Triggers (Source):
    instance = None

    def __init__(self):
        Source.__init__(self, _("Triggers"))
        self.trigger_table = {}

    def config_save(self):
        return {"triggers": self.trigger_table, "version": self.version}

    def config_save_name(self):
        return __name__

    def config_restore(self, state):
        self.trigger_table = state["triggers"]
        return True
    
    def initialize(self):
        Triggers.instance = self
        keybindings.GetKeyboundObject().connect("keybinding",
                                                self.keybinding_callback)
        for target, (keystr, name, id_) in self.trigger_table.items():
            keybindings.bind_key(keystr, target)
        self.output_debug("Loaded triggers, count:", len(self.trigger_table))

    def finalize(self):
        for target, (keystr, name, id_) in self.trigger_table.items():
            keybindings.bind_key(None, target)

    def keybinding_callback(self, keyobj, target, display, event_time):
        if not self.has_trigger(target):
            return
        ui_ctx = uievents.gui_context_from_keyevent(event_time, display)
        ctx = commandexec.DefaultActionExecutionContext()
        exec_token = ctx.make_execution_token(ui_ctx)
        self.perform_trigger(exec_token, target)

    def get_items(self):
        for target, (keystr, name, id_) in self.trigger_table.items():
            label = Gtk.accelerator_get_label(*Gtk.accelerator_parse(keystr))
            yield Trigger(target, "%s (%s)" % (label or keystr, name))

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield Trigger

    @classmethod
    def has_trigger(cls, target):
        return target in cls.instance.trigger_table

    @classmethod
    def perform_trigger(cls, ctx, target):
        try:
            keystr, name, id_ = cls.instance.trigger_table[target]
        except KeyError:
            raise OperationError("Trigger '%s' does not exist" % (target, ))
        obj = puid.resolve_unique_id(id_)
        if obj is None:
            return
        return obj.run(ctx)

    @classmethod
    def add_trigger(cls, leaf, keystr):
        Triggers.instance._add_trigger(leaf, keystr)

    @classmethod
    def remove_trigger(cls, target):
        Triggers.instance._remove_trigger(target)
    
    def _add_trigger(self, leaf, keystr):
        for target in range(*keybindings.KEYRANGE_TRIGGERS):
            if target not in self.trigger_table:
                break
        keybindings.bind_key(keystr, target)
        name = str(leaf)
        self.trigger_table[target] = (keystr, name, puid.get_unique_id(leaf))
        self.mark_for_update()

    def _remove_trigger(self, target):
        self.trigger_table.pop(target, None)
        keybindings.bind_key(None, target)
        self.mark_for_update()

    def get_icon_name(self):
        return "key_bindings"

def try_bind_key(keystr):
    label = Gtk.accelerator_get_label(*Gtk.accelerator_parse(keystr))
    ulabel = kupferstring.tounicode(label)
    if len(ulabel) == 1 and ulabel.isalnum():
        return False
    target = keybindings.KEYRANGE_TRIGGERS[-1] - 1
    succ = keybindings.bind_key(keystr, target)
    if succ:
        keybindings.bind_key(None, target)
    return succ

class BindTask (task.Task):
    def __init__(self, leaf, screen):
        self.leaf = leaf
        self.screen = screen

    def start(self, finish_callback):
        GLib.idle_add(self.ask_key, finish_callback)

    def ask_key(self, finish_callback):
        keystr = getkey_dialog.ask_for_key(try_bind_key,
                                           screen=self.screen,
                                           show_clear=False)
        if keystr:
            Triggers.add_trigger(self.leaf, keystr)
        finish_callback(self)

class AddTrigger (Action):
    def __init__(self):
        Action.__init__(self, _("Add Trigger..."))
    
    def is_async(self):
        return True

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        return BindTask(leaf, ctx.environment.get_screen())

    def item_types(self):
        yield ComposedLeaf

    def get_icon_name(self):
        return "list-add"

class RemoveTrigger (Action):
    def __init__(self):
        Action.__init__(self, _("Remove Trigger"))

    def activate(self, leaf):
        Triggers.remove_trigger(leaf.object)

    def get_icon_name(self):
        return "list-remove"

