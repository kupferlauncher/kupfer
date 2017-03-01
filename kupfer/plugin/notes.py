"""
It *should* be possible to support Tomboy and Gnote equally since
they support the same DBus protocol. This plugin takes this assumption.
"""

__kupfer_name__ = _("Notes")
__kupfer_sources__ = ("NotesSource", )
__kupfer_actions__ = (
        "AppendToNote",
        "AppendTextToNote",
        "CreateNote",
        "GetNoteSearchResults",
    )
__description__ = _("Gnote or Tomboy notes")
__version__ = "2017.2"
__author__ = ""

import os
import time
import xml.sax.saxutils

from gi.repository import GLib

import dbus
import xdg.BaseDirectory as base

from kupfer.objects import Action, Source, Leaf, TextLeaf, NotAvailableError, SourceLeaf
from kupfer.obj.apps import ApplicationSource
from kupfer.objects import TextSource
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

    set_prog = __kupfer_settings__["notes_application"]
    programs = (set_prog, ) if set_prog else PROGRAM_IDS

    for program in programs:
        service_name, obj_name, iface_name = PROGRAM_SERIVCES[program]
        if activate:
            _ignore, status = bus.start_service_by_name(service_name)
        else:
            if not bus.name_has_owner(service_name):
                continue

        try:
            searchobj = bus.get_object(service_name, obj_name)
        except dbus.DBusException as e:
            pretty.print_error(__name__, e)
            return
        return dbus.Interface(searchobj, iface_name)

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

class RetryDbusCalls(pretty.OutputMixin):
    """
    A d-bus interface wrapper for a proxy object; will retry a method
    call if it fails (a limited number of times)

    The method call must be async (with reply_handler and error_handler)
    """
    def __init__(self, proxy_object, retries=10):
        self.__obj = proxy_object
        self.__retries = retries

    @property
    def proxy_obj(self):
        """
        Return the inner proxy object. You can call methods synchronously on it.
        """
        return self.__obj

    def __getattr__(self, name):
        x = 0
        def proxy_method(*args, error_handler=None, **kwargs):
            def make_call():
                getattr(self.__obj, name)(*args, error_handler=error_handler_, **kwargs)
            def error_handler_(exc):
                nonlocal x
                x += 1
                if (x > self.__retries or
                    exc.get_dbus_name() != "org.freedesktop.DBus.Error.UnknownMethod"):
                    return error_handler(exc)
                self.output_debug("retrying", name, "because of", exc)
                GLib.timeout_add(25 * x, make_call)
            return make_call()
        return proxy_method

def make_error_handler(ctx):
    def error_handler(exc):
        pretty.print_debug(__name__, exc)
        ctx.register_late_error(NotAvailableError(__kupfer_settings__["notes_application"]))
    return error_handler

class Open (Action):
    action_accelerator = "o"
    def __init__(self):
        Action.__init__(self, _("Open"))
    def wants_context(self):
        return True
    def activate(self, leaf, ctx):
        noteuri = leaf.object
        notes = RetryDbusCalls(_get_notes_interactive())
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
        notes = RetryDbusCalls(_get_notes_interactive())
        noteuri = iobj.object
        text = leaf.object

        def reply_note_plain_text(contents):
            if not contents.endswith("\n"):
                contents += "\n"
            contents += text
            if not text.endswith("\n"):
                contents += "\n"
            notes.SetNoteContents(noteuri, contents,
                                  reply_handler=reply_noop,
                                  error_handler=make_error_handler(ctx))

        def reply_note_xml(xmlcontents):
            # NOTE: We search and replace in the XML here
            endtag = "</note-content>"
            xmltext = xml.sax.saxutils.escape(text)
            xmlcontents = xmlcontents.replace(endtag, "\n%s%s" % (xmltext, endtag))
            notes.SetNoteCompleteXml(noteuri, xmlcontents,
                                     reply_handler=reply_noop,
                                     error_handler=make_error_handler(ctx))

        if __kupfer_settings__["notes_application"] == "kzrnote":
            notes.GetNoteContents(noteuri,
                                  reply_handler=reply_note_plain_text,
                                  error_handler=make_error_handler(ctx))
        else:
            notes.GetNoteCompleteXml(noteuri,
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

class AppendTextToNote (AppendToNote):
    def __init__(self):
        Action.__init__(self, _("Append..."))
    def wants_context(self):
        return True
    def activate(self, leaf, iobj, ctx):
        return super().activate(iobj, leaf, ctx)

    def item_types(self):
        return super().object_types()
    def requires_object(self):
        return True
    def object_types(self):
        return super().item_types()
    def object_source(self, for_item=None):
        return TextSource()

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

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        notes = RetryDbusCalls(_get_notes_interactive())
        text = _prepare_note_text(leaf.object)

        def _created_note(noteuri):
            nonlocal notes
            notes = notes.proxy_obj
            # FIXME: For Gnote we have to call DisplayNote
            # else we can't change its contents
            notes.DisplayNote(noteuri)
            notes.SetNoteContents(noteuri, text)

        notes.CreateNote(reply_handler=_created_note,
                         error_handler=make_error_handler(ctx))


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

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        query = leaf.object.lower()
        notes = RetryDbusCalls(_get_notes_interactive())

        def search_reply(noteuris):
            ctx.register_late_result(NoteSearchSource(query, noteuris))

        notes.SearchNotes(query, False,
                          reply_handler=search_reply,
                          error_handler=make_error_handler(ctx))

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Show search results for this query")

class NoteSearchSource (Source):
    def __init__(self, query, noteuris):
        self.query = query.lower()
        Source.__init__(self, _("Notes"))
        self.noteuris = noteuris

    def get_items(self):
        notes = _get_notes_interactive()
        for noteuri in self.noteuris:
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
        if new:
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

