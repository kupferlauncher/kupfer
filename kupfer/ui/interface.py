#! /usr/bin/env python3

"""
UI Interface controller
"""
from __future__ import annotations

import functools
import textwrap
import typing as ty

from gi.repository import Gdk, Gio, GObject, Gtk, Pango

from kupfer import interface
from kupfer.core import actionaccel, settings
from kupfer.core.datactrl import DataController, PaneMode, PaneSel
from kupfer.core.search import Rankable
from kupfer.obj import AnySource, FileLeaf, Leaf, Action
from kupfer.support import pretty, scheduler
from kupfer.ui import accelerators, getkey_dialog, kupferhelp, uievents, uiutils
from kupfer.ui import preferences
from kupfer.ui._support import escape_markup_str, text_direction_is_ltr
from kupfer.ui.search import ActionSearch, LeafSearch, Search, State

if ty.TYPE_CHECKING:
    from gettext import gettext as _

_ELLIPSIZE_MIDDLE: ty.Final = Pango.EllipsizeMode.MIDDLE
_SLOW_INPUT_INTERVAL: ty.Final = 2
_KEY_PRESS_INTERVAL: ty.Final = 0.3
_KEY_PRESS_REPEAT_THRESHOLD: ty.Final = 0.02


# accelerator is any function with no parameters; result is ignored
AccelFunc = ty.Callable[[], ty.Any]


# pylint: disable=too-few-public-methods
@ty.runtime_checkable
class KeyCallback(ty.Protocol):
    """Key press callback interface."""

    def __call__(self, shift_mask: int, mod_mask: int, /) -> bool:
        ...


def _trunc_long_str(instr: ty.Any) -> str:
    "truncate long object names"
    ustr = str(instr)
    return ustr[:25] + "…" if len(ustr) > 27 else ustr


def _get_accel(key: str, acf: AccelFunc) -> tuple[str, AccelFunc]:
    """Return name, method pair for @key"""
    if name := accelerators.ACCELERATOR_NAMES.get(key):
        return name, acf

    raise RuntimeError(f"Missing accelerator: {key}")


def _translate_keys(event: Gdk.EventKey) -> tuple[int, int, bool]:
    event_state = event.get_state()
    # translate keys properly
    (
        _was_bound,
        keyv,
        _egroup,
        _level,
        consumed,
    ) = Gdk.Keymap.get_default().translate_keyboard_state(
        event.hardware_keycode, event_state, event.group
    )

    all_modifiers = Gtk.accelerator_get_default_mod_mask()
    shift_mask = (event_state & all_modifiers) == Gdk.ModifierType.SHIFT_MASK
    event_state &= all_modifiers & ~consumed

    return event_state, keyv, shift_mask


