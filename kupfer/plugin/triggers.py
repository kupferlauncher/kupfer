from __future__ import annotations

__kupfer_name__ = _("Triggers")
__kupfer_sources__ = ("Triggers",)
__kupfer_actions__ = ("AddTrigger",)
__description__ = _(
    "Assign global keybindings (triggers) to objects created "
    "with 'Compose Command'."
)
__version__ = "2009-12-30"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from gettext import gettext as _

from gi.repository import GLib, Gtk

from kupfer import plugin_support, puid
from kupfer.core import commandexec
from kupfer.obj import Action, OperationError, RunnableLeaf, Source
from kupfer.obj.compose import ComposedLeaf
from kupfer.support import task
from kupfer.ui import getkey_dialog, keybindings, uievents

plugin_support.check_keybinding_support()


class Trigger(RunnableLeaf):
    def get_actions(self):
        yield from RunnableLeaf.get_actions(self)
        yield RemoveTrigger()

    def wants_context(self):
        return True

    def is_valid(self):
        return Triggers.has_trigger(self.object)

    def run(self, ctx=None):
        assert ctx
        return Triggers.perform_trigger(ctx, self.object)

    def repr_key(self):
        return self.object


class Triggers(Source):
    instance: Triggers | None = None

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
        keybindings.get_keybound_object().connect(
            "keybinding", self._on_keybinding_callback
        )
        for target, (keystr, _name, _id) in self.trigger_table.items():
            keybindings.bind_key(keystr, target)

        self.output_debug("Loaded triggers, count:", len(self.trigger_table))

    def finalize(self):
        for target in self.trigger_table.keys():
            keybindings.bind_key(None, target)

    def _on_keybinding_callback(self, keyobj, target, display, event_time):
        if not self.has_trigger(target):
            return

        ui_ctx = uievents.gui_context_from_keyevent(event_time, display)
        ctx = commandexec.default_action_execution_context()
        exec_token = ctx.make_execution_token(ui_ctx)
        self.perform_trigger(exec_token, target)

    def get_items(self):
        for target, (keystr, name, _id) in self.trigger_table.items():
            label = Gtk.accelerator_get_label(*Gtk.accelerator_parse(keystr))
            yield Trigger(target, f"{label or keystr} ({name})")

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield Trigger

    @classmethod
    def has_trigger(cls, target):
        assert cls.instance
        return target in cls.instance.trigger_table

    @classmethod
    def perform_trigger(cls, ctx, target):
        assert cls.instance
        try:
            _, _, id_ = cls.instance.trigger_table[target]
        except KeyError as exc:
            raise OperationError(f"Trigger '{target}' does not exist") from exc

        if (obj := puid.resolve_unique_id(id_)) is not None:
            return obj.run(ctx)  # type:ignore

        return None

    @classmethod
    def add_trigger(cls, leaf, keystr):
        assert cls.instance
        # pylint: disable=protected-access
        cls.instance._add_trigger(leaf, keystr)

    @classmethod
    def remove_trigger(cls, target):
        assert cls.instance
        # pylint: disable=protected-access
        cls.instance._remove_trigger(target)

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


def _try_bind_key(keystr):
    label = Gtk.accelerator_get_label(*Gtk.accelerator_parse(keystr))
    if label is None:
        return False

    if len(label) == 1 and label.isalnum():
        return False

    target = keybindings.KEYRANGE_TRIGGERS[-1] - 1
    if succ := keybindings.bind_key(keystr, target):
        keybindings.bind_key(None, target)

    return succ


class BindTask(task.Task):
    def __init__(self, leaf, screen):
        super().__init__()
        self.leaf = leaf
        self.screen = screen

    def start(self, finish_callback):
        GLib.idle_add(self.ask_key, finish_callback)

    def ask_key(self, finish_callback):
        keystr = getkey_dialog.ask_for_key(
            _try_bind_key, screen=self.screen, show_clear=False
        )
        if keystr:
            Triggers.add_trigger(self.leaf, keystr)

        finish_callback(self)


class AddTrigger(Action):
    def __init__(self):
        Action.__init__(self, _("Add Trigger..."))

    def is_async(self):
        return True

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        return BindTask(leaf, ctx.environment.get_screen())

    def item_types(self):
        yield ComposedLeaf

    def get_icon_name(self):
        return "list-add"


class RemoveTrigger(Action):
    def __init__(self):
        Action.__init__(self, _("Remove Trigger"))

    def activate(self, leaf, iobj=None, ctx=None):
        Triggers.remove_trigger(leaf.object)

    def get_icon_name(self):
        return "list-remove"
