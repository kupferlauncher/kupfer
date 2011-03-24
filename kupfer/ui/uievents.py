import contextlib
import os

import gtk

from kupfer import pretty
from kupfer.ui import keybindings

class _internal_data (object):
	seq = 0
	current_event_time = 0

	@classmethod
	def inc_seq(cls):
		cls.seq = cls.seq + 1


def make_startup_notification_id():
	time = current_event_time()
	_internal_data.inc_seq()
	return "%s-%d-%s_TIME%d" % ("kupfer", os.getpid(), _internal_data.seq, time)

def current_event_time():
	return (gtk.get_current_event_time() or
	        keybindings.get_current_event_time() or
	        _internal_data.current_event_time)

def _parse_notify_id(startup_notification_id):
	"""
	Return timestamp or 0 from @startup_notification_id
	"""
	time = 0
	if "_TIME" in startup_notification_id:
		_ign, bstime = startup_notification_id.split("_TIME", 1)
		try:
			time = int(bstime)
		except ValueError:
			pass
	return time

@contextlib.contextmanager
def using_startup_notify_id(notify_id):
	"""
	Pass in a DESKTOP_STARTUP_ID

	with using_startup_notify_id(...):
		pass
	"""
	timestamp = _parse_notify_id(notify_id)
	if timestamp:
		gtk.gdk.notify_startup_complete_with_id(notify_id)
	try:
		pretty.print_debug(__name__, "Using startup id", repr(notify_id))
		_internal_data.current_event_time = timestamp
		yield
	finally:
		_internal_data.current_event_time = gtk.gdk.CURRENT_TIME

