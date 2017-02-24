# -*- coding: UTF-8 -*-

import io
import itertools
import signal
import sys
import textwrap

import gi
from gi.repository import Gtk, Gdk, GObject
from gi.repository import GLib, Gio, Pango
from gi.repository import GdkPixbuf

try:
    gi.require_version("AppIndicator3", "0.1")
except ValueError:
    AppIndicator3 = None
else:
    from gi.repository import AppIndicator3

import cairo

from kupfer import kupferui
from kupfer import version

from kupfer import scheduler
from kupfer.ui import accelerators
from kupfer.ui import keybindings
from kupfer.ui import listen
from kupfer.ui import uievents
from kupfer.core import data, relevance, learn
from kupfer.core import settings
from kupfer import icons
from kupfer import interface
from kupfer import pretty
import kupfer.config
import kupfer.environment

ELLIPSIZE_MIDDLE = Pango.EllipsizeMode.MIDDLE


_escape_table = {
        ord("&"): "&amp;",
        ord("<"): "&lt;",
        ord(">"): "&gt;",
    }

def tounicode(ustr):
    if isinstance(ustr, str):
        return ustr
    return ustr.decode("UTF-8", "replace")

def escape_markup_str(mstr):
    """
    Use a simeple homegrown replace table to replace &, <, > with
    entities in @mstr
    """
    return tounicode(mstr).translate(_escape_table)

def text_direction_is_ltr():
    return Gtk.Widget.get_default_direction() != Gtk.TextDirection.RTL

def make_rounded_rect(cr,x,y,width,height,radius):
    """
    Draws a rounded rectangle with corners of @radius
    """
    MPI = 3.1415926535897931
    cr.save()

    w,h = width, height

    cr.move_to(radius, 0)
    cr.line_to(w-radius,0)
    cr.arc(w-radius, radius, radius, 3*MPI/2, 2*MPI)
    cr.line_to(w, h-radius)
    cr.arc(w-radius, h-radius, radius, 0, MPI/2)
    cr.line_to(radius, h)
    cr.arc(radius, h-radius, radius, MPI/2, MPI)
    cr.line_to(0, radius)
    cr.arc(radius, radius, radius, MPI, 3*MPI/2)
    cr.close_path()
    cr.restore()

def get_glyph_pixbuf(text, sz, center_vert=True, color=None):
    """Return pixbuf for @text

    if @center_vert, then center completely vertically
    """
    margin = sz * 0.1
    ims = cairo.ImageSurface(cairo.FORMAT_ARGB32, sz, sz)
    cc = cairo.Context(ims)

    cc.move_to(margin, sz-margin)
    cc.set_font_size(sz/2)
    if color is None:
        cc.set_source_rgba(0,0,0,1)
    else:
        cc.set_source_rgb(*color)

    cc.text_path(text)
    x1, y1, x2, y2 =cc.path_extents()
    skew_horiz = ((sz-x2) - (x1))/2.0
    skew_vert = ((sz-y2) - (y1))/2.0
    if not center_vert:
        skew_vert = skew_vert*0.2 - margin*0.5
    cc.new_path()
    cc.move_to(margin+skew_horiz, sz-margin+skew_vert)
    cc.text_path(text)
    cc.fill()

    ims.flush()
    f = io.BytesIO()
    ims.write_to_png(f)

    loader = GdkPixbuf.PixbufLoader()
    loader.write(f.getvalue())
    loader.close()

    return loader.get_pixbuf()


# State Constants
class State (object):
    Wait, Match, NoMatch = (1,2,3)

class LeafModel (object):
    """A base for a tree view
    With a magic load-on-demand feature.

    self.set_base will set its base iterator
    and self.populate(num) will load @num items into
    the model

    Attributes:
    icon_size
    """
    def __init__(self):
        """
        First column is always the object -- returned by get_object
        it needs not be specified in columns
        """
        columns = (GObject.TYPE_OBJECT, str, str, str, str)
        self.store = Gtk.ListStore(GObject.TYPE_PYOBJECT, *columns)
        self.object_column = 0
        self.base = None
        self._setup_columns()
        self.icon_size = 32

    def __len__(self):
        return len(self.store)

    def _setup_columns(self):
        self.icon_col = 1
        self.name_col = 2
        self.fav_col = 3
        self.info_col = 4
        self.rank_col = 5

        # only show in debug mode
        show_rank_col = pretty.debug

        # Name and description column
        # Expands to the rest of the space
        name_cell = Gtk.CellRendererText()
        name_cell.set_property("ellipsize", ELLIPSIZE_MIDDLE)
        name_col = Gtk.TreeViewColumn("item", name_cell)
        name_col.set_expand(True)
        name_col.add_attribute(name_cell, "markup", self.name_col)

        fav_cell = Gtk.CellRendererText()
        fav_col = Gtk.TreeViewColumn("fav", fav_cell)
        fav_col.add_attribute(fav_cell, "text", self.fav_col)

        info_cell = Gtk.CellRendererText()
        info_col = Gtk.TreeViewColumn("info", info_cell)
        info_col.add_attribute(info_cell, "text", self.info_col)

        nbr_cell = Gtk.CellRendererText()
        nbr_col = Gtk.TreeViewColumn("rank", nbr_cell)
        nbr_cell.set_property("width-chars", 3)
        nbr_col.add_attribute(nbr_cell, "text", self.rank_col)

        icon_cell = Gtk.CellRendererPixbuf()
        #icon_cell.set_property("height", 32)
        #icon_cell.set_property("width", 32)
        #icon_cell.set_property("stock-size", Gtk.IconSize.LARGE_TOOLBAR)

        icon_col = Gtk.TreeViewColumn("icon", icon_cell)
        icon_col.add_attribute(icon_cell, "pixbuf", self.icon_col)

        self.columns = [icon_col, name_col, fav_col, info_col,]
        if show_rank_col:
            self.columns += (nbr_col, )

    def _get_column(self, treepath, col):
        it = self.store.get_iter(treepath)
        val = self.store.get_value(it, col)
        return val

    def get_object(self, path):
        if path is None:
            return
        return self._get_column(path, self.object_column)

    def get_store(self):
        return self.store

    def clear(self):
        """Clear the model and reset its base"""
        self.store.clear()
        self.base = None

    def set_base(self, baseiter):
        self.base = iter(baseiter)

    def populate(self, num=None):
        """
        populate model with num items from its base
        and return first item inserted
        if num is none, insert everything
        """
        if not self.base:
            return None
        if num:
            iterator = itertools.islice(self.base, num)
        first = None
        for item in iterator:
            self.add(item)
            if not first: first = item.object
        # first.object is a leaf
        return first

    def _get_row(self, rankable):
        """Use the UI description functions get_*
        to initialize @rankable into the model
        """
        leaf, rank = rankable.object, rankable.rank
        icon = self.get_icon(leaf)
        markup = self.get_label_markup(rankable)
        fav = self.get_fav(leaf)
        info = self.get_aux_info(leaf)
        rank_str = self.get_rank_str(rank)
        return (rankable, icon, markup, fav, info, rank_str)

    def add(self, rankable):
        self.store.append(self._get_row(rankable))

    def add_first(self, rankable):
        self.store.prepend(self._get_row(rankable))

    def get_icon(self, leaf):
        sz = self.icon_size
        if sz >= 8:
            return leaf.get_thumbnail(sz, sz) or leaf.get_pixbuf(sz)

    def get_label_markup(self, rankable):
        leaf = rankable.object
        # Here we use the items real name
        # Previously we used the alias that was matched,
        # but it can be too confusing or ugly
        name = escape_markup_str(str(leaf))
        desc = escape_markup_str(leaf.get_description() or "")
        if desc:
            text = '%s\n<small>%s</small>' % (name, desc, )
        else:
            text = '%s' % (name, )
        return text

    def get_fav(self, leaf):
        # fav: display star if it's a favourite
        if learn.is_favorite(leaf):
            return "\N{BLACK STAR}"
        else:
            return ""

    def get_aux_info(self, leaf):
        # info: display arrow if leaf has content
        if hasattr(leaf, "has_content") and leaf.has_content():
            if text_direction_is_ltr():
                return "\N{BLACK RIGHT-POINTING SMALL TRIANGLE} "
            else:
                return "\N{BLACK LEFT-POINTING SMALL TRIANGLE} "
        else:
            return ""

    def get_rank_str(self, rank):
        # Display rank empty instead of 0 since it looks better
        return str(int(rank)) if rank else ""

