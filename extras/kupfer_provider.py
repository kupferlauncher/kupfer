# Copyright (C) 2009 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA

"""
This is a Nautilus Extension for Kupfer

It is a Menu Provider, but needs not show a menu. This Extension will be
updated with all file selections in Nautilus, and broadcast them over a D-Bus
signal.
"""

import locale

import dbus
import dbus.glib
from dbus.gobject_service import ExportedGObject
import gio
import gobject

import nautilus

service_name="se.kaizer.FileSelection"
interface_name="se.kaizer.FileSelection"
object_path = "/se/kaizer/FileSelection"

class Object (ExportedGObject):
	@dbus.service.signal(interface_name, signature="asi")
	def SelectionChanged(self, uris, window_id):
		"""Nautilus selection changed.

		@uris: an array of URI strings.
		@window_id: An ID for the window where the selection happened
		"""
		return uris

class KupferSelectionProvider(nautilus.MenuProvider):
	def __init__(self):
		selfname = type(self).__name__
		print "Initializing", selfname
		self.cursel = None
		self.max_threshold = 500
		try:
			session_bus = dbus.Bus()
		except dbus.DBusException, exc:
			print exc
			self.service = None
		else:
			if session_bus.name_has_owner(service_name):
				self.service = None
				print selfname, "already running"
			else:
				bus_name = dbus.service.BusName(service_name, bus=session_bus)
				self.service = Object(bus_name, object_path=object_path)
	
	def get_file_items(self, window, files):
		"""We show nothing, but we get info on files that are selected

		Ask GIO for the file path of each URI item, and pass on any that
		have a defined path.

		We use a threshold on the files so that we don't generate too much
		traffic; with more than 500 files selected, we simply send nothing.
		"""
		if len(files) > self.max_threshold:
			return []
		window_id = window.window.xid if window.window else 0
		uris = [f.get_uri() for f in files]
		if self.cursel != (uris, window_id) and self.service:
			self.service.SelectionChanged(uris, window_id)
		self.cursel = (uris, window_id)
		return []
