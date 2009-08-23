import gettext
import locale

_debug = False

def setup_locale_and_gettext():
	"""Set up localization with gettext"""
	package_name = "kupfer"
	localedir = "./locale"
	try:
		from . import version_subst
	except ImportError:
		pass
	else:
		package_name = version_subst.PACKAGE_NAME
		localedir = version_subst.LOCALEDIR
	# Install _() builtin for gettext; always returning unicode objects
	# also install ngettext()
	gettext.install(package_name, localedir=localedir, unicode=True,
			names=("ngettext",))
	# also bind this for gtkbuilder (wtf?)
	locale.bindtextdomain(package_name, localedir)
	# to load in current locale properly for sorting etc
	try:
		locale.setlocale(locale.LC_ALL)
	except locale.Error, e:
		print type(e), e

setup_locale_and_gettext()

def get_options(default_opts=""):
	"""
	Read cli options and process --usage, --version and --debug
	return a list of other application flags with --* prefix included
	"""
	usage_string = _("Usage:")

	program_options = [
		("no-splash", _("do not present main interface on launch")),
	]
	misc_options = [
		("help", _("show usage help")),
		("version", _("show version information")),
		("debug", _("enable debug info")),
	]

	usage_string = usage_string + "\n" + "\n".join("  --%-15s  %s" % (o,h) for o,h in (program_options + misc_options))

	configure_help1 = _("To configure kupfer, edit:")
	configure_help2 = _("The default config for reference is at:")
	plugin_header = _("Available plugins:")

	from getopt import getopt, GetoptError
	from sys import argv

	from kupfer import config, plugins

	config_filename = "kupfer.cfg"
	defaults_filename = "defaults.cfg"
	conf_path = config.save_config_file(config_filename)
	defaults_path = config.get_data_file(defaults_filename)

	def make_usage_text():
		plugin_list = plugins.get_plugin_desc()
		usage_text = "\n".join((
			usage_string,
			"\n",
			configure_help1,
			"\t%s" % conf_path,
			configure_help2,
			"\t%s" % defaults_path,
			"\n",
			plugin_header,
			plugin_list,
		))
		return usage_text

	try:
		opts, args = getopt(argv[1:], "", [o for o,h in program_options] + 
				[o for o,h in misc_options])
	except GetoptError, info:
		print info
		print make_usage_text()
		raise SystemExit

	for k, v in opts:
		if k == "--help":
			print make_usage_text()
			raise SystemExit
		if k == "--version":
			print_version()
			print
			print_banner()
			raise SystemExit
		if k == "--debug":
			try:
				import debug
			except ImportError, e:
				pass
			global _debug
			_debug = True

	# return list first of tuple pair
	return [tupl[0] for tupl in opts]

def print_version():
	from . import version
	print version.PACKAGE_NAME, version.VERSION

def print_banner():
	from . import version
	var = {
		"program": version.PROGRAM_NAME, "desc": version.SHORT_DESCRIPTION,
		"website": version.WEBSITE, "copyright": version.COPYRIGHT
	}
	banner = _(
		"%(program)s: %(desc)s\n"
		"	%(copyright)s\n"
		"	%(website)s\n") % var

	# Be careful about unicode here, since it might stop the whole program
	try:
		print banner
	except UnicodeEncodeError, e:
		print banner.encode("ascii", "replace")

def main():
	# parse commandline before importing UI
	cli_opts = get_options()
	print_banner()

	from . import browser, pretty

	if _debug:
		pretty.debug = _debug

	w = browser.WindowController()

	quiet = ("--no-splash" in cli_opts)
	w.main(quiet=quiet)

