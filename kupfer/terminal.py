
_TERMINALS = []

class Terminal (object):
	"""
	@id_ should be unique and if possible the
	application id
	"""
	def __init__(self, name, argv, exearg, id_, startup_notify=False):
		self.name = unicode(name)
		self.argv = list(argv)
		self.exearg = str(exearg)
		self.startup_notify = bool(startup_notify)
		self.app_id = str(id_)
	def __unicode__(self):
		return self.name
	def get_id(self):
		return self.app_id

def register_terminal(terminal_description):
	"""Register @terminal_description (can be used by plugins)"""
	_TERMINALS.append(terminal_description)

def unregister_terminal(terminal_id):
	_TERMINALS[:] = [t for t in _TERMINALS if t.app_id != terminal_id]

def get_configured_terminal():
	"""
	Return the configured Terminal object
	"""
	from kupfer.core import settings
	setctl = settings.SettingsController()
	id_ = setctl.get_preferred_tool('terminal')
	for term in _TERMINALS:
		if term.app_id == id_:
			return term
	return _TERMINALS[0]

# Insert default terminals

register_terminal(Terminal(_("GNOME Terminal"), ["gnome-terminal"],
                             "-x", "gnome-terminal.desktop", True))

register_terminal(Terminal(_("XFCE Terminal"), ["xfce4-terminal"],
                             "-x", "xfce4-terminal.desktop", True))

register_terminal(Terminal(_("Urxvt"), ["urxvt"],
                             "-e", "urxvt.desktop", False))

register_terminal(Terminal(_("X Terminal"), ["xterm"],
                             "-e", "xterm.desktop", False))

