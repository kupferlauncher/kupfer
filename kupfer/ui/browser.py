from __future__ import annotations

import signal
import sys
import typing as ty
from contextlib import suppress

import cairo
from gi.repository import Gdk, GLib, Gtk

try:
    from gi.repository import AppIndicator3
except ImportError:
    AppIndicator3 = None

import kupfer.config
import kupfer.environment
from kupfer import version
from kupfer.core import settings, commandexec
from kupfer.core.datactrl import DataController
from kupfer.support import pretty, scheduler
from kupfer.ui import about, keybindings, kupferhelp, listen, uievents
from kupfer.ui import preferences
from kupfer.ui._support import text_direction_is_ltr
from kupfer.ui.interface import Interface

if ty.TYPE_CHECKING:
    from gettext import gettext as _


_KUPFER_CSS: ty.Final = b"""
#kupfer {
}

.matchview {
    border-radius: 0.6em;
}

#kupfer-preedit {
    padding: 0 0 0 0;
}

#kupfer-preedit.hidden {
    border-width: 0 0 0 0;
    padding: 0 0 0 0 ;
    margin: 0 0 0 0;
    outline-width: 0;
    min-height: 0;
    min-width: 0;
}

#kupfer-object-pane {
}

#kupfer-action-pane {
}

#kupfer-indirect-object-pane {
}

#kupfer-list {
}

#kupfer-list-view {
}

*:selected.matchview {
    background: alpha(@theme_selected_bg_color, 0.5);
    border: 2px solid alpha(black, 0.3)
}
"""

WINDOW_BORDER_WIDTH: ty.Final = 8