class MatchView (Gtk.Bin, pretty.OutputMixin):
    """
    A Widget for displaying name, icon and underlining properly if
    it matches
    """
    __gtype_name__ = "MatchView"

    def __init__(self):
        GObject.GObject.__init__(self)
        # object attributes
        self.label_char_width = 25
        self.preedit_char_width = 5
        self.match_state = State.Wait

        self.object_stack = []

        self.connect("realize", self._update_theme)
        self.connect("style-set", self._update_theme)
        # finally build widget
        self.build_widget()
        self.cur_icon = None
        self.cur_text = None
        self.cur_match = None
        self._icon_size = None
        self._read_icon_size()

    @property
    def icon_size(self):
        return self._icon_size

    def _icon_size_changed(self, setctl, section, key, value):
        self._icon_size = setctl.get_config_int("Appearance", "icon_large_size")

    def _read_icon_size(self, *args):
        setctl = settings.GetSettingsController()
        setctl.connect("value-changed::appearance.icon_large_size",
                       self._icon_size_changed)
        self._icon_size_changed(setctl, None, None, None)
        
    def _update_theme(self, *args):
        # Style subtables to choose from
        # fg, bg, text, base
        # light, mid, dark

        # Use a darker color for selected state
        # leave active state as preset
        #selectedc = self.style.dark[Gtk.StateType.SELECTED]
        #self.event_box.modify_bg(Gtk.StateType.SELECTED, selectedc)
                pass

    def build_widget(self):
        """
        Core initalization method that builds the widget
        """
        self.label = Gtk.Label.new("<match>")
        self.label.set_single_line_mode(True)
        self.label.set_width_chars(self.label_char_width)
        self.label.set_max_width_chars(self.label_char_width)
        self.label.set_ellipsize(ELLIPSIZE_MIDDLE)
        self.icon_view = Gtk.Image()

        # infobox: icon and match name
        icon_align = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        icon_align.set_property("top-padding", 5)
        icon_align.add(self.icon_view)
        infobox = Gtk.HBox()
        infobox.pack_start(icon_align, True, True, 0)
        box = Gtk.VBox()
        box.pack_start(infobox, True, False, 0)
        self._editbox = Gtk.HBox()
        self._editbox.pack_start(self.label, True, True, 0)
        box.pack_start(self._editbox, False, True, 0)
        self.event_box = Gtk.EventBox()
        self.event_box.add(box)
        self.event_box.get_style_context().add_class("matchview")
        self.add(self.event_box)
        self.event_box.show_all()
        self.__child = self.event_box


    # No do_size_allocate here, we just use the default
    def do_forall (self, include_internals, callback, *user_data):
        callback (self.__child, *user_data)

    def _render_composed_icon(self, base, pixbufs, small_size):
        """
        Render the main selection + a string of objects on the stack.

        Scale the main image into the upper portion, leaving a clear
        strip at the bottom where we line up the small icons.

        @base: main selection pixbuf
        @pixbufs: icons of the object stack, in final (small) size
        @small_size: the size of the small icons
        """
        sz = self.icon_size
        base_scale = min((sz-small_size)*1.0/base.get_height(),
                sz*1.0/base.get_width())
        new_sz_x = int(base_scale*base.get_width())
        new_sz_y = int(base_scale*base.get_height())
        if not base.get_has_alpha():
            base = base.add_alpha(False, 0, 0, 0)
        destbuf = base.scale_simple(sz, sz, GdkPixbuf.InterpType.NEAREST)
        destbuf.fill(0x00000000)
        # Align in the middle of the area
        offset_x = (sz - new_sz_x)/2
        offset_y = ((sz - small_size) - new_sz_y)/2
        base.composite(destbuf, offset_x, offset_y, new_sz_x, new_sz_y,
                offset_x, offset_y,
                base_scale, base_scale, GdkPixbuf.InterpType.BILINEAR, 255)

        # @fr is the scale compared to the destination pixbuf
        fr = small_size*1.0/sz
        dest_y = offset_y = int((1-fr)*sz)
        n_small = sz // small_size
        for idx, pbuf in enumerate(list(pixbufs[-n_small:])):
            dest_x = offset_x = int(fr*sz)*idx
            pbuf.copy_area(0,0, small_size,small_size, destbuf, dest_x,dest_y)
        return destbuf

    def update_match(self):
        """
        Update interface to display the currently selected match
        """
        # update icon
        icon = self.cur_icon
        if icon:
            if self.match_state is State.NoMatch:
                icon = self._dim_icon(icon)
            if icon and self.object_stack:
                small_max = 16
                small_size = 16
                pixbufs = [o.get_pixbuf(small_size) for o in
                        self.object_stack[-small_max:]]
                icon = self._render_composed_icon(icon, pixbufs, small_size)
            self.icon_view.set_from_pixbuf(icon)
        else:
            self.icon_view.clear()
            self.icon_view.set_pixel_size(self.icon_size)

        if not self.cur_text:
            self.label.set_text("")
            return

        if not self.cur_match:
            if self.match_state is not State.Match:
                # Allow markup in the text string if we have no match
                self.label.set_markup(self.cur_text)
            else:
                self.label.set_text(self.cur_text)
            return

        # update the text label
        text = str(self.cur_text)
        key = str(self.cur_match).lower()

        format_match=(lambda m: "<u><b>%s</b></u>" % escape_markup_str(m))
        markup = relevance.formatCommonSubstrings(text, key,
                format_clean=escape_markup_str,
                format_match=format_match)

        self.label.set_markup(markup)

    @classmethod
    def _dim_icon(cls, icon):
        if not icon:
            return icon
        dim_icon = icon.copy()
        dim_icon.fill(0)
        icon.composite(dim_icon,
                       0, 0,
                       icon.get_width(), icon.get_height(),
                       0, 0,
                       1., 1.,
                       GdkPixbuf.InterpType.NEAREST,
                       127)
        return dim_icon

    def set_object(self, text, icon, update=True):
        self.cur_text = text
        self.cur_icon = icon
        if update:
            self.update_match()

    def set_match(self, match=None, state=None, update=True):
        self.cur_match = match
        if state:
            self.match_state = state
        else:
            self.match_state = (State.NoMatch, State.Match)[self.cur_match != None]
        if update:
            self.update_match()

    def set_match_state(self, text, icon, match=None, state=None, update=True):
        self.set_object(text,icon, update=False)
        self.set_match(match, state, update=False)
        if update:
            self.update_match()

    def set_match_text(self, text, update=True):
        self.cur_match = text
        if update:
            self.update_match()

    def expand_preedit(self, preedit):
        new_label_width = self.label_char_width - self.preedit_char_width
        self.label.set_width_chars(new_label_width)
        preedit.set_width_chars(self.preedit_char_width)
        preedit.get_style_context().remove_class(PREEDIT_HIDDEN_CLASS)

    def shrink_preedit(self, preedit):
        self.label.set_width_chars(self.label_char_width)
        preedit.set_width_chars(0)
        preedit.get_style_context().add_class(PREEDIT_HIDDEN_CLASS)

    def inject_preedit(self, preedit):
        """
        @preedit: Widget to be injected or None
        """
        if preedit:
            old_parent = preedit.get_parent()
            if old_parent:
                old_parent.remove(preedit)
            self.shrink_preedit(preedit)
            self._editbox.pack_start(preedit, False, True, 0)
            #selectedc = self.style.dark[Gtk.StateType.SELECTED]
            #preedit.modify_bg(Gtk.StateType.SELECTED, selectedc)
            preedit.show()
            preedit.grab_focus()
        else:
            self.label.set_width_chars(self.label_char_width)
            self.label.set_alignment(.5,.5)

GObject.type_register(MatchView)
CORNER_RADIUS = 15
#Gtk.widget_class_install_style_property(MatchView, ('corner-radius', GObject.TYPE_INT, 'Corner radius', 'Radius of bezel around match', 0, 50, 15, GObject.PARAM_READABLE))
OPACITY = 95
#Gtk.widget_class_install_style_property(MatchView, ('opacity', GObject.TYPE_INT, 'Bezel opacity', 'Opacity of bezel around match', 50, 100, 95, GObject.PARAM_READABLE))