# pylint: disable=too-many-public-methods,too-many-instance-attributes
class Interface(GObject.GObject, pretty.OutputMixin):  # type:ignore
    """Controller object that controls the input and the state (current active)
    search object/widget.

    Signals:
    * cancelled: def callback(controller)
        escape was typed


    NOTE: some methods are get by getattr and call!
    """

    __gtype_name__ = "Interface"

    def __init__(self, controller: DataController, window: Gtk.Window) -> None:
        """
        @controller: DataController
        @window: toplevel window
        """
        GObject.GObject.__init__(self)

        self.search = LeafSearch()
        self.search.set_name("kupfer-object-pane")

        self.action = ActionSearch()
        self.action.set_name("kupfer-action-pane")

        self.third = LeafSearch()
        self.third.set_name("kupfer-indirect-object-pane")
        self.current: Search | None = None

        self._widget: Gtk.Widget | None = None
        self._ui_transition_timer = scheduler.Timer()
        self._pane_three_is_visible = False
        self._is_text_mode = False
        self._latest_input_timer = scheduler.Timer()
        self._reset_to_toplevel = False
        self._reset_when_back = False
        self._preedit_text = ""

        self._create_widgets(window)

        self._data_ctrl = controller
        self._data_ctrl.connect("search-result", self._on_search_result)
        self._data_ctrl.connect("source-changed", self._on_source_changed)
        self._data_ctrl.connect("pane-reset", self._on_pane_reset)
        self._data_ctrl.connect("mode-changed", self._on_mode_changed)
        self._data_ctrl.connect(
            "object-stack-changed", self._on_object_stack_changed
        )
        # Setup keyval mapping
        self._prepare_key_book()
        self._action_accel_config = actionaccel.AccelConfig()
        self.search.reset()

    def _create_widgets(self, window: Gtk.Window) -> None:
        self._entry = Gtk.Entry()
        self._preedit = Gtk.Entry()
        ## make sure we lose the preedit focus ring
        self._preedit.set_name("kupfer-preedit")
        self._preedit.set_has_frame(False)
        self._preedit.set_width_chars(0)
        self._preedit.set_alignment(1)

        self._label = Gtk.Label()
        self._label.set_width_chars(50)
        self._label.set_max_width_chars(50)
        self._label.set_single_line_mode(True)
        self._label.set_ellipsize(_ELLIPSIZE_MIDDLE)
        self._label.set_name("kupfer-description")

        self._switch_to_source_init()

        self._entry.connect("realize", self._on_entry_realized)
        self._entry.connect("changed", self._on_entry_changed)
        self._preedit.connect("insert-text", self._on_preedit_insert_text)
        self._preedit.connect("draw", self._on_preedit_draw)
        self._preedit.connect("preedit-changed", self._on_preedit_im_changed)
        for widget in (self._entry, self._preedit):
            widget.connect("activate", self._on_activate, None)
            widget.connect("key-press-event", self._on_entry_key_press)
            widget.connect("key-release-event", self._on_entry_key_release)
            widget.connect("copy-clipboard", self._on_entry_copy_clipboard)
            widget.connect("cut-clipboard", self._on_entry_cut_clipboard)
            widget.connect("paste-clipboard", self._on_entry_paste_clipboard)

        # set up panewidget => self signals
        # as well as window => panewidgets
        for widget_owner in (self.search, self.action, self.third):
            widget = widget_owner.widget()
            widget_owner.connect("activate", self._on_activate)
            widget_owner.connect("cursor-changed", self._on_selection_changed)
            widget.connect("button-press-event", self._on_pane_button_press)
            # window signals
            window.connect("configure-event", widget_owner.window_config)
            window.connect("hide", widget_owner.window_hidden)

    def _prepare_key_book(self) -> None:
        keys = (
            "Up",
            "Down",
            "Right",
            "Left",
            "Tab",
            "ISO_Left_Tab",
            "BackSpace",
            "Escape",
            "Delete",
            "space",
            "Page_Up",
            "Page_Down",
            "Home",
            "End",
            "Return",
        )
        self._key_book = key_book = {k: Gdk.keyval_from_name(k) for k in keys}
        if not text_direction_is_ltr():
            # for RTL languages, simply swap the meaning of Left and Right
            # (for keybindings!)
            key_book["Left"], key_book["Right"] = (
                key_book["Right"],
                key_book["Left"],
            )

        self._key_book_cbs: dict[int, KeyCallback] = {
            key_book["Escape"]: self._on_escape_key_press,
            key_book["Up"]: self._on_up_key_press,
            key_book["Page_Up"]: self._on_page_up_key_press,
            key_book["Down"]: self._on_down_key_press,
            key_book["Page_Down"]: self._on_page_down_key_press,
            key_book["Right"]: self._on_right_key_press,
            key_book["BackSpace"]: self._on_backspace_key_press,
            key_book["Left"]: self._on_back_key_press,
            key_book["Tab"]: functools.partial(
                self._on_tab_key_press, reverse=False
            ),
            key_book["ISO_Left_Tab"]: functools.partial(
                self._on_tab_key_press, reverse=True
            ),
            key_book["Home"]: self._on_home_key_press,
        }

    def get_widget(self) -> Gtk.Widget:
        """Return a Widget containing the whole Interface. Create if not exist."""
        if self._widget:
            return self._widget

        box = Gtk.HBox()
        box.pack_start(self.search.widget(), True, True, 3)
        box.pack_start(self.action.widget(), True, True, 3)
        box.pack_start(self.third.widget(), True, True, 3)
        vbox = Gtk.VBox()
        vbox.pack_start(box, True, True, 0)

        label_align = Gtk.Alignment.new(0.5, 1, 0, 0)
        label_align.set_property("top-padding", 3)
        label_align.add(self._label)
        vbox.pack_start(label_align, False, False, 0)
        vbox.pack_start(self._entry, False, False, 0)
        vbox.show_all()
        self.third.hide()
        self._widget = vbox
        return vbox

    def lazy_setup(self) -> None:
        def validate(keystr):
            keyv, mod = Gtk.accelerator_parse(keystr)
            return (
                mod == 0
                and keyv != 0
                and Gtk.accelerator_valid(
                    keyv,
                    Gdk.ModifierType.MOD1_MASK,  # pylint: disable=no-member
                )
            )

        self._action_accel_config.load(validate)
        self.action.action_accel_config = self._action_accel_config
        self.action.lazy_setup()
        self.output_debug("Finished lazy_setup")

    def save_config(self) -> None:
        self._action_accel_config.store()
        self.output_debug("Finished save_config")

    def _on_entry_realized(self, widget: Gtk.Widget) -> None:
        self._update_text_mode()

    def _on_entry_key_release(self, entry, event):
        return

    def _process_accels(self, keyv: int, event_state: int) -> bool:
        setctl = settings.get_settings_controller()
        # process accelerators
        for action, accel in setctl.get_accelerators().items():
            akeyv, amodf = Gtk.accelerator_parse(accel)
            if akeyv and akeyv == keyv and amodf == event_state:
                if action_method := getattr(self, action, None):
                    action_method()
                else:
                    pretty.print_error(__name__, f"Action invalid '{action}'")

                return True

        return False

    # pylint: disable=too-many-statements,too-many-branches,too-many-return-statements
    def _on_entry_key_press(
        self, entry: Gtk.Entry, event: Gdk.EventKey
    ) -> bool:
        """Intercept arrow keys and manipulate table without losing focus from
        entry field."""
        assert self.current is not None
        direct_text_key: int = Gdk.keyval_from_name("period")
        init_text_keys = list(
            map(Gdk.keyval_from_name, ("slash", "equal", "question"))
        )
        init_text_keys.append(direct_text_key)
        # translate keys properly
        event_state, keyv, shift_mask = _translate_keys(event)

        self._reset_input_timer()
        # process accelerators
        if self._process_accels(keyv, event_state):
            return True

        # look for action accelerators
        if event_state == self.action.accel_modifier:
            keystr = Gtk.accelerator_name(keyv, 0)
            if self._action_accelerator(keystr):
                return True

        if self._preedit_text:
            return False

        key_book = self._key_book
        use_command_keys = (
            settings.get_settings_controller().get_use_command_keys()
        )
        has_selection = self.current.get_match_state() == State.MATCH
        if not self._is_text_mode and use_command_keys:
            # translate extra commands to normal commands here
            # and remember skipped chars
            if keyv == key_book["space"]:
                keyv = key_book["Up" if shift_mask else "Down"]

            elif keyv == ord("/") and has_selection:
                keyv = key_book["Right"]

            elif keyv == ord(",") and has_selection:
                if self.comma_trick():
                    return True

            elif keyv in init_text_keys:
                if self._try_enable_text_mode():
                    # swallow if it is the direct key
                    return keyv == direct_text_key

        if self._is_text_mode and keyv in (
            key_book["Left"],
            key_book["Right"],
            key_book["Home"],
            key_book["End"],
        ):
            # pass these through in text mode
            # except on → at the end of the input
            cursor_position = self._entry.get_property("cursor-position")
            if (
                keyv != key_book["Right"]
                or cursor_position == 0
                or cursor_position != self._entry.get_text_length()
            ):
                return False

        if key_cb := self._key_book_cbs.get(keyv):
            self._reset_to_toplevel = False
            # pylint: disable=no-member
            return key_cb(shift_mask, event_state == Gdk.ModifierType.MOD1_MASK)

        return False

    def _on_entry_copy_clipboard(self, entry: Gtk.Entry) -> bool:
        """Copy current selection to clipboard. Delegate to text entry when in
        text mode."""
        if self._is_text_mode or not self.current:
            return False

        if selection := self.current.get_current():
            clip = Gtk.Clipboard.get_for_display(
                entry.get_display(), Gdk.SELECTION_CLIPBOARD
            )
            return interface.copy_to_clipboard(selection, clip)

        return False

    def _on_entry_cut_clipboard(self, entry: Gtk.Entry) -> bool:
        if self._on_entry_copy_clipboard(entry):
            self.reset_current()
            self._reset()

        return False

    def _entry_paste_data_received(
        self,
        clipboard: Gtk.Clipboard,
        targets: ty.Iterable[str],
        _extra: ty.Any,
        entry: Gtk.Widget,
    ) -> None:
        uri_target = Gdk.Atom.intern("text/uri-list", False)
        ### check if we can insert files
        if uri_target in targets:
            # paste as files
            sdata = clipboard.wait_for_contents(uri_target)
            self.reset_current()
            self._reset()
            self.put_files(sdata.get_uris(), paths=False)
            ## done
        else:
            # enable text mode and reemit to paste text
            self._try_enable_text_mode()
            if self._is_text_mode:
                entry.emit("paste-clipboard")

    def _on_entry_paste_clipboard(self, entry: Gtk.Widget) -> None:
        if not self._is_text_mode:
            self._reset()
            ## when not in text mode,
            ## stop signal emission so we can handle it
            clipboard = Gtk.Clipboard.get_for_display(
                entry.get_display(), Gdk.SELECTION_CLIPBOARD
            )
            clipboard.request_targets(self._entry_paste_data_received, entry)
            entry.emit_stop_by_name("paste-clipboard")

    def _reset_text(self) -> None:
        """Reset text in entry."""
        self._entry.set_text("")

    def _reset(self) -> None:
        """Reset text and hide table."""
        self._reset_text()
        if self.current:
            self.current.hide_table()

    def reset_current(self, populate: bool = False) -> None:
        """Reset the source or action view.

        Corresponds to backspace.
        """
        assert self.current
        if self.current.get_match_state() is State.WAIT:
            self._toggle_text_mode(False)

        if self.current is self.action or populate:
            self._populate_search()
        else:
            self.current.reset()

    def reset_all(self) -> None:
        """Reset all panes and focus the first.

        This is accelerator handler."""
        self.switch_to_source()
        while self._browse_up():
            pass

        self._toggle_text_mode(False)
        self._data_ctrl.object_stack_clear_all()
        self.reset_current()
        self._reset()

    def _populate_search(self) -> None:
        """Do a blanket search/empty search to populate current pane"""
        if pane := self._pane_for_widget(self.current):
            self._data_ctrl.search(pane, interactive=True)

    def soft_reset(self, pane: PaneSel | None = None) -> None:
        """Reset `pane` or current pane context/source softly
        (without visible update), and unset _reset_to_toplevel marker.
        """
        pane = pane or self._pane_for_widget(self.current)
        assert pane is not None
        if newsrc := self._data_ctrl.soft_reset(pane):
            assert self.current
            self.current.set_source(newsrc)

        self._reset_to_toplevel = False

    def _delete_from_stack(self) -> None:
        """Delete item from stack; related do backspace key press."""
        pane = self._pane_for_widget(self.current)
        if self._data_ctrl.get_object_stack(pane):
            self._data_ctrl.object_stack_pop(pane)
            self._reset_text()
            return

        self._on_back_key_press()

    def _relax_search_terms(self) -> None:
        if self._is_text_mode:
            return

        assert self.current
        self._reset_text()
        self.current.relax_match()

    def _get_can_enter_text_mode(self) -> bool:
        """We can enter text mode if the data backend allows,
        and the text entry is ready for input (empty)
        """
        if pane := self._pane_for_widget(self.current):
            val = self._data_ctrl.get_can_enter_text_mode(pane)
            entry_text = self._entry.get_text()
            return val and not entry_text

        return False

    def _try_enable_text_mode(self) -> bool:
        """Perform a soft reset if possible and then try enabling text mode"""
        if self._reset_to_toplevel:
            self.soft_reset()

        if self._get_can_enter_text_mode():
            return self._toggle_text_mode(True)

        return False

    def _toggle_text_mode(self, val: bool) -> bool:
        """Toggle text mode on/off per @val, and return the subsequent on/off
        state.
        """
        val = val and self._get_can_enter_text_mode()
        self._is_text_mode = val
        self._update_text_mode()
        self._reset()
        return val

    def toggle_text_mode_quick(self) -> None:
        """Toggle text mode or not, if we can or not, without reset.

        NOTE: accelerator
        """
        self._is_text_mode = not self._is_text_mode
        if self._is_text_mode and self.current:
            self.current.hide_table()

        self._update_text_mode()

    def _disable_text_mode_quick(self) -> None:
        """Toggle text mode or not, if we can or not, without reset"""
        if self._is_text_mode:
            self._is_text_mode = False
            self._update_text_mode()

    def _update_text_mode(self) -> None:
        """update appearance to whether text mode enabled or not"""
        if self._is_text_mode:
            self._entry.show()
            self._entry.grab_focus()
            self._entry.set_position(-1)
            self._preedit.hide()
            self._preedit.set_width_chars(0)
        else:
            self._entry.hide()

        self._update_active()

    def _switch_to_source_init(self) -> None:
        """Initial switch to source."""
        self.current = self.search
        self._update_active()
        if self._is_text_mode:
            self.toggle_text_mode_quick()

    def switch_to_source(self) -> None:
        """Switch to first (leaves) pane.

        NOTE: accelerator
        """
        self._switch_current_to(0)

    def switch_to_2(self) -> None:
        """Switch to second (action) pane.

        NOTE: accelerator
        """
        self._switch_current_to(1)

    def switch_to_3(self) -> None:
        """Switch to third (leaves) pane.

        NOTE: accelerator
        """
        self._switch_current_to(2)

    def focus(self) -> None:
        """Called when the interface is focus (after being away)."""
        if self._reset_when_back:
            self._reset_when_back = False
            self._toggle_text_mode(False)

        # preserve text mode, but switch to source if we are not in it
        if not self._is_text_mode:
            self.switch_to_source()

        # Check that items are still valid when "coming back"
        self._data_ctrl.validate()

    def did_launch(self) -> None:
        """Called to notify that 'activate' was successful. Request reset on get
        focus again."""
        self._reset_when_back = True

    def did_get_result(self) -> None:
        """called when a command result has come in."""
        self._reset_when_back = False

    def put_away(self) -> None:
        """Called when the interface is hidden"""
        self._relax_search_terms()
        self._reset_to_toplevel = True
        # no hide / show pane three on put away -> focus anymore

    def select_selected_file(self) -> None:
        """Find & select selected file in browser.

        Note: accelerator.
        """
        # Add optional lookup data to narrow the search
        self._data_ctrl.find_object("qpfer:selectedfile#any.FileLeaf")

    def select_clipboard_file(self) -> None:
        """Find & select leaf representing file in clipboard.

        Note: accelerator.
        """
        # Add optional lookup data to narrow the search
        self._data_ctrl.find_object("qpfer:clipboardfile#any.FileLeaf")

    def select_selected_text(self) -> None:
        """Find & select leaf representing selected text.

        Note: accelerator.
        """
        self._data_ctrl.find_object("qpfer:selectedtext#any.TextLeaf")

    def select_clipboard_text(self) -> None:
        """Find & select leaf representing text in clipboard.

        Note: accelerator.
        """
        # Add optional lookup data to narrow the search
        self._data_ctrl.find_object("qpfer:clipboardtext#any.TextLeaf")

    def select_quit(self) -> None:
        """Find & select quit leaf.

        Note: accelerator.
        """
        self._data_ctrl.reset()
        self._data_ctrl.find_object("qpfer:quit")

    def show_help(self) -> None:
        """Show help.

        Note: accelerator.
        """
        kupferhelp.show_help(self._make_gui_ctx())
        self.emit("launched-action")

    def show_preferences(self) -> None:
        """Show preferences window.

        Note: accelerator.
        """
        self._data_ctrl.reset()
        preferences.show_preferences(self._make_gui_ctx())
        self.emit("launched-action")

    def compose_action(self) -> None:
        """Compose action from current stack.
        NOTE: accelerator
        """
        self._data_ctrl.compose_selection()

    def mark_as_default(self) -> bool:
        """Mark current action as default for selected leaf.

        NOTE: accelerator
        """
        if self.action.get_match_state() != State.MATCH:
            return False

        self._data_ctrl.mark_as_default(PaneSel.ACTION)
        return True

    def erase_affinity_for_first_pane(self) -> bool:
        """
        NOTE: accelerator
        """
        if self.search.get_match_state() != State.MATCH:
            return False

        self._data_ctrl.erase_object_affinity(PaneSel.SOURCE)
        return True

    def comma_trick(self) -> bool:
        """Comma trick - add current leaf to stack.
        NOTE: accelerator
        """
        assert self.current

        if self.current.get_match_state() != State.MATCH:
            return False

        cur = self.current.get_current()
        curpane = self._pane_for_widget(self.current)
        if cur and self._data_ctrl.object_stack_push(curpane, cur):
            self._relax_search_terms()
            if self._is_text_mode:
                self._reset_text()

            return True

        return False

    def _action_accelerator(self, keystr: str) -> bool:
        """Find & launch accelerator action for `keystr` accelerator name..

        Return False if it was not possible to handle or the action was not
        used, return True if it was acted upon
        """
        if self.search.get_match_state() != State.MATCH:
            return False

        self.output_debug("Looking for action accelerator for", keystr)
        success, activate = self.action.select_action_by_accel(keystr)
        if success:
            if activate:
                self._disable_text_mode_quick()
                self.activate()
            else:
                self.switch_to_3()
        else:
            self.output_debug("No action found for", keystr)
            return False

        return True

    def _assign_action_accelerator(self) -> None:
        if self.action.get_match_state() != State.MATCH:
            raise RuntimeError("No Action Selected")

        def is_good_keystr(k: str) -> bool:
            keyv, mods = Gtk.accelerator_parse(k)
            return keyv != 0 and mods in (0, self.action.accel_modifier)

        widget = self.get_widget()
        keystr = getkey_dialog.ask_for_key(
            is_good_keystr,
            screen=widget.get_screen(),
            parent=widget.get_toplevel(),
        )
        if keystr is None:
            # Was cancelled
            return

        action = self.action.get_current()
        # Remove the modifiers
        keyv, _mods = Gtk.accelerator_parse(keystr)
        keystr = Gtk.accelerator_name(keyv, 0)
        assert keystr
        self._action_accel_config.set(action, keystr)

    def get_context_actions(self) -> ty.Iterable[tuple[str, AccelFunc]]:
        """Get a list of (name, function) currently active context actions."""
        assert self.current

        has_match = self.current.get_match_state() == State.MATCH
        if has_match:
            yield _get_accel("compose_action", self.compose_action)

        yield _get_accel("select_selected_text", self.select_selected_text)

        if self._get_can_enter_text_mode():
            yield _get_accel(
                "toggle_text_mode_quick", self.toggle_text_mode_quick
            )

        if self.action.get_match_state() == State.MATCH:
            smatch = self.search.get_current()
            amatch = self.action.get_current()

            label = _('Assign Accelerator to "%(action)s"') % {
                "action": _trunc_long_str(amatch)
            }
            w_label = textwrap.wrap(label, width=40, subsequent_indent="    ")
            yield ("\n".join(w_label), self._assign_action_accelerator)

            label = _('Make "%(action)s" Default for "%(object)s"') % {
                "action": _trunc_long_str(amatch),
                "object": _trunc_long_str(smatch),
            }
            w_label = textwrap.wrap(label, width=40, subsequent_indent="    ")
            yield ("\n".join(w_label), self.mark_as_default)

        if has_match:
            if self._data_ctrl.get_object_has_affinity(PaneSel.SOURCE):
                # TRANS: Removing learned and/or configured bonus search score
                yield (
                    _('Forget About "%s"')
                    % _trunc_long_str(self.search.get_current()),
                    self.erase_affinity_for_first_pane,
                )

            yield _get_accel("reset_all", self.reset_all)

    def _on_pane_reset(
        self,
        _controller: ty.Any,
        pane: int,  # real PaneSel,
        item: Rankable | None,
    ) -> None:
        pane = PaneSel(pane)
        wid = self._widget_for_pane(pane)
        if not item:
            wid.reset()
            return

        wid.set_match_plain(item)
        if wid is self.search:
            self._reset()
            self._toggle_text_mode(False)
            self.switch_to_source()

    def _on_source_changed(
        self,
        _sender: ty.Any,
        pane: int,  # real PaneSel,
        source: AnySource,
        at_root: bool,
        select: ty.Any,
    ) -> None:
        """Notification about a new data source, (represented object for the
        `self.search object`."""
        pane = PaneSel(pane)
        wid = self._widget_for_pane(pane)
        wid.set_source(source)
        wid.reset()
        if pane == PaneSel.SOURCE:
            self.switch_to_source()
            self.action.reset()

        if wid is self.current:
            self._toggle_text_mode(False)
            self._reset_to_toplevel = False
            # when `select` try to show selected item even on root
            if not at_root or select:
                self.reset_current(populate=True)
                wid.show_table_quirk()
                if select:
                    wid.set_match_leaf(select)

    def update_third(self) -> None:
        """Show or hide third panel according to _pane_three_is_visible state."""
        if self._pane_three_is_visible:
            self._ui_transition_timer.set_ms(200, self._show_third_pane, True)
        else:
            self._show_third_pane(False)

    def _on_mode_changed(
        self, _ctr: ty.Any, mode: int, _ignored: ty.Any
    ) -> None:
        """Show / hide third panel on mode changed."""
        if mode == PaneMode.SOURCE_ACTION_OBJECT:
            # use a delay before showing the third pane,
            # but set internal variable to "shown" already now
            self._pane_three_is_visible = True
            self._ui_transition_timer.set_ms(200, self._show_third_pane, True)
        else:
            self._pane_three_is_visible = False
            self._show_third_pane(False)

    def _show_third_pane(self, show: bool) -> None:
        """Set visibility of third panel to `show`."""
        self._ui_transition_timer.invalidate()
        self.third.set_visible(show)

    def _update_active(self) -> None:
        for panewidget in (self.action, self.search, self.third):
            if panewidget is not self.current:
                panewidget.set_state(Gtk.StateType.NORMAL)

            panewidget.match_view.inject_preedit(None)

        assert self.current

        if self._is_text_mode:  # or self._key_repeat_active:
            self.current.set_state(Gtk.StateType.ACTIVE)
        else:
            self.current.set_state(Gtk.StateType.SELECTED)
            self.current.match_view.inject_preedit(self._preedit)

        self._description_changed()

    def _switch_current(self, reverse: bool = False) -> None:
        # Only allow switch if we have match
        if self._pane_three_is_visible:
            curidx = self._pane_for_widget(self.current).value - 1
            newidx = (curidx - 1 if reverse else curidx + 1) % 3
        else:
            # for 2 panels simple switch to other one
            newidx = 0 if self.current == self.action else 1

        self._switch_current_to(newidx)

    def _switch_current_to(self, index: int) -> bool:
        """Switch selected pane.

        index: index (0, 1, or 2) of the pane to select.
        """
        order: tuple[LeafSearch, ActionSearch, LeafSearch] | tuple[
            LeafSearch, ActionSearch
        ]
        if self._pane_three_is_visible:
            order = (self.search, self.action, self.third)
        else:
            order = (self.search, self.action)

        if not (0 <= index <= len(order)):
            return False

        pane_before = order[max(index - 1, 0)]
        new_focus = order[index]
        no_match_ok = index == 0
        # Only allow switch if we have match in the pane before
        if (
            self.current
            and (no_match_ok or pane_before.get_match_state() is State.MATCH)
            and new_focus is not self.current
        ):
            self.current.hide_table()
            self.current = new_focus
            # Use toggle_text_mode to reset
            self._toggle_text_mode(False)
            pane = self._pane_for_widget(new_focus)
            if not pane:
                return False

            self._update_active()
            if self._data_ctrl.get_should_enter_text_mode(pane):
                self.toggle_text_mode_quick()

        return True

    def _browse_up(self) -> bool:
        if pane := self._pane_for_widget(self.current):
            return self._data_ctrl.browse_up(pane)

        return False

    def _browse_down(self, alternate: bool = False) -> None:
        if pane := self._pane_for_widget(self.current):
            self._data_ctrl.browse_down(pane, alternate=alternate)

    def _make_gui_ctx(self) -> uievents.GUIEnvironmentContext:
        event_time = Gtk.get_current_event_time()
        return uievents.gui_context_from_widget(event_time, self._widget)

    def _on_activate(self, _pane_owner: ty.Any, _current: ty.Any) -> None:
        self._data_ctrl.activate(ui_ctx=self._make_gui_ctx())

    def activate(self) -> None:
        """Activate current selection (Run action).

        NOTE: accelerator
        """
        self._on_activate(None, None)

    def execute_file(
        self,
        filepath: str,
        display: str,
        event_time: int,
    ) -> None:
        """Execute a .kfcom file"""

        def _handle_error(exc_info):
            _etype, exc, _tb = exc_info
            if not uiutils.show_notification(str(exc), icon_name="kupfer"):
                raise exc

        ctxenv = uievents.gui_context_from_keyevent(event_time, display)
        self._data_ctrl.execute_file(filepath, ctxenv, _handle_error)

    def _on_search_result(
        self,
        _sender: ty.Any,
        pane: int,  # real PaneSel
        matchrankable: Rankable | None,
        matches: ty.Iterable[Rankable],
        key: str | None,
    ) -> None:
        pane = PaneSel(pane)
        # NOTE: "Always-matching" search.
        # If we receive an empty match, we ignore it, to retain the previous
        # results. The user is not served by being met by empty results.
        if key and len(key) > 1 and matchrankable is None:
            # with typos or so, reset quicker
            self._latest_input_timer.set(
                _SLOW_INPUT_INTERVAL / 2, self._relax_search_terms
            )
            return

        wid = self._widget_for_pane(pane)
        wid.update_match(key, matchrankable, matches)

    def _widget_for_pane(self, pane: PaneSel) -> Search:
        # we have only 3 panels, so this is better than lookup in dict
        if pane == PaneSel.SOURCE:
            return self.search
        if pane == PaneSel.ACTION:
            return self.action
        if pane == PaneSel.OBJECT:
            return self.third

        raise ValueError(f"invalid pane value {pane}")

    def _pane_for_widget(self, widget: GObject.GObject) -> PaneSel:
        # we have only 3 panels, so this is better than lookup in dict
        if widget == self.search:
            return PaneSel.SOURCE
        if widget == self.action:
            return PaneSel.ACTION
        if widget == self.third:
            return PaneSel.OBJECT

        raise ValueError("invalid widget")

    def _on_object_stack_changed(
        self, controller: DataController, pane: int  # real PaneSel
    ) -> None:
        """Stack of objects (for comma trick) changed in @pane."""
        pane = PaneSel(pane)
        wid = self._widget_for_pane(pane)
        wid.set_object_stack(controller.get_object_stack(pane))

    def _on_pane_button_press(
        self, widget: Gtk.Widget, event: Gdk.EventButton
    ) -> bool:
        """mouse clicked on a pane widget - activate it."""
        # activate on double-click
        # pylint: disable=no-member,protected-access
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            self.activate()
            return True

        return False

    def _on_selection_changed(
        self, pane_owner: Search, match: Leaf | Action | None
    ) -> None:
        pane = self._pane_for_widget(pane_owner)
        if not pane:
            return

        self._data_ctrl.select(pane, match)
        if pane_owner is not self.current:
            return

        self._description_changed()

    def _description_changed(self) -> None:
        assert self.current
        match = self.current.get_current()
        # Use invisible WORD JOINER instead of empty, to maintain vertical size
        desc = match and match.get_description() or "\N{WORD JOINER}"
        desc = escape_markup_str(desc)
        markup = f"<small>{desc}</small>"
        self._label.set_markup(markup)

    def put_text(self, text: str) -> None:
        """Put @text into the interface to search, to use for "queries" from
        other sources."""
        self._try_enable_text_mode()
        self._entry.set_text(text)
        self._entry.set_position(-1)

    def put_files(self, fileuris: ty.Iterable[str], paths: bool) -> None:
        # don't consume iterable
        # self.output_debug("put-files:", list(fileuris))
        if paths:
            objs = (Gio.File.new_for_path(U).get_path() for U in fileuris)
        else:
            objs = (Gio.File.new_for_uri(U).get_path() for U in fileuris)

        if leaves := list(map(FileLeaf, filter(None, objs))):
            self._data_ctrl.insert_objects(
                PaneSel.SOURCE, ty.cast(list[Leaf], leaves)
            )

    def _reset_input_timer(self) -> None:
        # if input is slow/new, we reset
        self._latest_input_timer.set(
            _SLOW_INPUT_INTERVAL, self._relax_search_terms
        )

    def _on_preedit_im_changed(
        self, _editable: ty.Any, preedit_string: str
    ) -> None:
        """This is called whenever the input method changes its own preedit box.
        We take this opportunity to expand it."""
        if preedit_string:
            assert self.current
            self.current.match_view.expand_preedit(self._preedit)
            self._reset_input_timer()

        self._preedit_text = preedit_string

    def _on_preedit_insert_text(
        self, editable: Gtk.Entry, text: str, byte_length: int, position: int
    ) -> bool:
        # New text about to be inserted in preedit
        if text:
            self._entry.insert_text(text, -1)
            self._entry.set_position(-1)
            self._reset_input_timer()
            self._update_active()

        GObject.signal_stop_emission_by_name(editable, "insert-text")
        return False

    def _on_preedit_draw(self, widget: Gtk.Widget, _cr: ty.Any) -> bool:
        # draw nothing if hidden
        return widget.get_width_chars() == 0  # type: ignore

    def _on_entry_changed(self, editable: Gtk.Entry) -> None:
        """The entry changed callback. if text is blank, start search. Otherwise
        cancel search."""
        text = editable.get_text()

        # draw character count as icon
        editable.set_icon_from_pixbuf(Gtk.EntryIconPosition.SECONDARY, None)

        # cancel search and return if empty
        if not text:
            self._data_ctrl.cancel_search()
            # See if it was a deleting key press
            curev = Gtk.get_current_event()
            if (
                curev
                and curev.type == Gdk.EventType.KEY_PRESS
                and curev.keyval
                in (self._key_book["Delete"], self._key_book["BackSpace"])
            ):
                self._delete_from_stack()

            return

        # start search for updated query
        pane = self._pane_for_widget(self.current)
        assert pane
        if not self._is_text_mode and self._reset_to_toplevel:
            self.soft_reset(pane)

        self._data_ctrl.search(
            pane, key=text, context=text, text_mode=self._is_text_mode
        )

    def _on_up_key_press(self, shift_mask: int, mod_mask: int) -> bool:
        assert self.current
        self.current.go_up()
        return True

    def _on_down_key_press(self, shift_mask: int, mod_mask: int) -> bool:
        assert self.current

        if shift_mask and self.current == self.search:
            self.current.hide_table()
            self._switch_current()

        if (
            not self.current.get_current()
            and self.current.get_match_state() is State.WAIT
        ):
            self._populate_search()

        self.current.go_down()
        return True

    def _on_page_up_key_press(self, shift_mask: int, mod_mask: int) -> bool:
        assert self.current
        self.current.go_page_up()
        return True

    def _on_page_down_key_press(self, shift_mask: int, mod_mask: int) -> bool:
        assert self.current
        if (
            not self.current.get_current()
            and self.current.get_match_state() is State.WAIT
        ):
            self._populate_search()

        self.current.go_page_down()
        return True

    def _on_right_key_press(self, shift_mask: int, mod_mask: int) -> bool:
        # MOD1_MASK is alt/option
        self._browse_down(alternate=bool(mod_mask))
        return True

    def _on_backspace_key_press(self, shift_mask: int, mod_mask: int) -> bool:
        if not self._entry.get_text():  # not has_input
            self._delete_from_stack()
        elif not self._is_text_mode:
            self._entry.delete_text(self._entry.get_text_length() - 1, -1)
        else:
            return False
        return True

    def _on_tab_key_press(
        self, shift_mask: int, mod_mask: int, reverse: bool
    ) -> bool:
        self._switch_current(reverse=reverse)
        return True

    def _on_home_key_press(self, shift_mask: int, mod_mask: int) -> bool:
        assert self.current
        self.current.go_first()
        return True

    def _on_back_key_press(
        self, shift_mask: int = 0, mod_mask: int = 0
    ) -> bool:
        # leftarrow (or backspace without object stack)
        # delete/go up through stource stack
        assert self.current
        if self.current.is_showing_result():
            self.reset_current(populate=True)
        elif not self._browse_up():
            self._reset()
            self.reset_current()
            self._reset_to_toplevel = True

        self._reset_text()
        return True

    def _on_escape_key_press(self, shift_mask: int, mod_mask: int) -> bool:
        """Handle escape if first pane is reset, cancel (put away) self."""
        assert self.current

        if self.current.has_result():
            if self.current.is_showing_result():
                self.reset_current(populate=True)
            else:
                self.reset_current()
        else:
            if self._is_text_mode:
                self._toggle_text_mode(False)
            elif not self.current.get_table_visible():
                pane = self._pane_for_widget(self.current)
                self._data_ctrl.object_stack_clear(pane)
                self.emit("cancelled")

            self._reset_to_toplevel = True
            self.current.hide_table()

        self._reset_text()
        return True


GObject.type_register(Interface)
GObject.signal_new(
    "cancelled",
    Interface,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (),
)
# Send only when the interface itself launched an action directly
GObject.signal_new(
    "launched-action",
    Interface,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (),
)
