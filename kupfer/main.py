import gettext
import locale
import sys

_debug = False

def setup_locale_and_gettext():
	"""Set up localization with gettext"""
	package_name = "kupfer"
	localedir = "./locale"
	try:
		from kupfer import version_subst
	except ImportError:
		pass
	else:
		package_name = version_subst.PACKAGE_NAME
		localedir = version_subst.LOCALEDIR
	# Install _() builtin for gettext; always returning unicode objects
	# also install ngettext()
	gettext.install(package_name, localedir=localedir, unicode=True,
			names=("ngettext",))
	# For gtk.Builder, we need to call the C library gettext functions
	# As well as set the codeset to avoid locale-dependent translation
	# of the message catalog
	locale.bindtextdomain(package_name, localedir)
	locale.bind_textdomain_codeset(package_name, "UTF-8")
	# to load in current locale properly for sorting etc
	try:
		locale.setlocale(locale.LC_ALL, "")
	except locale.Error, e:
		pass

setup_locale_and_gettext()

def get_options():
	"""Return a list of other application flags with --* prefix included."""

	program_options = [
		("no-splash", _("do not present main interface on launch")),
		("list-plugins", _("list available plugins")),
		("debug", _("enable debug info")),
	]
	misc_options = [
		("help", _("show usage help")),
		("version", _("show version information")),
	]

	import getopt
	def make_help_text():
		from kupfer import config

		config_filename = "kupfer.cfg"
		defaults_filename = "defaults.cfg"
		conf_path = config.save_config_file(config_filename)
		defaults_path = config.get_data_file(defaults_filename)
		usage_string = _("Usage: kupfer [OPTIONS | QUERY]")
		def format_options(opts):
			return "\n".join("  --%-15s  %s" % (o,h) for o,h in opts)

		options_string = u"%s\n\n%s\n\n%s" % (usage_string,
				format_options(program_options), format_options(misc_options))

		configure_help1 = _("To configure kupfer, edit:")
		configure_help2 = _("The default config for reference is at:")
		help_text = "\n".join((
			options_string,
			"\n",
			configure_help1,
			"\t%s" % conf_path,
			configure_help2,
			"\t%s" % defaults_path,
			"\n",
		))
		return help_text

	def make_plugin_list():
		from kupfer.core import plugins
		plugin_header = _("Available plugins:")
		plugin_list = plugins.get_plugin_desc()
		return "\n".join((plugin_header, plugin_list))

	# Fix sys.argv that can be None in exceptional cases
	if sys.argv[0] is None:
		sys.argv[0] = "kupfer"

	try:
		opts, args = getopt.getopt(sys.argv[1:], "",
				[o for o,h in program_options] +
				[o for o,h in misc_options])
	except getopt.GetoptError, info:
		print info
		print make_help_text()
		raise SystemExit

	for k, v in opts:
		if k == "--list-plugins":
			print make_plugin_list()
			raise SystemExit
		if k == "--help":
			print make_help_text()
			raise SystemExit
		if k == "--version":
			print_version()
			print
			print_banner()
			raise SystemExit
		if k == "--debug":
			global _debug
			_debug = True

	# return list first of tuple pair
	return [tupl[0] for tupl in opts]

def print_version():
	from kupfer import version
	print version.PACKAGE_NAME, version.VERSION

def print_banner():
	from kupfer import version

	banner = _(
		"%(PROGRAM_NAME)s: %(SHORT_DESCRIPTION)s\n"
		"	%(COPYRIGHT)s\n"
		"	%(WEBSITE)s\n") % vars(version)

	# Be careful about unicode here, since it might stop the whole program
	try:
		print banner
	except UnicodeEncodeError, e:
		print banner.encode("ascii", "replace")

def _set_process_title_linux():
	try:
		import ctypes
	except ImportError:
		return
	try:
		libc = ctypes.CDLL("libc.so.6")
		libc.prctl(15, "kupfer")
	except (AttributeError, OSError):
		pass

def main():
	# parse commandline before importing UI
	cli_opts = get_options()
	print_banner()

	from kupfer.ui import browser
	from kupfer import pretty

	if _debug:
		pretty.debug = _debug
		try:
			import debug
			debug.install()
		except ImportError, e:
			pass
	sys.excepthook = sys.__excepthook__
	_set_process_title_linux()

	w = browser.WindowController()

	quiet = ("--no-splash" in cli_opts)
	w.main(quiet=quiet)

