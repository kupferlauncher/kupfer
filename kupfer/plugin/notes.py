"""
It *should* be possible to support Tomboy and Gnote equally since
they support the same DBus protocol. This plugin takes this assumption.
"""

import dbus

from kupfer.objects import Action, Source, Leaf, AppLeafContentMixin, TextLeaf
from kupfer import icons

__kupfer_name__ = _("Notes")
__kupfer_sources__ = ("NotesSource", )
__kupfer_contents__ = ("NotesSource", )
__kupfer_actions__ = (
		"AppendToNote",
	)
__description__ = _("Gnote or Tomboy notes")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

# the very secret priority list
PROGRAM_IDS = ("gnote", "tomboy")

def _get_notes_interface():
	bus = dbus.SessionBus()
	for program in PROGRAM_IDS:
		service_name = "org.gnome.%s" % program.title()
		obj_name = "/org/gnome/%s/RemoteControl" % program.title()
		iface_name = "org.gnome.%s.RemoteControl" % program.title()

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
		notes = _get_notes_interface()
		notes.DisplayNote(noteuri)
	def get_description(self):
		return _("Open with notes application")
	def get_gicon(self):
		app_icon = icons.get_gicon_with_fallbacks(None, PROGRAM_IDS)
		return icons.ComposedIcon(self.get_icon_name(), app_icon)

class Note (Leaf):
	"""The Note Leaf's represented object is the Note URI"""
	def get_actions(self):
		yield Open()
	def get_icon_name(self):
		return "text-x-generic"

class NotesSource (AppLeafContentMixin, Source):
	appleaf_content_id = PROGRAM_IDS
	def __init__(self):
		Source.__init__(self, _("Notes"))

	def get_items(self):
		notes = _get_notes_interface()
		if not notes:
			return

		try:
			noteuris = notes.ListAllNotes()
		except dbus.DBusException, e:
			self.output_error("%s: %s" % (type(e).__name__, e))
			return

		templates = notes.GetAllNotesWithTag("system:template")

		for noteuri in noteuris:
			if noteuri in templates:
				continue
			title = notes.GetNoteTitle(noteuri)
			yield Note(noteuri, title)

	def should_sort_lexically(self):
		return True

	def get_gicon(self):
		return icons.get_gicon_with_fallbacks(None, PROGRAM_IDS)

	def get_icon_name(self):
		return "gnote"
