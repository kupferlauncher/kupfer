import gobject

from kupfer import pretty

KEYBINDING_DEFAULT = 1

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
		self.emit("keybinding", target, time)

gobject.signal_new("keybinding", KeyboundObject, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_INT))

_currently_bound = {}

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
		pretty.print_error("Could not import keybinder, keybindings disabled!")
		return False

	keybinding_target = int(keybinding_target)
	callback = lambda : GetKeyboundObject()._keybinding(keybinding_target)
	if len(keystr) == 1:
		pretty.print_error(__name__, "Refusing to bind key", repr(keystr))
		return False

	succ = True
	if keystr:
		try:
			succ = keybinder.bind(keystr, callback)
			pretty.print_debug(__name__, "binding", repr(keystr))
		except KeyError, exc:
			pretty.print_error(__name__, exc)
			succ = False
	if succ:
		old_keystr = get_currently_bound_key(keybinding_target)
		if old_keystr and old_keystr != keystr:
			keybinder.unbind(old_keystr)
			pretty.print_debug(__name__, "unbinding", repr(old_keystr))
		_register_bound_key(keystr, keybinding_target)
	return succ

