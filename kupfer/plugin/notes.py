"""
It *should* be possible to support Tomboy and Gnote equally since
they support the same DBus protocol. This plugin takes this assumption.
"""

__kupfer_name__ = _("Notes")
__kupfer_sources__ = ("NotesSource", )
__kupfer_actions__ = (
        "AppendToNote",
        "CreateNote",
        "GetNoteSearchResults",
    )
__description__ = _("Gnote or Tomboy notes")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
import time
import xml.sax.saxutils

import dbus
import xdg.BaseDirectory as base

from kupfer.objects import Action, Source, Leaf, TextLeaf, NotAvailableError
from kupfer.obj.apps import ApplicationSource
from kupfer import icons, plugin_support
from kupfer import pretty, textutils
from kupfer.weaklib import dbus_signal_connect_weakly


PROGRAM_IDS = ["gnote", "tomboy", "kzrnote"]
__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "notes_application",
        "label": _("Work with application"),
        "type": str,
        "value": "",
        "alternatives": ["",] + PROGRAM_IDS
    },
)

plugin_support.check_dbus_connection()

def unicode_strftime(fmt, time_tuple=None):
    return time.strftime(fmt, time_tuple)

## Tuples of  service name, object name, interface name
PROGRAM_SERIVCES = {
    "gnote": ("org.gnome.Gnote",
              "/org/gnome/Gnote/RemoteControl",
              "org.gnome.Gnote.RemoteControl"),
    "tomboy": ("org.gnome.Tomboy",
               "/org/gnome/Tomboy/RemoteControl",
               "org.gnome.Tomboy.RemoteControl"),
    "kzrnote": ("io.github.kupferlauncher.kzrnote",
                "/io/github/kupferlauncher/kzrnote",
                "io.github.kupferlauncher.kzrnote"),
}

def _get_notes_interface(activate=False):
    """Return the dbus proxy object for our Note Application.

    if @activate, we will activate it over d-bus (start if not running)
    """
    bus = dbus.SessionBus()
    proxy_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')

    set_prog = __kupfer_settings__["notes_application"]
    programs = (set_prog, ) if set_prog else PROGRAM_IDS

    for program in programs:
        service_name, obj_name, iface_name = PROGRAM_SERIVCES[program]

        if not activate and not dbus_iface.NameHasOwner(service_name):
            continue

        try:
            searchobj = bus.get_object(service_name, obj_name)
        except dbus.DBusException as e:
            pretty.print_error(__name__, e)
            return
        notes = dbus.Interface(searchobj, iface_name)
        return notes

def _get_notes_interactive():
    """
    Return the dbus proxy object, activate if necessary,
    raise an OperationError if not available.
    """
    obj = _get_notes_interface(activate=True)
    if obj is None:
        raise NotAvailableError(__kupfer_settings__["notes_application"])
    return obj

def reply_noop(*args):
    pass

def make_error_handler(ctx):
    def error_handler(exc):
        pretty.print_debug(__name__, exc)
        ctx.register_late_error(NotAvailableError(__kupfer_settings__["notes_application"]))
    return error_handler

class Open (Action):
    def __init__(self):
        Action.__init__(self, _("Open"))
    def wants_context(self):
        return True
    def activate(self, leaf, ctx):
        noteuri = leaf.object
        notes = _get_notes_interactive()
        notes.DisplayNote(noteuri,
                          reply_handler=reply_noop,
                          error_handler=make_error_handler(ctx))
    def get_description(self):
        return _("Open with notes application")
    def get_gicon(self):
        app_icon = icons.get_gicon_with_fallbacks(None, PROGRAM_IDS)
        return icons.ComposedIcon(self.get_icon_name(), app_icon)

class AppendToNote (Action):
    def __init__(self):
        Action.__init__(self, _("Append to Note..."))

    def wants_context(self):
        return True
    def activate(self, leaf, iobj, ctx):
        notes = _get_notes_interactive()
        noteuri = iobj.object
        text = leaf.object

        # NOTE: We search and replace in the XML here
        def reply_note_xml(xmlcontents):
            pretty.print_debug(__name__, "reply_note_xml", xmlcontents)
            endtag = "</note-content>"
            xmltext = xml.sax.saxutils.escape(text)
            xmlcontents = xmlcontents.replace(endtag, "\n%s%s" % (xmltext, endtag))
            notes.SetNoteCompleteXml(noteuri, xmlcontents,
                                     reply_handler=reply_noop,
                                     error_handler=make_error_handler(ctx))

        xmlcontents = notes.GetNoteCompleteXml(noteuri,
                                               reply_handler=reply_note_xml,
                                               error_handler=make_error_handler(ctx))

    def item_types(self):
        yield TextLeaf
    def requires_object(self):
        return True
    def object_types(self):
        yield Note
    def object_source(self, for_item=None):
        return NotesSource()
    def get_description(self):
        return _("Add text to existing note")
    def get_icon_name(self):
        return "list-add"

