"""
It *should* be possible to support Tomboy and Gnote equally since
they support the same DBus protocol. This plugin takes this assumption.
"""

import os
import time
import xml.sax.saxutils

import dbus
import xdg.BaseDirectory as base

from kupfer.objects import (Action, Source, Leaf, AppLeafContentMixin, TextLeaf,
		PicklingHelperMixin, FilesystemWatchMixin, )
from kupfer import icons, plugin_support

__kupfer_name__ = _("Notes")
__kupfer_sources__ = ("NotesSource", )
__kupfer_contents__ = ("NotesSource", )
__kupfer_actions__ = (
		"AppendToNote",
		"CreateNote",
	)
__description__ = _("Gnote or Tomboy notes")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

PROGRAM_IDS = ["gnote", "tomboy"]

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "notes_application",
		"label": _("Work with application"),
		"type": str,
		"value": "",
		"alternatives": ["",] + PROGRAM_IDS
	},
)

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
		service_name = "org.gnome.%s" % program.title()
		obj_name = "/org/gnome/%s/RemoteControl" % program.title()
		iface_name = "org.gnome.%s.RemoteControl" % program.title()

		if not activate and not dbus_iface.NameHasOwner(service_name):
			continue

		try:
			searchobj = bus.get_object(service_name, obj_name)
		except dbus.DBusException, e:
			pretty.print_error(__name__, e)
			return
		notes = dbus.Interface(searchobj, iface_name)
		return notes

class Open (Action):
	def __init__(self):
		Action.__init__(self, _("Open"))
	def activate(self, leaf):
		noteuri = leaf.object
		notes = _get_notes_interface(activate=True)
		notes.DisplayNote(noteuri)
	def get_description(self):
		return _("Open with notes application")
	def get_gicon(self):
		app_icon = icons.get_gicon_with_fallbacks(None, PROGRAM_IDS)
		return icons.ComposedIcon(self.get_icon_name(), app_icon)

class AppendToNote (Action):
	def __init__(self):
		Action.__init__(self, _("Append to Note..."))

	def activate(self, leaf, iobj):
		notes = _get_notes_interface(activate=True)
		noteuri = iobj.object
		text = leaf.object

		# NOTE: We search and replace in the XML here
		xmlcontents = notes.GetNoteCompleteXml(noteuri)
		endtag = u"</note-content>"
		xmltext = xml.sax.saxutils.escape(text)
		xmlcontents = xmlcontents.replace(endtag, u"\n%s%s" % (xmltext, endtag))
		notes.SetNoteCompleteXml(noteuri, xmlcontents)

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
		return "gtk-add"

class CreateNote (Action):
	def __init__(self):
		Action.__init__(self, _("Create Note"))

	def activate(self, leaf):
		notes = _get_notes_interface(activate=True)
		text = leaf.object
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
		return "gtk-new"

class Note (Leaf):
	"""The Note Leaf's represented object is the Note URI"""
	def __init__(self, obj, name, date):
		self.changedate = date
		Leaf.__init__(self, obj, name)
	def get_actions(self):
		yield Open()
	def get_description(self):
		time_str = time.strftime("%c", time.localtime(self.changedate))
		# TRANS: Note description, %s is last changed time in locale format
		return _("Last updated %s") % time_str
	def get_icon_name(self):
		return "text-x-generic"

class ClassProperty (property):
	"""Subclass property to make classmethod properties possible"""
	def __get__(self, cls, owner):
		return self.fget.__get__(None, owner)()

class NotesSource (AppLeafContentMixin, Source, PicklingHelperMixin,
		FilesystemWatchMixin):
	def __init__(self):
		Source.__init__(self, _("Notes"))
		self._notes = []
		self.unpickle_finish()

	def unpickle_finish(self):
		"""Set up filesystem monitors to catch changes"""
		# We monitor all directories that exist of a couple of candidates
		dirs = []
		for program in PROGRAM_IDS:
			notedatapaths = (os.path.join(base.xdg_data_home, program),
					os.path.expanduser("~/.%s" % program))
			dirs.extend(notedatapaths)
		self.monitor_token = self.monitor_directories(*dirs)

	def pickle_prepare(self):
		self.monitor_token = None

	def _update_cache(self, notes):
		try:
			noteuris = notes.ListAllNotes()
		except dbus.DBusException, e:
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

	def get_gicon(self):
		return icons.get_gicon_with_fallbacks(None, PROGRAM_IDS)

	def get_icon_name(self):
		return "gnote"

	@ClassProperty
	@classmethod
	def appleaf_content_id(cls):
		return __kupfer_settings__["notes_application"] or PROGRAM_IDS