class WindowController(pretty.OutputMixin):
    """
    This is the fundamental Window (and App) Controller
    """

    def __init__(self):
        self._window: Gtk.Window = None
        self._current_screen_handler = 0
        self._interface: Interface = None  # type: ignore
        self._statusicon = None
        self._statusicon_ai = None
        self._window_hide_timer = scheduler.Timer()

    def _initialize(self, data_controller: DataController) -> None:
        self._window = Gtk.Window(
            type=Gtk.WindowType.TOPLEVEL,
            border_width=WINDOW_BORDER_WIDTH,
            decorated=False,
            name="kupfer",
        )
        # screen = self._window.get_screen()  # pylint: disable=no-member
        # if (visual := screen.get_rgba_visual()) and screen.is_composited():
        #     self._window.set_visual(visual)  # pylint: disable=no-member

        self._window.connect("realize", self._on_window_realize)
        self._window.connect("configure-event", self._on_window_configure_event)
        self._window.add_events(  # pylint: disable=no-member
            Gdk.EventMask.BUTTON_PRESS_MASK
        )
        data_controller.connect("launched-action", self._on_launch_action)
        data_controller.connect("command-result", self._on_command_result)

        self._interface = Interface(data_controller, self._window)
        self._interface.connect("launched-action", self._on_launch_action)
        self._interface.connect("cancelled", self._on_cancelled)
        self._window.connect("map-event", self._on_window_map_event)
        self._setup_window()

        # Accept drops
        self._window.drag_dest_set(  # pylint: disable=no-member
            Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY
        )
        self._window.drag_dest_add_uri_targets()  # pylint: disable=no-member
        self._window.drag_dest_add_text_targets()  # pylint: disable=no-member
        self._window.connect("drag-data-received", self._on_drag_data_received)

        signal.signal(signal.SIGINT, self._on_sigterm)
        signal.signal(signal.SIGTERM, self._on_sigterm)
        signal.signal(signal.SIGHUP, self._on_sigterm)

    def _on_window_map_event(self, *_args: ty.Any) -> None:
        self._interface.update_third()

    def _on_window_realize(self, widget: Gtk.Widget) -> None:
        # Load css
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(_KUPFER_CSS)

        Gtk.StyleContext.add_provider_for_screen(  # pylint: disable=no-member
            widget.get_screen(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _on_window_configure_event(
        self, widget: Gtk.Widget, event: Gdk.EventConfigure
    ) -> None:
        """Set main window rounded shape."""
        width, height = widget.get_size()
        radius = 10
        width_radius = width - radius
        height_radius = height - radius
        surface = cairo.ImageSurface(  # pylint: disable=no-member
            cairo.FORMAT_ARGB32, width, height  # pylint: disable=no-member
        )
        ctx = cairo.Context(surface)  # pylint: disable=no-member
        ctx.set_source_rgba(0.0, 0.0, 255.0, 128.0)
        ctx.set_operator(cairo.OPERATOR_SOURCE)  # pylint: disable=no-member
        ctx.move_to(radius, 0)
        ctx.line_to(width_radius, 0)
        ctx.arc(width_radius, radius, radius, 4.71, 6.28)
        ctx.line_to(width, height_radius)
        ctx.arc(width_radius, height_radius, radius, 0, 1.57)
        ctx.line_to(radius, height)
        ctx.arc(radius, height_radius, radius, 1.57, 3.14)
        ctx.line_to(0, radius)
        ctx.arc(radius, radius, radius, 3.14, 4.71)
        ctx.close_path()
        ctx.fill()
        reg = Gdk.cairo_region_create_from_surface(surface)
        widget.shape_combine_region(reg)

    def _show_statusicon(self) -> None:
        """Create (if not exists) and show status icon."""
        if not self._statusicon:
            status = Gtk.StatusIcon.new_from_icon_name(version.ICON_NAME)
            status.set_tooltip_text(version.PROGRAM_NAME)
            status.connect(
                "popup-menu", self._on_popup_menu, self._setup_menu()
            )
            status.connect("activate", self._on_statusicon_activate)
            self._statusicon = status

        with suppress(AttributeError):
            self._statusicon.set_visible(True)

    def _on_showstatusicon_changed(
        self,
        setctl: settings.SettingsController,
        section: str,
        key: str,
        value: ty.Any,
    ) -> None:
        """Callback from SettingsController - show / hide status icon on
        settings changed."""
        if value:
            self._show_statusicon()
        elif self._statusicon:
            # hide
            try:
                self._statusicon.set_visible(False)
            except AttributeError:
                self._statusicon = None

    def _show_statusicon_ai(self) -> None:
        """Show (create if not exists) status icon using AppIndicator3."""
        if AppIndicator3 is None:
            return

        if not self._statusicon_ai:
            indicator = AppIndicator3.Indicator.new(
                version.PROGRAM_NAME,
                version.ICON_NAME,
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            indicator.set_menu(self._setup_menu())
            self._statusicon_ai = indicator

        if self._statusicon_ai or AppIndicator3 is None:
            return

        self._statusicon_ai.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    def _showstatusicon_ai_changed(
        self,
        setctl: settings.SettingsController,
        section: str,
        key: str,
        value: ty.Any,
    ) -> None:
        """Show/Hide AppIndicator3 status icon on preferences change."""
        if AppIndicator3 is None:
            return

        if value:
            self._show_statusicon_ai()
        elif self._statusicon_ai:
            # hide
            self._statusicon_ai.set_status(
                AppIndicator3.IndicatorStatus.PASSIVE
            )

    def _setup_menu(self, context_menu: bool = False) -> Gtk.Menu:
        menu = Gtk.Menu()
        menu.set_name("kupfer-menu")

        def submenu_callback(
            menuitem: Gtk.MenuItem, callback: ty.Callable[[], None]
        ) -> bool:
            callback()
            return True

        def add_menu_item(
            icon: str | None,
            callback: ty.Callable[..., None],
            label: str | None = None,
            with_ctx: bool = True,
        ) -> None:
            def mitem_handler(
                menuitem: Gtk.MenuItem, callback: ty.Callable[..., None]
            ) -> bool:
                if with_ctx:
                    ui_ctx = uievents.gui_context_from_widget(
                        Gtk.get_current_event_time(), menuitem
                    )
                    callback(ui_ctx)
                else:
                    callback()

                if context_menu:
                    self.put_away()

                return True

            if label and not icon:
                mitem = Gtk.MenuItem(label=label)
            else:
                mitem = Gtk.ImageMenuItem.new_from_stock(icon)

            mitem.connect("activate", mitem_handler, callback)
            menu.append(mitem)

        if context_menu:
            add_menu_item(Gtk.STOCK_CLOSE, self.put_away, with_ctx=False)
        else:
            add_menu_item(None, self._on_activate, _("Show Main Interface"))

        menu.append(Gtk.SeparatorMenuItem())
        if context_menu:
            for name, func in self._interface.get_context_actions():
                mitem = Gtk.MenuItem(label=name)
                mitem.connect("activate", submenu_callback, func)
                menu.append(mitem)

            menu.append(Gtk.SeparatorMenuItem())

        add_menu_item(Gtk.STOCK_PREFERENCES, preferences.show_preferences)
        add_menu_item(Gtk.STOCK_HELP, kupferhelp.show_help)
        add_menu_item(Gtk.STOCK_ABOUT, about.show_about_dialog)
        menu.append(Gtk.SeparatorMenuItem())
        add_menu_item(Gtk.STOCK_QUIT, self._on_quit, with_ctx=False)
        menu.show_all()

        return menu

    def _setup_window(self) -> None:
        """Returns window."""
        self._window.connect("delete-event", self._on_close_window)
        self._window.connect("focus-out-event", self._on_lost_focus)
        self._window.connect(
            "button-press-event", self._on_window_frame_clicked
        )
        widget = self._interface.get_widget()
        widget.show()

        # Build the window frame with its top bar
        topbar = Gtk.HBox()

        vbox = Gtk.VBox()
        vbox.pack_start(topbar, False, False, 0)
        vbox.pack_start(widget, True, True, 0)
        vbox.show()
        self._window.add(vbox)  # pylint: disable=no-member

        title = Gtk.Label.new("")
        button = Gtk.Label.new("")
        l_programname = version.PROGRAM_NAME.lower()
        # The text on the general+context menu button
        btext = f"<b>{l_programname} ⚙</b>"
        button.set_markup(btext)
        button_box = Gtk.EventBox()
        button_box.set_visible_window(False)
        button_adj = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        button_adj.set_padding(0, 2, 0, 3)
        button_adj.add(button)
        button_box.add(button_adj)
        button_box.connect("button-press-event", self._on_context_menu_clicked)
        button_box.connect(
            "enter-notify-event", self._on_button_enter, button, btext
        )
        button_box.connect(
            "leave-notify-event", self._on_button_leave, button, btext
        )
        button.set_name("kupfer-menu-button")
        title_align = Gtk.Alignment.new(0, 0.5, 0, 0)
        title_align.add(title)
        topbar.pack_start(title_align, True, True, 0)
        topbar.pack_start(button_box, False, False, 0)
        topbar.show_all()

        self._window.set_title(version.PROGRAM_NAME)
        self._window.set_icon_name(version.ICON_NAME)
        self._window.set_type_hint(  # pylint: disable=no-member
            self._create_window_type_hint()
        )
        self._window.set_property("skip-taskbar-hint", True)
        self._window.set_keep_above(True)  # pylint: disable=no-member
        if (pos := self._create_window_position()) != Gtk.WindowPosition.NONE:
            self._window.set_position(pos)  # pylint: disable=no-member

        if not text_direction_is_ltr():
            self._window.set_gravity(  # pylint: disable=no-member
                Gdk.GRAVITY_NORTH_EAST
            )
        # Setting not resizable changes from utility window
        # on metacity
        self._window.set_resizable(False)

    def _create_window_type_hint(self) -> Gdk.WindowTypeHint:
        """Create window type hints according to WINDOW_TYPE_HINT env setting."""
        type_hint = Gdk.WindowTypeHint.UTILITY
        hint_name = kupfer.config.get_kupfer_env("WINDOW_TYPE_HINT").upper()
        if not hint_name:
            return type_hint

        if hint_enum := getattr(Gdk.WindowTypeHint, hint_name, None):
            return hint_enum

        self.output_error("No such Window Type Hint", hint_name)
        self.output_error("Existing type hints:")
        for name in dir(Gdk.WindowTypeHint):
            if name.upper() == name:
                self.output_error(name)

        return type_hint

    def _create_window_position(self) -> Gtk.WindowPosition:
        """Create window position according to WINDOW_POSITION env setting."""
        value = Gtk.WindowPosition.NONE
        hint_name = kupfer.config.get_kupfer_env("WINDOW_POSITION").upper()
        if not hint_name:
            return value

        if hint_enum := getattr(Gtk.WindowPosition, hint_name, None):
            return hint_enum

        self.output_error("No such Window Position", hint_name)
        self.output_error("Existing values:")
        for name in dir(Gtk.WindowPosition):
            if name.upper() == name:
                self.output_error(name)

        return value

    def _on_window_frame_clicked(
        self, widget: Gtk.Widget, event: Gdk.EventButton
    ) -> None:
        """Start drag when the window is clicked"""
        widget.begin_move_drag(
            event.button, int(event.x_root), int(event.y_root), event.time
        )

    def _on_context_menu_clicked(
        self, widget: Gtk.Widget, event: Gdk.EventButton
    ) -> bool:
        """The context menu label was clicked"""
        menu = self._setup_menu(True)
        menu.set_screen(self._window.get_screen())  # pylint: disable=no-member
        menu.popup(None, None, None, None, event.button, event.time)
        return True

    def _on_button_enter(
        self,
        widget: Gtk.Widget,
        event: Gdk.EventCrossing,
        button: Gtk.Widget,
        udata: str,
    ) -> None:
        """Pointer enters context menu button"""
        button.set_markup(f"<u>{udata}</u>")

    def _on_button_leave(
        self,
        widget: Gtk.Widget,
        event: Gdk.EventCrossing,
        button: Gtk.Widget,
        udata: str,
    ) -> None:
        """Pointer leaves context menu button"""
        button.set_markup(udata)

    def _on_popup_menu(
        self,
        status_icon: Gtk.StatusIcon,
        button: int,
        activate_time: float,
        menu: Gtk.Menu,
    ) -> None:
        """When the StatusIcon is right-clicked."""
        menu.popup(
            None,
            None,
            Gtk.StatusIcon.position_menu,
            status_icon,
            button,
            activate_time,
        )

    def _on_launch_action(self, sender: ty.Any, *_args: ty.Any) -> None:
        """Callback for launch-action event: hide window.

        Separate window hide from the action being done. This is to solve
        a window focus bug when we switch windows using an action.
        """
        self._interface.did_launch()
        self._window_hide_timer.set_ms(100, self.put_away)

    def _on_command_result(
        self,
        sender: DataController,
        result_type: int,
        ui_ctx: uievents.GUIEnvironmentContext,
    ) -> None:
        """Callback for command-result event: update window."""
        result_type = commandexec.ExecResult(result_type)
        # handle "refresh" result
        if result_type == commandexec.ExecResult.REFRESH:
            self.output_debug("refresh leaves list")
            self._interface.reset_current()
            self._interface.did_launch()
            return

        self._interface.did_get_result()
        if ui_ctx:
            self._on_present(
                sender, ui_ctx.get_display(), ui_ctx.get_timestamp()
            )
        else:
            self._on_present(sender, "", Gtk.get_current_event_time())

    def _on_lost_focus(self, window: Gtk.Window, event: Gdk.EventFocus) -> None:
        """Hide window on lost focus."""
        if not kupfer.config.has_capability("HIDE_ON_FOCUS_OUT"):
            return
        # Close at unfocus.
        # Since focus-out-event is triggered even when we click inside the
        # window, we'll do some additional math to make sure that
        # that window won't close if the mouse pointer is over it.
        _gdkwindow, x, y, _mods = (
            window.get_screen().get_root_window().get_pointer()
        )
        w_x, w_y = window.get_position()
        w_w, w_h = window.get_size()
        if not (w_x <= x <= w_x + w_w and w_y <= y <= w_y + w_h):
            self._window_hide_timer.set_ms(50, self.put_away)

    def _on_monitors_changed(self, *_ignored: ty.Any) -> None:
        """Center window on monitor changed."""
        self._center_window()

    def _window_put_on_screen(self, screen: Gdk.Screen) -> None:
        """Move window to `screen`."""
        if self._current_screen_handler:
            scr = self._window.get_screen()  # pylint: disable=no-member
            scr.disconnect(self._current_screen_handler)

        self._window.set_screen(screen)  # pylint: disable=no-member
        self._current_screen_handler = screen.connect(
            "monitors-changed", self._on_monitors_changed
        )

    def _center_window(self, displayname: str | None = None) -> None:
        """Center Window on the monitor the pointer is currently on"""
        # pylint: disable=no-member
        if not displayname and self._window.has_screen():
            display = self._window.get_display()
        else:
            display = uievents.GUIEnvironmentContext.ensure_display_open(
                displayname
            )

        screen, x, y, _mod = display.get_pointer()
        self._window_put_on_screen(screen)
        monitor_nr = screen.get_monitor_at_point(x, y)
        geo = screen.get_monitor_geometry(monitor_nr)
        wid, hei = self._window.get_size()
        midx = geo.x + geo.width / 2 - wid / 2
        midy = geo.y + geo.height / 2 - hei / 2

        self._window.move(midx, midy)
        uievents.try_close_unused_displays(screen)

    def _should_recenter_window(self) -> bool:
        """Return True if the mouse pointer and the window are on different
        monitors."""
        # Check if the GtkWindow was realized yet
        if not self._window.get_realized():
            return True

        # pylint: disable=no-member
        display = self._window.get_screen().get_display()
        screen, x, y, _modifiers = display.get_pointer()
        mon_cur = screen.get_monitor_at_point(x, y)
        mon_win = screen.get_monitor_at_window(self._window.get_window())
        return mon_cur != mon_win  # type: ignore

    def _on_activate(self, sender: ty.Any = None) -> None:
        """Activate (show) main windows."""
        # pylint: disable=no-member
        dispname = self._window.get_screen().make_display_name()
        self._on_present(sender, dispname, Gtk.get_current_event_time())

    def _on_present(
        self, sender: ty.Any, display: str | None, timestamp: int
    ) -> None:
        """Present on @display, where None means default display"""
        self._window_hide_timer.invalidate()
        display = display or Gdk.Display.get_default().get_name()
        # Center window before first show
        if not self._window.get_realized():
            self._center_window(display)

        self._window.stick()  # pylint: disable=no-member
        self._window.present_with_time(timestamp)
        # pylint: disable=no-member
        self._window.get_window().focus(timestamp=timestamp)
        self._interface.focus()

        # Center after present if we are moving between monitors
        if self._should_recenter_window():
            self._center_window(display)

    def put_away(self) -> None:
        """Hide main window."""
        self._interface.put_away()
        self._window.hide()

    def _on_cancelled(self, _obj: Interface) -> None:
        self.put_away()

    def _on_show_hide(
        self, sender: ty.Any, display: str, timestamp: int
    ) -> None:
        """Toggle activate/put-away."""
        if self._window.get_property("visible"):
            self.put_away()
        else:
            self._on_present(sender, display, timestamp)
            # refresh current match (if has qf_id)
            self._interface.re_search_kpfer()

    def _on_statusicon_activate(self, sender: Gtk.StatusIcon) -> None:
        """GtkStatusIcon callback"""
        self._on_show_hide(sender, "", Gtk.get_current_event_time())

    def _on_key_binding(
        self,
        keyobj: keybindings.KeyboundObject,
        keybinding_number: int,
        display: str,
        timestamp: int,
    ) -> None:
        """Keybinding activation callback"""
        if keybinding_number == keybindings.KEYBINDING_TARGET_DEFAULT:
            self._on_show_hide(keyobj, display, timestamp)

        elif keybinding_number == keybindings.KEYBINDING_TARGET_MAGIC:
            self._on_present(keyobj, display, timestamp)
            self._interface.select_selected_text()
            self._interface.select_selected_file()

    def _on_drag_data_received(
        self,
        widget: Gtk.Widget,
        context: ty.Any,
        x: int,
        y: int,
        data_: Gtk.SelectionData,
        info: ty.Any,
        time: int,
    ) -> None:
        if uris := data_.get_uris():
            self._interface.put_files(uris, paths=False)
        else:
            self._interface.put_text(data_.get_text())

    def _on_put_text(
        self, sender: Gtk.Widget, text: str, display: str, timestamp: int
    ) -> None:
        """We got a search text from dbus"""
        self._on_present(sender, display, timestamp)
        self._interface.put_text(text)

    def _on_put_files(
        self,
        sender: ty.Any,
        fileuris: ty.Iterable[str],
        display: str,
        timestamp: int,
    ) -> None:
        self._on_present(sender, display, timestamp)
        self._interface.put_files(fileuris, paths=True)

    def _on_find_object(
        self, sender: ty.Any, qpfer: str, display: str, timestamp: int
    ) -> None:
        self._on_present(sender, display, timestamp)
        self._interface.find_object(qpfer)

    def _on_execute_file(
        self,
        sender: ty.Any,
        filepath: str,
        display: str,
        timestamp: int,
    ) -> None:
        self._interface.execute_file(filepath, display, timestamp)

    def _on_close_window(self, window: Gtk.Widget, event: ty.Any) -> bool:
        """Callback for main window delete-event."""
        self.put_away()
        return True

    def _on_sigterm(self, signal_: int, _frame: ty.Any) -> None:
        self.output_info("Caught signal", signal_, "exiting..")
        self._on_quit()

    def _on_early_interrupt(self, _signal: int, _frame: ty.Any) -> None:
        sys.exit(1)

    def save_data(self) -> None:
        """Save state before quit"""
        sch = scheduler.get_scheduler()
        sch.finish()
        self._interface.save_config()

    def _on_quit(self, sender: Gtk.Widget | None = None) -> None:
        Gtk.main_quit()

    def _quit_now(self) -> None:
        """Quit immediately (state save should already be done)"""
        raise SystemExit

    def _on_session_save(self, *_args: ty.Any) -> bool:
        """Old-style session save callback.  Return True on successful."""
        # No quit, only save
        self.output_info("Saving for logout...")
        self.save_data()
        return True

    def _on_session_die(self, *_args: ty.Any) -> None:
        """Session callback on session end: quit now, without saving, since we
        already do that on Session save!
        """
        self._quit_now()

    def lazy_setup(self) -> None:
        """Do all setup that can be done after showing main interface.
        Connect to desktop services (keybinding callback, session logout
        callbacks etc).
        """
        # pylint: disable=import-outside-toplevel
        from kupfer.ui import session

        self.output_debug("in lazy_setup")

        setctl = settings.get_settings_controller()
        if setctl.get_show_status_icon():
            self._show_statusicon()

        if setctl.get_show_status_icon_ai():
            self._show_statusicon_ai()

        setctl.connect(
            "value-changed::kupfer.showstatusicon",
            self._on_showstatusicon_changed,
        )
        setctl.connect(
            "value-changed::kupfer.showstatusicon_ai",
            self._showstatusicon_ai_changed,
        )

        if keystr := setctl.get_keybinding():
            succ = keybindings.bind_key(keystr)
            self.output_info(
                f"Trying to register {keystr} to spawn kupfer.. "
                + ("success" if succ else "failed")
            )

        if magickeystr := setctl.get_magic_keybinding():
            succ = keybindings.bind_key(
                magickeystr, keybindings.KEYBINDING_TARGET_MAGIC
            )
            self.output_debug(
                f"Trying to register {magickeystr} to spawn kupfer.. "
                + ("success" if succ else "failed")
            )

        keyobj = keybindings.get_keybound_object()
        keyobj.connect("keybinding", self._on_key_binding)

        client = session.SessionClient()
        client.connect("save-yourself", self._on_session_save)
        client.connect("die", self._on_session_die)
        self._interface.lazy_setup()

        self.output_debug("finished lazy_setup")

    def main(self, quiet: bool = False) -> None:
        """Start WindowController, present its window (if not @quiet)"""
        signal.signal(signal.SIGINT, self._on_early_interrupt)

        kserv1 = None
        kserv2 = None

        try:
            # NOTE: For a *very short* time we will use both APIs  TOOD: off one
            kserv1 = listen.Service()
            kserv2 = listen.ServiceNew()
        except listen.AlreadyRunningError:
            self.output_info("An instance is already running, exiting...")
            self._quit_now()
        except listen.NoConnectionError:
            pass

        if kserv1:
            keyobj = keybindings.get_keybound_object()
            keyobj.connect(
                "bound-key-changed",
                lambda x, y, z: kserv1.BoundKeyChanged(y, z),
            )
            kserv1.connect("relay-keys", keyobj.relayed_keys)

        # Load data
        data_controller = DataController.instance()
        sch = scheduler.get_scheduler()
        sch.load()
        # Now create UI and display
        self._initialize(data_controller)
        sch.display()

        for kserv in (kserv1, kserv2):
            if kserv:
                kserv.connect("present", self._on_present)
                kserv.connect("show-hide", self._on_show_hide)
                kserv.connect("put-text", self._on_put_text)
                kserv.connect("put-files", self._on_put_files)
                kserv.connect("find-object", self._on_find_object)
                kserv.connect("execute-file", self._on_execute_file)
                kserv.connect("quit", self._on_quit)

        if not quiet:
            self._on_activate()

        GLib.idle_add(self.lazy_setup)

        def do_main_iterations(max_events=0):
            # use sentinel form of iter
            for idx, _pending in enumerate(iter(Gtk.events_pending, False)):
                if max_events and idx > max_events:
                    break

                Gtk.main_iteration()

        try:
            Gtk.main()
            # put away window *before exiting further*
            self.put_away()
            do_main_iterations(10)
        finally:
            self.save_data()

        # tear down but keep hanging
        for kserv in (kserv1, kserv2):
            if kserv:
                kserv.unregister()

        keybindings.bind_key(None, keybindings.KEYBINDING_TARGET_DEFAULT)
        keybindings.bind_key(None, keybindings.KEYBINDING_TARGET_MAGIC)

        do_main_iterations(100)
        # if we are still waiting, print a message
        if Gtk.events_pending():
            self.output_info("Waiting for tasks to finish...")
            do_main_iterations()