def _prepare_note_text(text):
    ## split the text into a title + newline + rest of the text
    ## if we only get the title, put in two helpful newlines
    title, body = textutils.extract_title_body(text)
    if body.lstrip():
        return "%s\n%s" % (title, body)
    else:
        return "%s\n\n" % (title,)

class CreateNote (Action):
    def __init__(self):
        Action.__init__(self, _("Create Note"))

    def activate(self, leaf):
        notes = _get_notes_interactive()
        text = _prepare_note_text(leaf.object)
        # FIXME: For Gnote we have to call DisplayNote
        # else we can't change its contents
        noteuri = notes.CreateNote()
        notes.DisplayNote(noteuri)
        notes.SetNoteContents(noteuri, text)

    def item_types(self):
        yield TextLeaf
    def get_description(self):
        return _("Create a new note from this text")
    def get_icon_name(self):
        return "document-new"

class GetNoteSearchResults (Action):
    def __init__(self):
        Action.__init__(self, _("Get Note Search Results..."))

    def is_factory(self):
        return True

    def activate(self, leaf):
        query = leaf.object
        return NoteSearchSource(query)

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Show search results for this query")

class NoteSearchSource (Source):
    def __init__(self, query):
        self.query = query.lower()
        Source.__init__(self, _("Notes"))

    def get_items(self):
        notes = _get_notes_interactive()
        noteuris = notes.SearchNotes(self.query, False)
        for noteuri in noteuris:
            title = notes.GetNoteTitle(noteuri)
            date = notes.GetNoteChangeDate(noteuri)
            yield Note(noteuri, title, date)

    def repr_key(self):
        return self.query

    def get_gicon(self):
        return icons.get_gicon_with_fallbacks(None, PROGRAM_IDS)

    def provides(self):
        yield Note

class Note (Leaf):
    """The Note Leaf's represented object is the Note URI"""
    def __init__(self, obj, name, date):
        self.changedate = date
        Leaf.__init__(self, obj, name)
    def get_actions(self):
        yield Open()
    def repr_key(self):
        # the Note URI is unique&persistent for each note
        return self.object
    def get_description(self):
        today_date = time.localtime()[:3]
        yest_date = time.localtime(time.time() - 3600*24)[:3]
        change_time = time.localtime(self.changedate)

        if today_date == change_time[:3]:
            time_str = _("today, %s") % unicode_strftime("%X", change_time)
        elif yest_date == change_time[:3]:
            time_str = _("yesterday, %s") % unicode_strftime("%X", change_time)
        else:
            time_str = unicode_strftime("%c", change_time)
        # TRANS: Note description, %s is last changed time in locale format
        return _("Last updated %s") % time_str
    def get_icon_name(self):
        return "text-x-generic"

class ClassProperty (property):
    """Subclass property to make classmethod properties possible"""
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()

class NotesSource (ApplicationSource):
    def __init__(self):
        Source.__init__(self, _("Notes"))
        self._notes = []

    def initialize(self):
        """Set up filesystem monitors to catch changes"""
        # We monitor all directories that exist of a couple of candidates
        dirs = []
        for program in PROGRAM_IDS:
            notedatapaths = (os.path.join(base.xdg_data_home, program),
                    os.path.expanduser("~/.%s" % program))
            dirs.extend(notedatapaths)
        self.monitor_token = self.monitor_directories(*dirs)

        set_prog = __kupfer_settings__["notes_application"]
        if set_prog in PROGRAM_SERIVCES:
            bus_name = PROGRAM_SERIVCES[set_prog][0]
            bus = dbus.SessionBus()
            dbus_signal_connect_weakly(bus, "NameOwnerChanged", self._name_owner_changed,
                                       dbus_interface="org.freedesktop.DBus",
                                       arg0=bus_name)

    def _name_owner_changed(self, name, old, new):
        if new is not None:
            self.mark_for_update()

    def _update_cache(self, notes):
        try:
            noteuris = notes.ListAllNotes()
        except dbus.DBusException as e:
            self.output_error("%s: %s" % (type(e).__name__, e))
            return

        templates = notes.GetAllNotesWithTag("system:template")

        self._notes = []
        for noteuri in noteuris:
            if noteuri in templates:
                continue
            title = notes.GetNoteTitle(noteuri)
            date = notes.GetNoteChangeDate(noteuri)
            self._notes.append((noteuri, title, date))

    def get_items(self):
        notes = _get_notes_interface()
        if notes:
            self._update_cache(notes)
        for noteuri, title, date in self._notes:
            yield Note(noteuri, title, date=date)

    def provides(self):
        yield Note

    def get_gicon(self):
        return icons.get_gicon_with_fallbacks(None, PROGRAM_IDS)

    def get_icon_name(self):
        return "gnote"

    @ClassProperty
    @classmethod
    def appleaf_content_id(cls):
        return __kupfer_settings__["notes_application"] or PROGRAM_IDS

