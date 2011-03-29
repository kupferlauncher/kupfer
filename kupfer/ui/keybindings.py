import gobject

from kupfer import pretty

KEYBINDING_DEFAULT = 1
KEYBINDING_MAGIC = 2

KEYRANGE_RESERVED = (3, 0x1000)
KEYRANGE_TRIGGERS = (0x1000, 0x2000)

_keybound_object = None
def GetKeyboundObject():
	"""Get the shared instance"""
	global _keybound_object
	if not _keybound_object:
		_keybound_object = KeyboundObject()
	return _keybound_object

class KeyboundObject (gobject.GObject):
	"""Keybinder object

	signals:
		keybinding (target, event_time)
		keybinding signal is triggered when the key bound
		for @target is triggered.
	"""
	__gtype_name__ = "KeyboundObject"
	def __init__(self):
		super(KeyboundObject, self).__init__()
	def _keybinding(self, target):
		import keybinder
		time = keybinder.get_current_event_time()
		self.emit("keybinding", target, "", time)
	def emit_bound_key_changed(self, keystring, is_bound):
		self.emit("bound-key-changed", keystring, is_bound)
	def relayed_keys(self, sender, keystring, display, timestamp):
		for target, key in _currently_bound.iteritems():
			if keystring == key:
				self.emit("keybinding", target, display, timestamp)

# Arguments: Target, Display, Timestamp
gobject.signal_new("keybinding", KeyboundObject, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN,
		(gobject.TYPE_INT, gobject.TYPE_STRING, gobject.TYPE_UINT))
# Arguments: Keystring, Boolean
gobject.signal_new("bound-key-changed", KeyboundObject, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN,
		(gobject.TYPE_STRING, gobject.TYPE_BOOLEAN,))

_currently_bound = {}

def get_all_bound_keys():
	return filter(bool, _currently_bound.values())

def get_current_event_time():
	"Return current event time as given by keybinder"
	try:
		import keybinder
	except ImportError:
		return 0
	return keybinder.get_current_event_time()

def _register_bound_key(keystr, target):
	_currently_bound[target] = keystr

def get_currently_bound_key(target=KEYBINDING_DEFAULT):
	return _currently_bound.get(target)

def bind_key(keystr, keybinding_target=KEYBINDING_DEFAULT):
	"""
	Bind @keystr, unbinding any previous key for @keybinding_target.
	If @keystr is a false value, any previous key will be unbound.
	"""
	try:
		import keybinder
	except ImportError:
		pretty.print_error(__name__, "Could not import keybinder, "
				"keybindings disabled!")
		return False

	keybinding_target = int(keybinding_target)
	callback = lambda : GetKeyboundObject()._keybinding(keybinding_target)
	if not _is_sane_keybinding(keystr):
		pretty.print_error(__name__, "Refusing to bind key", repr(keystr))
		return False

	succ = True
	if keystr:
		try:
			succ = keybinder.bind(keystr, callback)
			pretty.print_debug(__name__, "binding", repr(keystr))
			GetKeyboundObject().emit_bound_key_changed(keystr, True)
		except KeyError, exc:
			pretty.print_error(__name__, exc)
			succ = False
	if succ:
		old_keystr = get_currently_bound_key(keybinding_target)
		if old_keystr and old_keystr != keystr:
			keybinder.unbind(old_keystr)
			pretty.print_debug(__name__, "unbinding", repr(old_keystr))
			GetKeyboundObject().emit_bound_key_changed(old_keystr, False)
		_register_bound_key(keystr, keybinding_target)
	return succ


def _is_sane_keybinding(keystr):
	"Refuse keys that we absolutely do not want to bind"
	if keystr is None:
		return True
	if len(keystr) == 1 and keystr.isalnum():
		return False
	if keystr in set(["Return", "space", "BackSpace", "Escape"]):
		return False
	return True
