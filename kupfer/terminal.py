import os

_TERMINALS = {}

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

def register_terminal(id_, terminal_description):
	"""Register @terminal_description (can be used by plugins)"""
	_TERMINALS[id_] = terminal_description

def unregister_terminal(terminal_id):
	_TERMINALS.pop(terminal_id, None)

def is_known_terminal_executable(exearg):
	"Return True if @exearg is a known terminal"
	for term in _TERMINALS.itervalues():
		if exearg == term.argv[0]:
			return True
	return False

def get_valid_terminals():
	""" Yield (identifier, unicode name) tuples """
	for id_, term in _TERMINALS.iteritems():
		# iterate over $PATH directories
		PATH = os.environ.get("PATH") or os.defpath
		for execdir in PATH.split(os.pathsep):
			exepath = os.path.join(execdir, term.argv[0])
			if os.access(exepath, os.R_OK|os.X_OK) and os.path.isfile(exepath):
				yield (id_, unicode(term))
				break

def get_configured_terminal():
	"""
	Return the configured Terminal object
	"""
	from kupfer.core import settings
	setctl = settings.GetSettingsController()
	id_ = setctl.get_preferred_tool('terminal')
	return _TERMINALS.get(id_) or _TERMINALS["default"]

# Insert default terminals

register_terminal("gnome-terminal",
                  Terminal(_("GNOME Terminal"), ["gnome-terminal"],
                  "-x", "gnome-terminal.desktop", True))

register_terminal("xfce4-terminal",
                  Terminal(_("XFCE Terminal"), ["xfce4-terminal"],
                  "-x", "xfce4-terminal.desktop", True))

register_terminal("urxvt",
                  Terminal(_("Urxvt"), ["urxvt"],
                  "-e", "urxvt.desktop", False))

register_terminal("lxterminal",
                  Terminal(_("LXTerminal"), ["lxterminal"],
                  "-e", "lxterminal.desktop", False))

register_terminal("default",
                  Terminal(_("X Terminal"), ["xterm"],
                  "-e", "xterm.desktop", False))