class Search (Gtk.Bin, pretty.OutputMixin):
    """
    A Widget for displaying search results
    icon + aux table etc

    Signals
    * cursor-changed: def callback(widget, selection)
        called with new selected (represented) object or None
    * activate: def callback(widget, selection)
        called with activated leaf, when the widget is activated
        by double-click in table
    * table-event: def callback(widget, table, event)
        called when the user types in the table
    """
    __gtype_name__ = 'Search'
    def __init__(self):
        GObject.GObject.__init__(self)
        # object attributes
        self.model = LeafModel()
        self.match = None
        self.match_state = State.Wait
        self.text = ""
        # internal constants
        self.show_initial = 10
        self.show_more = 10
        # number rows to skip when press PgUp/PgDown
        self.page_step = 7
        self.source = None
        self._old_win_position=None
        self._has_search_result = False
        self._initialized = False
        # finally build widget
        self.build_widget()
        self._icon_size = None
        self._icon_size_small = None
        self._read_icon_size()
        self.setup_empty()

    @property
    def icon_size(self):
        return self._icon_size

    def _icon_size_changed(self, setctl, section, key, value):
        self._icon_size = setctl.get_config_int("Appearance", "icon_large_size")
        self._icon_size_small = setctl.get_config_int("Appearance", "icon_small_size")
        self.model.icon_size = self._icon_size_small

    def _read_icon_size(self, *args):
        setctl = settings.GetSettingsController()
        setctl.connect("value-changed::appearance.icon_large_size", self._icon_size_changed)
        setctl.connect("value-changed::appearance.icon_small_size", self._icon_size_changed)
        self._icon_size_changed(setctl, None, None, None)

    def build_widget(self):
        """
        Core initalization method that builds the widget
        """
        self.match_view = MatchView()

        self.table = Gtk.TreeView.new_with_model(self.model.get_store())
        self.table.set_name("kupfer-list-view")
        self.table.set_headers_visible(False)
        self.table.set_property("enable-search", False)

        for col in self.model.columns:
            self.table.append_column(col)

        self.table.connect("row-activated", self._row_activated)
        self.table.connect("cursor-changed", self._cursor_changed)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.add(self.table)
        vscroll = self.scroller.get_vscrollbar()
        vscroll.connect("change-value", self._table_scroll_changed)

        self.list_window = Gtk.Window.new(Gtk.WindowType.POPUP)
        self.list_window.set_name("kupfer-list")

        box = Gtk.VBox()
        box.pack_start(self.match_view, True, True, 0)
        self.add(box)
        box.show_all()
        self.__child = box

        self.list_window.add(self.scroller)
        self.scroller.show_all()

    def get_current(self):
        """
        return current selection
        """
        return self.match

    def set_object_stack(self, stack):
        self.match_view.object_stack[:] = stack
        self.match_view.update_match()

    def set_source(self, source):
        """Set current source (to get icon, name etc)"""
        self.source = source

    def get_match_state(self):
        return self.match_state
    def get_match_text(self):
        return self.text

    def do_size_request (self, requisition):
        requisition.width, requisition.height = self.__child.size_request ()

    def do_size_allocate (self, allocation):
        self.__child.size_allocate (allocation)

    def do_forall (self, include_internals, callback, *user_data):
        callback (self.__child, *user_data)

    def get_table_visible(self):
        return self.list_window.get_property("visible")

    def hide_table(self):
        if self.get_table_visible():
            self.list_window.hide()

    def _show_table(self):
        setctl = settings.GetSettingsController()
        list_maxheight = setctl.get_config_int("Appearance", "list_height")
        # self.get_window() is a GdkWindow (of self's parent)
        win_width = self.get_window().get_width()
        win_height = self.get_window().get_height()
        pos_x, pos_y = self.get_window().get_position()
        # find origin in parent's coordinates
        self_x, self_y = self.translate_coordinates(self.get_parent(), 0, 0)
        self_width = self.size_request().width
        sub_x = pos_x
        sub_y = pos_y + win_height
        # to stop a warning
        _dummy_sr = self.table.size_request()
        # FIXME: Adapt list length
        subwin_height = list_maxheight
        subwin_width = self_width*2 - self_x
        if not text_direction_is_ltr():
            sub_x += win_width - subwin_width + self_x
        else:
            sub_x -= self_x
        self.list_window.move(sub_x, sub_y)
        self.list_window.resize(subwin_width, subwin_height)

        win = self.get_toplevel()
        self.list_window.set_transient_for(win)
        self.list_window.set_property("focus-on-map", False)
        self.list_window.show()
        self._old_win_position = pos_x, pos_y

    def show_table(self):
        self.go_down(True)

    def show_table_quirk(self):
        "Show table after being hidden in the same event"
        # KWin bugs out if we hide and show the table during the same gtk event
        # issue #47
        if kupfer.environment.is_kwin():
            GLib.idle_add(self.show_table)
        else:
            self.show_table()

    def _table_scroll_changed(self, scrollbar, scroll_type, value):
        """When the scrollbar changes due to user interaction"""
        # page size: size of currently visible area
        adj = scrollbar.get_adjustment()
        upper = adj.get_property("upper")
        page_size = adj.get_property("page-size")

        if value + page_size >= upper:
            self.populate(self.show_more)

    # table methods
    def _table_set_cursor_at_row(self, row):
        path_at_row = lambda r: (r,)
        self.table.set_cursor(path_at_row(row))

    def go_up(self, rows_count=1):
        """
        Upwards in the table
        """
        row_at_path = lambda p: p[0]

        # go up, simply. close table if we go up from row 0
        path, col = self.table.get_cursor()
        if path:
            r = row_at_path(path)
            if r >= 1:
                self._table_set_cursor_at_row(r-min(rows_count, r))
            else:
                self.hide_table()

    def go_down(self, force=False, rows_count=1):
        """
        Down in the table
        """
        row_at_path = lambda p: p[0]

        table_visible = self.get_table_visible()
        # if no data is loaded (frex viewing catalog), load
        # if too little data is loaded, try load more
        if len(self.model) <= 1:
            self.populate(self.show_more)
        if len(self.model) >= 1:
            path, col = self.table.get_cursor()
            if path:
                r = row_at_path(path)
                if len(self.model) - rows_count <= r:
                    self.populate(self.show_more)
                # go down only if table is visible
                if table_visible:
                    step = min(len(self.model) - r - 1, rows_count)
                    if step > 0:
                        self._table_set_cursor_at_row(r + step)
            else:
                self._table_set_cursor_at_row(0)
            self._show_table()
        if force:
            self._show_table()

    def go_page_up(self):
        ''' move list one page up '''
        self.go_up(self.page_step)

    def go_page_down(self):
        ''' move list one page down '''
        self.go_down(rows_count=self.page_step)

    def go_first(self):
        ''' Rewind to first item '''
        if self.get_table_visible():
            self._table_set_cursor_at_row(0)

    def _window_config(self, widget, event):
        """
        When the window moves
        """
        winpos = event.x, event.y
        # only hide on move, not resize
        # set old win position in _show_table
        if self.get_table_visible() and winpos != self._old_win_position:
            self.hide_table()
            GLib.timeout_add(300, self._show_table)

    def _window_hidden(self, window):
        """
        Window changed hid
        """
        self.hide_table()

    def _row_activated(self, treeview, path, col):
        obj = self.get_current()
        self.emit("activate", obj)

    def _cursor_changed(self, treeview):
        path, col = treeview.get_cursor()
        match = self.model.get_object(path)
        self._set_match(match)

    def _set_match(self, rankable=None):
        """
        Set the currently selected (represented) object, either as
        @rankable or KupferObject @obj

        Emits cursor-changed
        """
        self.match = (rankable.object if rankable else None)
        self.emit("cursor-changed", self.match)
        if self.match:
            match_text = (rankable and rankable.value)
            self.match_state = State.Match
            m = self.match
            pbuf = (m.get_thumbnail(self.icon_size*4//3, self.icon_size) or
                m.get_pixbuf(self.icon_size))
            self.match_view.set_match_state(match_text, pbuf,
                    match=self.text, state=self.match_state)

    def set_match_plain(self, obj):
        """Set match to object @obj, without search or matches"""
        self.text = None
        self._set_match(obj)
        self.model.add_first(obj)
        self._table_set_cursor_at_row(0)

    def relax_match(self):
        """Remove match text highlight"""
        self.match_view.set_match_text(None)
        self.text = None

    def has_result(self):
        """A search with explicit search term is active"""
        return self._has_search_result

    def is_showing_result(self):
        """Showing search result:
        A search with explicit search term is active,
        and the result list is shown.
        """
        return self._has_search_result and self.get_table_visible()

    def update_match(self, key, matchrankable, matches):
        """
        @matchrankable: Rankable first match or None
        @matches: Iterable to rest of matches
        """
        self._has_search_result = bool(key)
        self.model.clear()
        self.text = key
        if not matchrankable:
            self._set_match(None)
            return self.handle_no_matches(empty=not key)
        self._set_match(matchrankable)
        self.model.set_base(iter(matches))
        self._browsing_match = False
        if not self.model and self.get_table_visible():
            self.go_down()

    def reset(self):
        self._has_search_result = False
        self._initialized = True
        self.model.clear()
        self.setup_empty()

    def setup_empty(self):
        self.match_state = State.NoMatch
        self.match_view.set_match_state("No match", None, state=State.NoMatch)
        self.relax_match()

    def get_is_browsing(self):
        """Return if self is browsing"""
        return self._browsing_match

    def populate(self, num):
        """populate model with num items"""
        return self.model.populate(num)

    def handle_no_matches(self, empty=False):
        """if @empty, there were no matches to find"""
        name, icon = self.get_nomatch_name_icon(empty=empty)
        self.match_state = State.NoMatch
        self.match_view.set_match_state(name, icon, state=State.NoMatch)

# Take care of GObject things to set up the Search class
GObject.type_register(Search)
GObject.signal_new("activate", Search, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, (GObject.TYPE_PYOBJECT, ))
GObject.signal_new("cursor-changed", Search, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, (GObject.TYPE_PYOBJECT, ))

class LeafSearch (Search):
    """
    Customize for leaves search
    """
    def get_nomatch_name_icon(self, empty):
        get_pbuf = \
            lambda m: (m.get_thumbnail(self.icon_size*4/3, self.icon_size) or \
                    m.get_pixbuf(self.icon_size))
        if empty and self.source:
            return ("<i>" + escape_markup_str(self.source.get_empty_text()) + "</i>",
                    get_pbuf(self.source))
        elif self.source:
            return (_('No matches in %(src)s for "%(query)s"') % {
                "src": "<i>%s</i>" % escape_markup_str(str(self.source)),
                "query": escape_markup_str(self.text),
                },
                get_pbuf(self.source))
        else:
            return _("No matches"), icons.get_icon_for_name("kupfer-object",
                    self.icon_size)

    def setup_empty(self):
        icon = None
        def get_pbuf(m):
            return (m.get_thumbnail(self.icon_size*4//3, self.icon_size) or
                    m.get_pixbuf(self.icon_size))
        if self.source:
            icon = get_pbuf(self.source)
            title = "<i>" + self.source.get_search_text() + "</i>"
        else:
            title = "<i>" + _("Type to search") + "</i>"

        self._set_match(None)
        self.match_state = State.Wait
        self.match_view.set_match_state(title, icon, state=State.Wait)

class ActionSearch (Search):
    """
    Customization for Actions
    """
    def get_nomatch_name_icon(self, empty=False):
        # don't look up icons too early
        if not self._initialized:
            return ("", None)
        if self.text:
            title = "<i>" + (_('No action matches "%s"') % escape_markup_str(self.text)) + "</i>"
        else:
            title = ""

        return title, icons.get_icon_for_name("kupfer-execute", self.icon_size)
    def setup_empty(self):
        self.handle_no_matches()
        self.hide_table()

class Interface (GObject.GObject, pretty.OutputMixin):
    """
    Controller object that controls the input and
    the state (current active) search object/widget

    Signals:
    * cancelled: def callback(controller)
        escape was typed
    """
    __gtype_name__ = "Interface"

    def __init__(self, controller, window):
        """
        @controller: DataController
        @window: toplevel window
        """
        GObject.GObject.__init__(self)

        self.search = LeafSearch()
        self.action = ActionSearch()
        self.third = LeafSearch()
        self.entry = Gtk.Entry()
        self.label = Gtk.Label()
        self.preedit = Gtk.Entry()
        self.search.set_name("kupfer-object-pane")
        self.action.set_name("kupfer-action-pane")
        self.third.set_name("kupfer-indirect-object-pane")
        ## make sure we lose the preedit focus ring
        self.preedit.set_name("kupfer-preedit")

        self.current = None

        self._widget = None
        self._ui_transition_timer = scheduler.Timer()
        self._pane_three_is_visible = False
        self._is_text_mode = False
        self._latest_input_timer = scheduler.Timer()
        self._slow_input_interval = 2
        self._key_press_time = None
        self._key_press_interval = 0.3
        self._key_press_repeat_threshold = 0.02
        self._key_repeat_key = None
        self._key_repeat_active = False
        self._reset_to_toplevel = False
        self._reset_when_back = False
        self.entry.connect("realize", self._entry_realized)
        self.preedit.set_has_frame(False)
        self.preedit.set_width_chars(0)
        self.preedit.set_alignment(1)

        self.label.set_width_chars(50)
        self.label.set_max_width_chars(50)
        self.label.set_single_line_mode(True)
        self.label.set_ellipsize(ELLIPSIZE_MIDDLE)
        self.label.set_name("kupfer-description")

        self.switch_to_source_init()
        self.entry.connect("changed", self._changed)
        self.preedit.connect("insert-text", self._preedit_insert_text)
        self.preedit.connect("draw", self._preedit_draw)
        self.preedit.connect("preedit-changed", self._preedit_im_changed)
        for widget in (self.entry, self.preedit):
            widget.connect("activate", self._activate, None)
            widget.connect("key-press-event", self._entry_key_press)
            widget.connect("key-release-event", self._entry_key_release)
            widget.connect("copy-clipboard", self._entry_copy_clipboard)
            widget.connect("cut-clipboard", self._entry_cut_clipboard)
            widget.connect("paste-clipboard", self._entry_paste_clipboard)

        # set up panewidget => self signals
        # as well as window => panewidgets
        for widget in (self.search, self.action, self.third):
            widget.connect("activate", self._activate)
            widget.connect("button-press-event", self._panewidget_button_press)
            widget.connect("cursor-changed", self._selection_changed)
            # window signals
            window.connect("configure-event", widget._window_config)
            window.connect("hide", widget._window_hidden)

        self.data_controller = controller
        self.data_controller.connect("search-result", self._search_result)
        self.data_controller.connect("source-changed", self._new_source)
        self.data_controller.connect("pane-reset", self._pane_reset)
        self.data_controller.connect("mode-changed", self._show_hide_third)
        self.data_controller.connect("object-stack-changed", self._object_stack_changed)
        self.widget_to_pane = {
            id(self.search) : data.SourcePane,
            id(self.action) : data.ActionPane,
            id(self.third) : data.ObjectPane,
            }
        self.pane_to_widget = {
            data.SourcePane : self.search,
            data.ActionPane : self.action,
            data.ObjectPane : self.third,
        }
        # Setup keyval mapping
        keys = (
            "Up", "Down", "Right", "Left",
            "Tab", "ISO_Left_Tab", "BackSpace", "Escape", "Delete",
            "space", 'Page_Up', 'Page_Down', 'Home', 'End',
            "Return",
            )
        self.key_book = dict((k, Gdk.keyval_from_name(k)) for k in keys)
        if not text_direction_is_ltr():
            # for RTL languages, simply swap the meaning of Left and Right
            # (for keybindings!)
            D = self.key_book
            D["Left"], D["Right"] = D["Right"], D["Left"]

        self.keys_sensible = set(self.key_book.values())
        self.search.reset()

    def get_widget(self):
        """Return a Widget containing the whole Interface"""
        if self._widget:
            return self._widget
        box = Gtk.HBox()
        box.pack_start(self.search, True, True, 3)
        box.pack_start(self.action, True, True, 3)
        box.pack_start(self.third, True, True, 3)
        vbox = Gtk.VBox()
        vbox.pack_start(box, True, True, 0)

        label_align = Gtk.Alignment.new(0.5, 1, 0, 0)
        label_align.set_property("top-padding", 3)
        label_align.add(self.label)
        vbox.pack_start(label_align, False, False, 0)
        vbox.pack_start(self.entry, False, False, 0)
        vbox.show_all()
        self.third.hide()
        self._widget = vbox
        return vbox

    def _entry_realized(self, widget):
        self.update_text_mode()

    def _entry_key_release(self, entry, event):
        return
        # check for key repeat activation (disabled)
        if self._key_repeat_key == event.keyval:
            if self._key_repeat_active:
                self.activate()
            self._key_repeat_key = None
            self._key_repeat_active = False
            self._update_active()

    def _entry_key_press(self, entry, event):
        """
        Intercept arrow keys and manipulate table
        without losing focus from entry field
        """

        direct_text_key = Gdk.keyval_from_name("period")
        init_text_keys = list(map(Gdk.keyval_from_name,
            ("slash", "equal", "question")))
        init_text_keys.append(direct_text_key)
        keymap = Gdk.Keymap.get_default()
        # translate keys properly
        _was_bound, keyv, egroup, level, consumed = keymap.translate_keyboard_state(
                    event.hardware_keycode, event.get_state(), event.group)
        all_modifiers = Gtk.accelerator_get_default_mod_mask()
        modifiers = all_modifiers & ~consumed
        # MOD1_MASK is alt/option
        mod1_mask = ((event.get_state() & modifiers) == Gdk.ModifierType.MOD1_MASK)
        shift_mask = ((event.get_state() & all_modifiers) == Gdk.ModifierType.SHIFT_MASK)

        text_mode = self.get_in_text_mode()
        has_input = bool(self.entry.get_text())

        # curtime = time.time()
        self._reset_input_timer()

        setctl = settings.GetSettingsController()
        # process accelerators
        for action, accel in setctl.get_accelerators().items():
            akeyv, amodf = Gtk.accelerator_parse(accel)
            if not akeyv:
                continue
            if akeyv == keyv and (amodf == (event.get_state() & modifiers)):
                action_method = getattr(self, action, None)
                if not action_method:
                    pretty.print_error(__name__, "Action invalid '%s'" % action)
                else:
                    action_method()
                return True

        key_book = self.key_book
        use_command_keys = setctl.get_use_command_keys()
        has_selection = (self.current.get_match_state() is State.Match)
        if not text_mode and use_command_keys:
            # translate extra commands to normal commands here
            # and remember skipped chars
            if keyv == key_book["space"]:
                if shift_mask:
                    keyv = key_book["Up"]
                else:
                    keyv = key_book["Down"]
            elif keyv == ord("/") and has_selection:
                keyv = key_book["Right"]
            elif keyv == ord(",") and has_selection:
                if self.comma_trick():
                    return True
            elif keyv in init_text_keys:
                if self.try_enable_text_mode():
                    # swallow if it is the direct key
                    swallow = (keyv == direct_text_key)
                    return swallow
        if text_mode and keyv in (key_book["Left"], key_book["Right"],
                                  key_book["Home"], key_book["End"]):
            # pass these through in text mode
            return False

        # disabled  repeat-key activation and shift-to-action selection
        # check for repeated key activation
        """
        if ((not text_mode) and self._key_repeat_key == keyv and
                keyv not in self.keys_sensible and
                curtime - self._key_press_time > self._key_press_repeat_threshold):
            if curtime - self._key_press_time > self._key_press_interval:
                self._key_repeat_active = True
                self._update_active()
            return True
        else:
            # cancel repeat key activation if a new key is pressed
            self._key_press_time = curtime
            self._key_repeat_key = keyv
            if self._key_repeat_active:
                self._key_repeat_active = False
                self._update_active()
        """

        """
            ## if typing with shift key, switch to action pane
            if not text_mode and use_command_keys and shift_mask:
                uchar = Gdk.keyval_to_unicode(keyv)
                if (uchar and unichr(uchar).isupper() and
                    self.current == self.search):
                    self.current.hide_table()
                    self.switch_current()
            return False
        """
        # exit here if it's not a special key
        if keyv not in self.keys_sensible:
            return False
        self._reset_to_toplevel = False

        if keyv == key_book["Escape"]:
            self._escape_key_press()
            return True


        if keyv == key_book["Up"]:
            self.current.go_up()
        elif keyv == key_book["Page_Up"]:
            self.current.go_page_up()
        elif keyv == key_book["Down"]:
            ## if typing with shift key, switch to action pane
            if shift_mask and self.current == self.search:
                self.current.hide_table()
                self.switch_current()
            if (not self.current.get_current() and
                    self.current.get_match_state() is State.Wait):
                self._populate_search()
            self.current.go_down()
        elif keyv == key_book["Page_Down"]:
            if (not self.current.get_current() and
                    self.current.get_match_state() is State.Wait):
                self._populate_search()
            self.current.go_page_down()
        elif keyv == key_book["Right"]:
            self._browse_down(alternate=mod1_mask)
        elif keyv == key_book["BackSpace"]:
            if not has_input:
                self._backspace_key_press()
            elif not text_mode:
                self.entry.delete_text(self.entry.get_text_length() - 1, -1)
            else:
                return False
        elif keyv == key_book["Left"]:
            self._back_key_press()
        elif keyv in (key_book["Tab"], key_book["ISO_Left_Tab"]):
            self.switch_current(reverse=(keyv == key_book["ISO_Left_Tab"]))
        elif keyv == key_book['Home']:
            self.current.go_first()
        else:
            # cont. processing
            return False
        return True

    def _entry_copy_clipboard(self, entry):
        # Copy current selection to clipboard
        # delegate to text entry when in text mode

        if self.get_in_text_mode():
            return False
        selection = self.current.get_current()
        if selection is None:
            return False
        clip = Gtk.Clipboard.get_for_display(
                entry.get_display(),
                Gdk.SELECTION_CLIPBOARD)
        return interface.copy_to_clipboard(selection, clip)

    def _entry_cut_clipboard(self, entry):
        if not self._entry_copy_clipboard(entry):
            return False
        self.reset_current()
        self.reset()

    def _entry_paste_data_received(self, clipboard, targets, _extra, entry):
        uri_target = Gdk.Atom.intern("text/uri-list", False)
        ### check if we can insert files
        if uri_target in targets:
            # paste as files
            sdata = clipboard.wait_for_contents(uri_target)
            self.reset_current()
            self.reset()
            self.put_files(sdata.get_uris(), paths=False)
            ## done
        else:
            # enable text mode and reemit to paste text
            self.try_enable_text_mode()
            if self.get_in_text_mode():
                entry.emit("paste-clipboard")

    def _entry_paste_clipboard(self, entry):
        if not self.get_in_text_mode():
            self.reset()
            ## when not in text mode,
            ## stop signal emission so we can handle it
            clipboard = Gtk.Clipboard.get_for_display(
                    entry.get_display(),
                    Gdk.SELECTION_CLIPBOARD)
            clipboard.request_targets(self._entry_paste_data_received, entry)
            entry.emit_stop_by_name("paste-clipboard")


    def reset_text(self):
        self.entry.set_text("")

    def reset(self):
        self.reset_text()
        self.current.hide_table()

    def reset_current(self, populate=False):
        """
        Reset the source or action view

        Corresponds to backspace
        """
        if self.current.get_match_state() is State.Wait:
            self.toggle_text_mode(False)
        if self.current is self.action or populate:
            self._populate_search()
        else:
            self.current.reset()

    def reset_all(self):
        """Reset all panes and focus the first"""
        self.switch_to_source()
        while self._browse_up():
            pass
        self.toggle_text_mode(False)
        self.data_controller.object_stack_clear_all()
        self.reset_current()
        self.reset()

    def _populate_search(self):
        """Do a blanket search/empty search to populate current pane"""
        pane = self._pane_for_widget(self.current)
        self.data_controller.search(pane, interactive=True)

    def soft_reset(self, pane=None):
        """Reset @pane or current pane context/source
        softly (without visible update), and unset _reset_to_toplevel marker.
        """
        pane = pane or self._pane_for_widget(self.current)
        newsrc = self.data_controller.soft_reset(pane)
        if newsrc:
            self.current.set_source(newsrc)
        self._reset_to_toplevel = False


    def _escape_key_press(self):
        """Handle escape if first pane is reset, cancel (put away) self.  """
        if self.current.has_result():
            if self.current.is_showing_result():
                self.reset_current(populate=True)
            else:
                self.reset_current()
        else:
            if self.get_in_text_mode():
                self.toggle_text_mode(False)
            elif not self.current.get_table_visible():
                pane = self._pane_for_widget(self.current)
                self.data_controller.object_stack_clear(pane)
                self.emit("cancelled")
            self._reset_to_toplevel = True
            self.current.hide_table()
        self.reset_text()

    def _backspace_key_press(self):
        # backspace: delete from stack
        pane = self._pane_for_widget(self.current)
        if self.data_controller.get_object_stack(pane):
            self.data_controller.object_stack_pop(pane)
            self.reset_text()
            return
        self._back_key_press()

    def _back_key_press(self):
        # leftarrow (or backspace without object stack)
        # delete/go up through stource stack
        if self.current.is_showing_result():
            self.reset_current(populate=True)
        else:
            if self._browse_up():
                pass
            else:
                self.reset()
                self.reset_current()
                self._reset_to_toplevel = True
        self.reset_text()

    def _relax_search_terms(self):
        if self.get_in_text_mode():
            return
        self.reset_text()
        self.current.relax_match()

    def get_in_text_mode(self):
        return self._is_text_mode

    def get_can_enter_text_mode(self):
        """We can enter text mode if the data backend allows,
        and the text entry is ready for input (empty)
        """
        pane = self._pane_for_widget(self.current)
        val = self.data_controller.get_can_enter_text_mode(pane)
        entry_text = self.entry.get_text()
        return val and not entry_text

    def try_enable_text_mode(self):
        """Perform a soft reset if possible and then try enabling text mode"""
        if self._reset_to_toplevel:
            self.soft_reset()
        if self.get_can_enter_text_mode():
            return self.toggle_text_mode(True)
        return False

    def toggle_text_mode(self, val):
        """Toggle text mode on/off per @val,
        and return the subsequent on/off state.
        """
        val = bool(val) and self.get_can_enter_text_mode()
        self._is_text_mode = val
        self.update_text_mode()
        self.reset()
        return val

    def toggle_text_mode_quick(self):
        """Toggle text mode or not, if we can or not, without reset"""
        if self._is_text_mode:
            self._is_text_mode = False
        else:
            self._is_text_mode = True
        self.update_text_mode()

    def update_text_mode(self):
        """update appearance to whether text mode enabled or not"""
        if self._is_text_mode:
            self.entry.show()
            self.entry.grab_focus()
            self.entry.set_position(-1)
            self.preedit.hide()
            self.preedit.set_width_chars(0)
        else:
            self.entry.hide()
        self._update_active()

    def switch_to_source_init(self):
        # Initial switch to source
        self.current = self.search
        self._update_active()
        if self.get_in_text_mode():
            self.toggle_text_mode_quick()

    def switch_to_source(self):
        self.switch_current_to(0)

    def switch_to_2(self):
        self.switch_current_to(1)

    def switch_to_3(self):
        self.switch_current_to(2)

    def focus(self):
        """called when the interface is focus (after being away)"""
        if self._reset_when_back:
            self._reset_when_back = False
            self.toggle_text_mode(False)
        # preserve text mode, but switch to source if we are not in it
        if not self.get_in_text_mode():
            self.switch_to_source()
        # Check that items are still valid when "coming back"
        self.data_controller.validate()

    def did_launch(self):
        "called to notify that 'activate' was successful"
        self._reset_when_back = True

    def did_get_result(self):
        "called when a command result has come in"
        self._reset_when_back = False

    def put_away(self):
        """Called when the interface is hidden"""
        self._relax_search_terms()
        self._reset_to_toplevel = True
        # no hide / show pane three on put away -> focus anymore

    def select_selected_file(self):
        # Add optional lookup data to narrow the search
        self.data_controller.find_object("qpfer:selectedfile#any.FileLeaf")

    def select_clipboard_file(self):
        # Add optional lookup data to narrow the search
        self.data_controller.find_object("qpfer:clipboardfile#any.FileLeaf")

    def select_selected_text(self):
        self.data_controller.find_object("qpfer:selectedtext#any.TextLeaf")

    def select_clipboard_text(self):
        # Add optional lookup data to narrow the search
        self.data_controller.find_object("qpfer:clipboardtext#any.FileLeaf")

    def select_quit(self):
        self.data_controller.find_object("qpfer:quit")

    def show_help(self):
        kupferui.show_help(self._make_gui_ctx())
        self.emit("launched-action")

    def show_preferences(self):
        kupferui.show_preferences(self._make_gui_ctx())
        self.emit("launched-action")

    def compose_action(self):
        self.data_controller.compose_selection()

    def mark_as_default(self):
        if self.action.get_match_state() != State.Match:
            return False
        self.data_controller.mark_as_default(data.ActionPane)
        return True

    def erase_affinity_for_first_pane(self):
        if self.search.get_match_state() != State.Match:
            return False
        self.data_controller.erase_object_affinity(data.SourcePane)
        return True

    def comma_trick(self):
        if self.current.get_match_state() != State.Match:
            return False
        cur = self.current.get_current()
        curpane = self._pane_for_widget(self.current)
        if self.data_controller.object_stack_push(curpane, cur):
            self._relax_search_terms()
            if self.get_in_text_mode():
                self.reset_text()
            return True

    def get_context_actions(self):
        """
        Get a list of (name, function) currently
        active context actions
        """
        def get_accel(key):
            """ Return name, method pair for @key"""
            if key not in accelerators.ACCELERATOR_NAMES:
                raise RuntimeError("Missing accelerator: %s" % key)
            return (accelerators.ACCELERATOR_NAMES[key], getattr(self, key))
        def trunc(ustr):
            "truncate long object names"
            return ustr[:25]
        has_match = self.current.get_match_state() == State.Match
        if has_match:
            yield get_accel('compose_action')
        yield get_accel('select_selected_text')
        if self.get_can_enter_text_mode():
            yield get_accel('toggle_text_mode_quick')
        if self.action.get_match_state() == State.Match:
            smatch = self.search.get_current()
            amatch = self.action.get_current()
            label = (_('Make "%(action)s" Default for "%(object)s"') % {
                     'action': trunc(str(amatch)),
                     'object': trunc(str(smatch)),
                     })
            w_label = textwrap.wrap(label, width=40, subsequent_indent="    ")
            yield ("\n".join(w_label), self.mark_as_default)
        if has_match:
            if self.data_controller.get_object_has_affinity(data.SourcePane):
                match = self.search.get_current()
                # TRANS: Removing learned and/or configured bonus search score
                yield (_('Forget About "%s"') % trunc(str(match)),
                       self.erase_affinity_for_first_pane)
        if has_match:
            yield get_accel('reset_all')

    def _pane_reset(self, controller, pane, item):
        wid = self._widget_for_pane(pane)
        if not item:
            wid.reset()
        else:
            wid.set_match_plain(item)
            if wid is self.search:
                self.reset()
                self.toggle_text_mode(False)
                self.switch_to_source()

    def _new_source(self, sender, pane, source, at_root):
        """Notification about a new data source,
        (represented object for the self.search object
        """
        wid = self._widget_for_pane(pane)
        wid.set_source(source)
        wid.reset()
        if pane is data.SourcePane:
            self.switch_to_source()
            self.action.reset()
        if wid is self.current:
            self.toggle_text_mode(False)
            self._reset_to_toplevel = False
            if not at_root:
                self.reset_current(populate=True)
                wid.show_table_quirk()

    def update_third(self):
        if self._pane_three_is_visible:
            self._ui_transition_timer.set_ms(200, self._show_third_pane, True)
        else:
            self._show_third_pane(False)

    def _show_hide_third(self, ctr, mode, ignored):
        if mode is data.SourceActionObjectMode:
            # use a delay before showing the third pane,
            # but set internal variable to "shown" already now
            self._pane_three_is_visible = True
            self._ui_transition_timer.set_ms(200, self._show_third_pane, True)
        else:
            self._pane_three_is_visible = False
            self._show_third_pane(False)

    def _show_third_pane(self, show):
        self._ui_transition_timer.invalidate()
        self.third.set_property("visible", show)

    def _update_active(self):
        for panewidget in (self.action, self.search, self.third):
            if panewidget is not self.current:
                panewidget.set_state(Gtk.StateType.NORMAL)
            panewidget.match_view.inject_preedit(None)
        if self._is_text_mode or self._key_repeat_active:
            self.current.set_state(Gtk.StateType.ACTIVE)
        else:
            self.current.set_state(Gtk.StateType.SELECTED)
            self.current.match_view.inject_preedit(self.preedit)
        self._description_changed()

    def switch_current(self, reverse=False):
        # Only allow switch if we have match
        order = [self.search, self.action]
        if self._pane_three_is_visible:
            order.append(self.third)
        curidx = order.index(self.current)
        newidx = curidx -1 if reverse else curidx +1
        newidx %= len(order)
        self.switch_current_to(newidx)

    def switch_current_to(self, index):
        """
        Switch selected pane

        index: index (0, 1, or 2) of the pane to select.
        """
        assert index in (0, 1, 2)
        order = [self.search, self.action]
        if self._pane_three_is_visible:
            order.append(self.third)

        if index >= len(order):
            return False
        pane_before = order[max(index - 1, 0)]
        new_focus = order[index]
        no_match_ok = index == 0
        # Only allow switch if we have match in the pane before
        if ((no_match_ok or pane_before.get_match_state() is State.Match) and
                new_focus is not self.current):
            self.current.hide_table()
            self.current = new_focus
            # Use toggle_text_mode to reset
            self.toggle_text_mode(False)
            pane = self._pane_for_widget(new_focus)
            self._update_active()
            if self.data_controller.get_should_enter_text_mode(pane):
                self.toggle_text_mode_quick()
        return True

    def _browse_up(self):
        pane = self._pane_for_widget(self.current)
        return self.data_controller.browse_up(pane)

    def _browse_down(self, alternate=False):
        pane = self._pane_for_widget(self.current)
        self.data_controller.browse_down(pane, alternate=alternate)

    def _make_gui_ctx(self):
        event_time = Gtk.get_current_event_time()
        return uievents.gui_context_from_widget(event_time, self._widget)

    def _activate(self, widget, current):
        self.data_controller.activate(ui_ctx=self._make_gui_ctx())

    def activate(self):
        """Activate current selection (Run action)"""
        self._activate(None, None)

    def execute_file(self, filepath, display, event_time):
        """Execute a .kfcom file"""
        def _handle_error(exc_info):
            from kupfer import uiutils
            etype, exc, tb = exc_info
            if not uiutils.show_notification(str(exc), icon_name="kupfer"):
                raise
        ctxenv = uievents.gui_context_from_keyevent(event_time, display)
        self.data_controller.execute_file(filepath, ctxenv, _handle_error)

    def _search_result(self, sender, pane, matchrankable, matches, context):
        # NOTE: "Always-matching" search.
        # If we receive an empty match, we ignore it, to retain the previous
        # results. The user is not served by being met by empty results.
        key = context
        if key and len(key) > 1 and matchrankable is None:
            # with typos or so, reset quicker
            self._latest_input_timer.set(self._slow_input_interval/2,
                    self._relax_search_terms)
            return
        wid = self._widget_for_pane(pane)
        wid.update_match(key, matchrankable, matches)

    def _widget_for_pane(self, pane):
        return self.pane_to_widget[pane]
    def _pane_for_widget(self, widget):
        return self.widget_to_pane[id(widget)]

    def _object_stack_changed(self, controller, pane):
        """
        Stack of objects (for comma trick) changed in @pane
        """
        wid = self._widget_for_pane(pane)
        wid.set_object_stack(controller.get_object_stack(pane))

    def _panewidget_button_press(self, widget, event):
        " mouse clicked on a pane widget "
        # activate on double-click
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            self.activate()
            return True

    def _selection_changed(self, widget, match):
        pane = self._pane_for_widget(widget)
        self.data_controller.select(pane, match)
        if not widget is self.current:
            return
        self._description_changed()

    def _description_changed(self):
        match = self.current.get_current()
        # Use invisible WORD JOINER instead of empty, to maintain vertical size
        desc = match and match.get_description() or "\N{WORD JOINER}"
        markup = "<small>%s</small>" % (escape_markup_str(desc), )
        self.label.set_markup(markup)

    def put_text(self, text):
        """
        Put @text into the interface to search, to use
        for "queries" from other sources
        """
        self.try_enable_text_mode()
        self.entry.set_text(text)
        self.entry.set_position(-1)

    def put_files(self, fileuris, paths):
        self.output_debug("put-files:", list(fileuris))
        if paths:
            leaves = list(map(interface.get_fileleaf_for_path,
                [_f for _f in [Gio.File.new_for_path(U).get_path() for U in fileuris] if _f]))
        else:
            leaves = list(map(interface.get_fileleaf_for_path,
                [_f for _f in [Gio.File.new_for_uri(U).get_path() for U in fileuris] if _f]))
        if leaves:
            self.data_controller.insert_objects(data.SourcePane, leaves)

    def _reset_input_timer(self):
        # if input is slow/new, we reset
        self._latest_input_timer.set(self._slow_input_interval,
                self._relax_search_terms)

    def _preedit_im_changed(self, editable, preedit_string):
        """
        This is called whenever the input method changes its own preedit box.
        We take this opportunity to expand it.
        """
        if preedit_string:
            self.current.match_view.expand_preedit(self.preedit)
            self._reset_input_timer()

    def _preedit_insert_text(self, editable, text, byte_length, position):
        # New text about to be inserted in preedit
        if text:
            self.entry.insert_text(text, -1)
            self.entry.set_position(-1)
            self._reset_input_timer()
            self._update_active()
        GObject.signal_stop_emission_by_name(editable, "insert-text")
        return False

    def _preedit_draw(self, widget, cr):
        # draw nothing if hidden
        return widget.get_width_chars() == 0

    def _changed(self, editable):
        """
        The entry changed callback: Here we have to be sure to use
        **UNICODE** (unicode()) for the entered text
        """
        # @text is UTF-8
        text = editable.get_text()
        #text = text.decode("UTF-8")

        # draw character count as icon
        if False and self.get_in_text_mode() and text:
            w, h = editable.size_request()
            sz = h - 3
            c = editable.style.text[Gtk.StateType.NORMAL]
            textc = (c.red/65535.0, c.green/65535.0, c.blue/65535.0)
            pb = get_glyph_pixbuf(str(len(text)), sz, color=textc)
            pb = get_glyph_pixbuf(str(len(text)), sz, color="black")
            editable.set_icon_from_pixbuf(Gtk.EntryIconPosition.SECONDARY, pb)
        else:
            editable.set_icon_from_pixbuf(Gtk.EntryIconPosition.SECONDARY, None)

        # cancel search and return if empty
        if not text:
            self.data_controller.cancel_search()
            # See if it was a deleting key press
            curev = Gtk.get_current_event()
            if (curev and curev.type == Gdk.EventType.KEY_PRESS and
                curev.keyval in (self.key_book["Delete"],
                    self.key_book["BackSpace"])):
                self._backspace_key_press()
            return

        # start search for updated query
        pane = self._pane_for_widget(self.current)
        if not self.get_in_text_mode() and self._reset_to_toplevel:
            self.soft_reset(pane)

        self.data_controller.search(pane, key=text, context=text,
                text_mode=self.get_in_text_mode())

GObject.type_register(Interface)
GObject.signal_new("cancelled", Interface, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())
# Send only when the interface itself launched an action directly
GObject.signal_new("launched-action", Interface, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())

PREEDIT_HIDDEN_CLASS = "hidden"

KUPFER_CSS = b"""
#kupfer {
}

.matchview {
    border-radius: 0.6em;
}
.matchview label {
    margin-bottom: 0.2em;
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

*:selected .matchview {
    background: alpha(@theme_selected_bg_color, 0.5);
    border: 2px solid alpha(black, 0.3)
}
"""

class KupferWindow (Gtk.Window):
    __gtype_name__ = "KupferWindow"
    def __init__(self, type_):
        super(KupferWindow, self).__init__(type=type_)
        self.connect("style-set", self.on_style_set)
        self.set_name("kupfer")
        #self.connect("map-event", self.on_expose_event)
        self.connect("size-allocate", self.on_size_allocate)
        self.connect("composited-changed", self.on_composited_changed)
        self.connect("realize", self.on_realize)
        #self.set_app_paintable(True)

    def on_style_set(self, widget, old_style):
        pretty.print_debug(__name__, "Scale factor", self.get_scale_factor())
        widget.set_property('decorated', WINDOW_DECORATED)
                #widget.style_get_property('decorated'))
        widget.set_property('border-width', WINDOW_BORDER_WIDTH)
                #widget.style_get_property('border-width'))
        self._load_css()
        return False

    def _load_css(self):
        style_provider = Gtk.CssProvider()

        style_provider.load_from_data(KUPFER_CSS)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_expose_event(self, widget, event):
        cr = widget.window.cairo_create()
        w,h = widget.allocation.width, widget.allocation.height

        region = Gdk.region_rectangle(event.area)
        cr.region(region)
        cr.clip()

        def rgba_from_gdk(c, alpha):
            return (c.red/65535.0, c.green/65535.0, c.blue/65535.0, alpha)

        radius = CORNER_RADIUS
        if widget.is_composited():
            opacity = 0.01*widget.style_get_property('opacity')
            #cr.set_operator(cairo.OPERATOR_CLEAR)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.set_source_rgba(0,0,0,0)
            cr.rectangle(0,0,w,h)
            cr.fill()
            #cr.rectangle(0,0,w,h)
            make_rounded_rect(cr, 0, 0, w, h, radius)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            c = widget.style.bg[widget.get_state()]
            cr.set_source_rgba(*rgba_from_gdk(c, opacity))
            cr.fill()

        #c = widget.style.dark[Gtk.StateType.SELECTED]
        #cr.set_operator(cairo.OPERATOR_OVER)
        #cr.set_source_rgba(*rgba_from_gdk(c, 0.7))

        make_rounded_rect(cr, 0, 0, w, h, radius)
        cr.set_line_width(1)
        cr.stroke()

    def on_composited_changed(self, widget):
        self.reshape(widget, widget.get_allocation())

    def on_realize(self, widget):
        self.reshape(widget, widget.get_allocation())

    def on_size_allocate(self, widget, allocation):
        if not hasattr(self, "_old_alloc"):
            self._old_alloc = (0,0)
        w,h = allocation.width, allocation.height

        if self._old_alloc == (w,h):
            return
        self._old_alloc = (w,h)
        self.reshape(widget, allocation)

    def reshape(self, widget, allocation):
        return
        ## if not composited, use rounded window shape
        w,h = allocation.width, allocation.height
        radius = CORNER_RADIUS
        if not widget.is_composited() and radius:
            bitmap = Gdk.Pixmap(None, w, h, 1)
            cr = bitmap.cairo_create()

            cr.set_source_rgb(0.0, 0.0, 0.0)
            cr.set_operator(cairo.OPERATOR_CLEAR)
            cr.paint()

            # radius of rounded corner
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            make_rounded_rect(cr, 0, 0, w, h, radius)
            cr.fill()
            widget.shape_combine_mask(bitmap, 0, 0)
        else:
            if widget.window:
                widget.window.shape_combine_mask(None, 0, 0)
        if widget.window:
            widget.window.invalidate_rect((0, 0, w, h), False)


GObject.type_register(KupferWindow)
WINDOW_CORNER_RAIDUS = 15
WINDOW_OPACITY = 85
WINDOW_DECORATED = False
#Gtk.widget_class_install_style_property(KupferWindow, ('corner-radius', GObject.TYPE_INT, 'Corner radius', 'Radius of bezel around window', 0, 50, 15, GObject.PARAM_READABLE))
#Gtk.widget_class_install_style_property(KupferWindow, ('opacity', GObject.TYPE_INT, 'Frame opacity', 'Opacity of window background', 50, 100, 85, GObject.PARAM_READABLE))
#Gtk.widget_class_install_style_property(KupferWindow, ('decorated', GObject.TYPE_BOOLEAN, 'Decorated', 'Whether to use window decorations', False, GObject.PARAM_READABLE))

WINDOW_BORDER_WIDTH = 8
#Gtk.widget_class_install_style_property(KupferWindow, ('border-width', GObject.TYPE_INT, 'Border width', 'Width of border around window content', 0, 100, 8, GObject.PARAM_READABLE))

class WindowController (pretty.OutputMixin):
    """
    This is the fundamental Window (and App) Controller
    """
    def __init__(self):
        self.window = None
        self.current_screen_handler = 0
        self.current_screen = None
        self.interface = None
        self._statusicon = None
        self._statusicon_ai = None
        self._window_hide_timer = scheduler.Timer()

    def initialize(self, data_controller):
        self.window = KupferWindow(Gtk.WindowType.TOPLEVEL)
        self.window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        #data_controller = data.DataController()
        data_controller.connect("launched-action", self.launch_callback)
        data_controller.connect("command-result", self.result_callback)

        self.interface = Interface(data_controller, self.window)
        self.interface.connect("launched-action", self.launch_callback)
        self.interface.connect("cancelled", self._cancelled)
        self.window.connect("map-event", self._on_window_map_event)
        self._setup_window()

        # Accept drops
        self.window.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.window.drag_dest_add_uri_targets()
        self.window.drag_dest_add_text_targets()
        self.window.connect("drag-data-received", self._on_drag_data_received)

    def _on_window_map_event(self, *args):
        self.interface.update_third()

    def show_statusicon(self):
        if not self._statusicon:
            self._statusicon = self._setup_gtk_status_icon(self._setup_menu())
        try:
            self._statusicon.set_visible(True)
        except AttributeError:
            pass

    def hide_statusicon(self):
        if self._statusicon:
            try:
                self._statusicon.set_visible(False)
            except AttributeError:
                self._statusicon = None

    def _showstatusicon_changed(self, setctl, section, key, value):
        "callback from SettingsController"
        if value:
            self.show_statusicon()
        else:
            self.hide_statusicon()

    def show_statusicon_ai(self):
        if not self._statusicon_ai:
            self._statusicon_ai = self._setup_appindicator(self._setup_menu())
        if not self._statusicon_ai:
            return
        self._statusicon_ai.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    def hide_statusicon_ai(self):
        if self._statusicon_ai:
            self._statusicon_ai.set_status(AppIndicator3.IndicatorStatus.PASSIVE)

    def _showstatusicon_ai_changed(self, setctl, section, key, value):
        if value:
            self.show_statusicon_ai()
        else:
            self.hide_statusicon_ai()

    def _setup_menu(self, context_menu=False):
        menu = Gtk.Menu()
        menu.set_name("kupfer-menu")

        def submenu_callback(menuitem, callback):
            callback()
            return True

        def add_menu_item(icon, callback, label=None, with_ctx=True):
            def mitem_handler(menuitem, callback):
                if with_ctx:
                    event_time = Gtk.get_current_event_time()
                    ui_ctx = uievents.gui_context_from_widget(event_time, menuitem)
                    callback(ui_ctx)
                else:
                    callback()
                if context_menu:
                    self.put_away()
                return True

            mitem = None
            if label and not icon:
                mitem = Gtk.MenuItem(label=label)
            else:
                mitem = Gtk.ImageMenuItem.new_from_stock(icon)
            mitem.connect("activate", mitem_handler, callback)
            menu.append(mitem)

        if context_menu:
            add_menu_item(Gtk.STOCK_CLOSE, self.put_away, with_ctx=False)
        else:
            add_menu_item(None, self.activate, _("Show Main Interface"))
        menu.append(Gtk.SeparatorMenuItem())
        if context_menu:
            for name, func in self.interface.get_context_actions():
                mitem = Gtk.MenuItem(label=name)
                mitem.connect("activate", submenu_callback, func)
                menu.append(mitem)
            menu.append(Gtk.SeparatorMenuItem())

        add_menu_item(Gtk.STOCK_PREFERENCES, kupferui.show_preferences)
        add_menu_item(Gtk.STOCK_HELP, kupferui.show_help)
        add_menu_item(Gtk.STOCK_ABOUT, kupferui.show_about_dialog)
        menu.append(Gtk.SeparatorMenuItem())
        add_menu_item(Gtk.STOCK_QUIT, self.quit, with_ctx=False)
        menu.show_all()

        return menu

    def _setup_gtk_status_icon(self, menu):
        status = Gtk.StatusIcon.new_from_icon_name(version.ICON_NAME)
        status.set_tooltip_text(version.PROGRAM_NAME)

        status.connect("popup-menu", self._popup_menu, menu)
        status.connect("activate", self.show_hide)
        return status

    def _setup_appindicator(self, menu):
        if AppIndicator3 is None:
            return None
        indicator = AppIndicator3.Indicator.new(version.PROGRAM_NAME,
            version.ICON_NAME,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        indicator.set_menu(menu)
        return indicator

    def _setup_window(self):
        """
        Returns window
        """

        self.window.connect("delete-event", self._close_window)
        self.window.connect("focus-out-event", self._lost_focus)
        self.window.connect("button-press-event", self._window_frame_clicked)
        widget = self.interface.get_widget()
        widget.show()

        # Build the window frame with its top bar
        topbar = Gtk.HBox()
        vbox = Gtk.VBox()
        vbox.pack_start(topbar, False, False, 0)
        vbox.pack_start(widget, True, True, 0)
        vbox.show()
        self.window.add(vbox)
        title = Gtk.Label.new("")
        button = Gtk.Label.new("")
        l_programname = version.PROGRAM_NAME.lower()
        # The text on the general+context menu button
        btext = "<b>%s \N{GEAR}</b>" % (l_programname, )
        button.set_markup(btext)
        button_box = Gtk.EventBox()
        button_box.set_visible_window(False)
        button_adj = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        button_adj.set_padding(0, 2, 0, 3)
        button_adj.add(button)
        button_box.add(button_adj)
        button_box.connect("button-press-event", self._context_clicked)
        button_box.connect("enter-notify-event", self._button_enter,
                           button, btext)
        button_box.connect("leave-notify-event", self._button_leave,
                           button, btext)
        button.set_name("kupfer-menu-button")
        title_align = Gtk.Alignment.new(0, 0.5, 0, 0)
        title_align.add(title)
        topbar.pack_start(title_align, True, True, 0)
        topbar.pack_start(button_box, False, False, 0)
        topbar.show_all()

        self.window.set_title(version.PROGRAM_NAME)
        self.window.set_icon_name(version.ICON_NAME)
        self.window.set_type_hint(self._window_type_hint())
        self.window.set_property("skip-taskbar-hint", True)
        self.window.set_keep_above(True)

        if not text_direction_is_ltr():
            self.window.set_gravity(Gdk.GRAVITY_NORTH_EAST)
        # Setting not resizable changes from utility window
        # on metacity
        self.window.set_resizable(False)

    def _window_type_hint(self):
        type_hint = Gdk.WindowTypeHint.UTILITY
        hint_name = kupfer.config.get_kupfer_env("WINDOW_TYPE_HINT").upper()
        if hint_name:
            hint_enum = getattr(Gdk.WindowTypeHint, hint_name, None)
            if hint_enum is None:
                self.output_error("No such Window Type Hint", hint_name)
                self.output_error("Existing type hints:")
                for name in dir(Gdk.WindowTypeHint):
                    if name.upper() == name:
                        self.output_error(name)
            else:
                type_hint = hint_enum
        return type_hint

    def _window_frame_clicked(self, widget, event):
        "Start drag when the window is clicked"
        widget.begin_move_drag(event.button,
                int(event.x_root), int(event.y_root), event.time)

    def _context_clicked(self, widget, event):
        "The context menu label was clicked"
        menu = self._setup_menu(True)
        menu.set_screen(self.window.get_screen())
        menu.popup(None, None, None, None, event.button, event.time)
        return True

    def _button_enter(self, widget, event, button, udata):
        "Pointer enters context menu button"
        button.set_markup("<u>" + udata + "</u>")

    def _button_leave(self, widget, event, button, udata):
        "Pointer leaves context menu button"
        button.set_markup(udata)

    def _popup_menu(self, status_icon, button, activate_time, menu):
        """
        When the StatusIcon is right-clicked
        """
        menu.popup(None, None, Gtk.StatusIcon.position_menu, status_icon, button, activate_time)

    def launch_callback(self, sender):
        # Separate window hide from the action being
        # done. This is to solve a window focus bug when
        # we switch windows using an action
        self.interface.did_launch()
        self._window_hide_timer.set_ms(100, self.put_away)

    def result_callback(self, sender, result_type, ui_ctx):
        self.interface.did_get_result()
        if ui_ctx:
            self.on_present(sender, ui_ctx.get_display(), ui_ctx.get_timestamp())
        else:
            self.on_present(sender, "", Gtk.get_current_event_time())

    def _lost_focus(self, window, event):
        if not kupfer.config.has_capability("HIDE_ON_FOCUS_OUT"):
            return
        # Close at unfocus.
        # Since focus-out-event is triggered even
        # when we click inside the window, we'll
        # do some additional math to make sure that
        # that window won't close if the mouse pointer
        # is over it.
        _gdkwindow, x, y, mods = window.get_screen().get_root_window().get_pointer()
        w_x, w_y = window.get_position()
        w_w, w_h = window.get_size()
        if (x not in range(w_x, w_x + w_w) or
            y not in range(w_y, w_y + w_h)):
            self._window_hide_timer.set_ms(50, self.put_away)

    def _monitors_changed(self, *ignored):
        self._center_window()

    def is_current_display(self, displayname):
        def norm_name(name):
            "Make :0.0 out of :0"
            if name[-2] == ":":
                return name + ".0"
            return name
        if not self.window.has_screen():
            return False
        cur_disp = self.window.get_screen().get_display().get_name()
        return norm_name(cur_disp) == norm_name(displayname)

    def _window_put_on_screen(self, screen):
        if self.current_screen_handler:
            scr = self.window.get_screen()
            scr.disconnect(self.current_screen_handler)
        if False:
            rgba = screen.get_rgba_colormap()
            if rgba:
                self.window.unrealize()
                self.window.set_screen(screen)
                self.window.set_colormap(rgba)
                self.window.realize()
        else:
            self.window.set_screen(screen)
        self.current_screen_handler = \
            screen.connect("monitors-changed", self._monitors_changed)
        self.current_screen = screen

    def _center_window(self, displayname=None):
        """Center Window on the monitor the pointer is currently on"""
        def norm_name(name):
            "Make :0.0 out of :0"
            if name[-2] == ":":
                return name + ".0"
            return name
        if not displayname and self.window.has_screen():
            display = self.window.get_display()
        else:
            display = uievents.GUIEnvironmentContext.ensure_display_open(displayname)
        screen, x, y, modifiers = display.get_pointer()
        self._window_put_on_screen(screen)
        monitor_nr = screen.get_monitor_at_point(x, y)
        geo = screen.get_monitor_geometry(monitor_nr)
        wid, hei = self.window.get_size()
        midx = geo.x + geo.width / 2 - wid / 2
        midy = geo.y + geo.height / 2 - hei / 2
        self.window.move(midx, midy)
        uievents.GUIEnvironmentContext._try_close_unused_displays(screen)

    def _should_recenter_window(self):
        """Return True if the mouse pointer and the window
        are on different monitors.
        """
        # Check if the GtkWindow was realized yet
        if not self.window.get_realized():
            return True
        display = self.window.get_screen().get_display()
        screen, x, y, modifiers = display.get_pointer()
        return (screen.get_monitor_at_point(x,y) !=
                screen.get_monitor_at_window(self.window.get_window()))

    def activate(self, sender=None):
        dispname = self.window.get_screen().make_display_name()
        self.on_present(sender, dispname, Gtk.get_current_event_time())

    def on_present(self, sender, display, timestamp):
        """Present on @display, where None means default display"""
        self._window_hide_timer.invalidate()
        if not display:
            display = Gdk.Display.get_default().get_name()
        if (self._should_recenter_window() or
            not self.is_current_display(display)):
            self._center_window(display)
        self.window.stick()
        self.window.present_with_time(timestamp)
        self.window.get_window().focus(timestamp=timestamp)
        self.interface.focus()

    def put_away(self):
        self.interface.put_away()
        self.window.hide()

    def _cancelled(self, widget):
        self.put_away()

    def on_show_hide(self, sender, display, timestamp):
        """
        Toggle activate/put-away
        """
        if self.window.get_property("visible"):
            self.put_away()
        else:
            self.on_present(sender, display, timestamp)

    def show_hide(self, sender):
        "GtkStatusIcon callback"
        self.on_show_hide(sender, "", Gtk.get_current_event_time())

    def _key_binding(self, keyobj, keybinding_number, display, timestamp):
        """Keybinding activation callback"""
        if keybinding_number == keybindings.KEYBINDING_DEFAULT:
            self.on_show_hide(keyobj, display, timestamp)
        elif keybinding_number == keybindings.KEYBINDING_MAGIC:
            self.on_present(keyobj, display, timestamp)
            self.interface.select_selected_text()
            self.interface.select_selected_file()

    def _on_drag_data_received(self, widget, context, x, y, data, info, time):
        uris = data.get_uris()
        if uris:
            self.interface.put_files(uris, paths=False)
        else:
            self.interface.put_text(data.get_text())

    def on_put_text(self, sender, text, display, timestamp):
        """We got a search text from dbus"""
        self.on_present(sender, display, timestamp)
        self.interface.put_text(text)

    def on_put_files(self, sender, fileuris, display, timestamp):
        self.on_present(sender, display, timestamp)
        self.interface.put_files(fileuris, paths=True)

    def on_execute_file(self, sender, filepath, display, timestamp):
        self.interface.execute_file(filepath, display, timestamp)

    def _close_window(self, window, event):
        self.put_away()
        return True

    def _destroy(self, widget, data=None):
        self.quit()

    def _sigterm(self, signal, frame):
        self.output_info("Caught signal", signal, "exiting..")
        self.quit()

    def _on_early_interrupt(self, signal, frame):
        sys.exit(1)

    def save_data(self):
        """Save state before quit"""
        sch = scheduler.GetScheduler()
        sch.finish()

    def quit(self, sender=None):
        Gtk.main_quit()

    def quit_now(self):
        """Quit immediately (state save should already be done)"""
        raise SystemExit

    def _session_save(self, *args):
        """Old-style session save callback.
        ret True on successful
        """
        # No quit, only save
        self.output_info("Saving for logout...")
        self.save_data()
        return True

    def _session_die(self, *args):
        """Session callback on session end
        quit now, without saving, since we already do that on
        Session save!
        """
        self.quit_now()

    def lazy_setup(self):
        """Do all setup that can be done after showing main interface.
        Connect to desktop services (keybinding callback, session logout
        callbacks etc).
        """
        from kupfer.ui import session

        self.output_debug("in lazy_setup")

        setctl = settings.GetSettingsController()
        if setctl.get_show_status_icon():
            self.show_statusicon()
        if setctl.get_show_status_icon_ai():
            self.show_statusicon_ai()
        setctl.connect("value-changed::kupfer.showstatusicon",
                       self._showstatusicon_changed)
        setctl.connect("value-changed::kupfer.showstatusicon_ai",
                       self._showstatusicon_ai_changed)
        keystr = setctl.get_keybinding()
        magickeystr = setctl.get_magic_keybinding()

        if keystr:
            succ = keybindings.bind_key(keystr)
            self.output_info("Trying to register %s to spawn kupfer.. %s"
                    % (keystr, "success" if succ else "failed"))


        if magickeystr:
            succ = keybindings.bind_key(magickeystr,
                    keybindings.KEYBINDING_MAGIC)
            self.output_debug("Trying to register %s to spawn kupfer.. %s"
                    % (magickeystr, "success" if succ else "failed"))
        keyobj = keybindings.GetKeyboundObject()
        keyobj.connect("keybinding", self._key_binding)

        signal.signal(signal.SIGINT, self._sigterm)
        signal.signal(signal.SIGTERM, self._sigterm)
        signal.signal(signal.SIGHUP, self._sigterm)

        client = session.SessionClient()
        client.connect("save-yourself", self._session_save)
        client.connect("die", self._session_die)

        self.output_debug("finished lazy_setup")

    def main(self, quiet=False):
        """Start WindowController, present its window (if not @quiet)"""
        signal.signal(signal.SIGINT, self._on_early_interrupt)

        try:
            # NOTE: For a *very short* time we will use both APIs
            kserv1 = listen.Service()
            kserv2 = listen.ServiceNew()
        except listen.AlreadyRunningError:
            self.output_info("An instance is already running, exiting...")
            self.quit_now()
        except listen.NoConnectionError:
            kserv1 = None
            kserv2 = None
        else:
            keyobj = keybindings.GetKeyboundObject()
            keyobj.connect("bound-key-changed",
                           lambda x,y,z: kserv1.BoundKeyChanged(y,z))
            kserv1.connect("relay-keys", keyobj.relayed_keys)

        # Load data
        data_controller = data.DataController()
        sch = scheduler.GetScheduler()
        sch.load()
        # Now create UI and display
        self.initialize(data_controller)
        sch.display()

        if kserv1:
            kserv1.connect("present", self.on_present)
            kserv1.connect("show-hide", self.on_show_hide)
            kserv1.connect("put-text", self.on_put_text)
            kserv1.connect("put-files", self.on_put_files)
            kserv1.connect("execute-file", self.on_execute_file)
            kserv1.connect("quit", self.quit)
        if kserv2:
            kserv2.connect("present", self.on_present)
            kserv2.connect("show-hide", self.on_show_hide)
            kserv2.connect("put-text", self.on_put_text)
            kserv2.connect("put-files", self.on_put_files)
            kserv2.connect("execute-file", self.on_execute_file)
            kserv2.connect("quit", self.quit)

        if not quiet:
            self.activate()
        GLib.idle_add(self.lazy_setup)

        def do_main_iterations(max_events=0):
            # use sentinel form of iter
            for idx, pending in enumerate(iter(Gtk.events_pending, False)):
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
        if kserv1:
            kserv1.unregister()
        if kserv2:
            kserv2.unregister()
        keybindings.bind_key(None, keybindings.KEYBINDING_DEFAULT)
        keybindings.bind_key(None, keybindings.KEYBINDING_MAGIC)

        do_main_iterations(100)
        # if we are still waiting, print a message
        if Gtk.events_pending():
            self.output_info("Waiting for tasks to finish...")
            do_main_iterations()
