#! /usr/bin/env python
# encoding: utf-8

import os
import sys
import Configure
import Utils

# the following two variables are used by the target "waf dist"
APPNAME="kupfer"
VERSION = "undefined"

def _get_git_version():
	""" try grab the current version number from git"""
	version = None
	if os.path.exists(".git"):
		try:
			version = os.popen("git describe").read().strip()
		except Exception, e:
			print e
	return version

def _read_git_version():
	"""Read version from git repo, or from GIT_VERSION"""
	version = _get_git_version()
	if not version and os.path.exists("GIT_VERSION"):
		f = open("GIT_VERSION", "r")
		version = f.read().strip()
		f.close()
	if version:
		global VERSION
		VERSION = version

_read_git_version()

VERSION_MAJOR_MINOR = ".".join(VERSION.split(".")[0:2])

# these variables are mandatory ('/' are converted automatically)
srcdir = '.'
blddir = 'build'

def dist_hook():
	"""in the dist preparation dir, delete unwanted files"""
	DIST_GIT_IGNORE = """
		debug.py
		makedist.sh
		""".split()

	for ignfile in filter(os.path.exists, DIST_GIT_IGNORE):
		os.unlink(ignfile)

def dist():
	"""Make the dist tarball and print its SHA-1 """
	def write_git_version():
		""" Write the revision to a file called GIT_VERSION,
		to grab the current version number from git when
		generating the dist tarball."""
		version = _get_git_version()
		if not version:
			return False
		version_file = open("GIT_VERSION", "w")
		version_file.write(version + "\n")
		version_file.close()
		return True

	import Scripting
	write_git_version()
	Scripting.g_gz = "gz"
	Scripting.dist(APPNAME, VERSION)

def set_options(opt):
	# options for disabling pyc or pyo compilation
	opt.tool_options("python")
	opt.tool_options("misc")
	opt.tool_options("gnu_dirs")
	opt.add_option('--nopyo',action='store_false',default=False,help='Do not install optimised compiled .pyo files [This is the default for Kupfer]',dest='pyo')
	opt.add_option('--pyo',action='store_true',default=False,help='Install optimised compiled .pyo files [Default:not install]',dest='pyo')
	opt.sub_options("extras")

def configure(conf):
	conf.check_tool("python")
	conf.check_python_version((2,5,0))
	conf.check_tool("misc gnu_dirs")

	# BUG: intltool requires gcc
	conf.check_tool("gcc intltool")

	python_modules = """
		gio
		gtk
		xdg
		dbus
		"""
	for module in python_modules.split():
		conf.check_python_module(module)

	Utils.pprint("NORMAL", "Checking optional dependencies:")

	opt_programs = {
			"dbus-send": "Focus kupfer from the command line",
			"rst2man": "Generate and install man page",
		}
	opt_pymodules = {
			"wnck": "Identify and focus running applications",
			"gnome": ("Log out cleanly with session managers *OTHER* than "
				"gnome-session >= 2.24"),
		}

	for prog in opt_programs:
		prog_path = conf.find_program(prog, var=prog.replace("-", "_").upper())
		if not prog_path:
			Utils.pprint("YELLOW", "Optional, allows: %s" % opt_programs[prog])

	try:
		conf.check_python_module("keybinder")
	except Configure.ConfigurationError, e:
		Utils.pprint("RED", "Python module keybinder is recommended")
		Utils.pprint("RED", "Please see README")
		
	for mod in opt_pymodules:
		try:
			conf.check_python_module(mod)
		except Configure.ConfigurationError, e:
			Utils.pprint("YELLOW", "module %s is recommended, allows %s" % (
				mod, opt_pymodules[mod]))

	conf.env["KUPFER"] = Utils.subst_vars("${BINDIR}/kupfer", conf.env)
	conf.env["VERSION"] = VERSION

	# Check sys.path
	Utils.pprint("NORMAL", "Installing python modules into: %(PYTHONDIR)s" % conf.env)
	pipe = os.popen("""%(PYTHON)s -c "import sys; print '%(PYTHONDIR)s' in sys.path" """ % conf.env)
	if "False" in pipe.read():
		Utils.pprint("YELLOW", "Please add %(PYTHONDIR)s to your sys.path!" % conf.env)
	conf.sub_config("extras")

def new_module(bld, name, sources=None):
	if not sources: sources = name
	obj = bld.new_task_gen("py")
	obj.find_sources_in_dirs(sources)
	obj.install_path = "${PYTHONDIR}/%s" % name
	return obj

def build(bld):
	# kupfer module version info file
	version_subst_file = "kupfer/version_subst.py"
	obj = bld.new_task_gen("subst",
		source=version_subst_file + ".in",
		target=version_subst_file,
		install_path="${PYTHONDIR}/kupfer",
		dict = bld.env,
		)

	# modules
	new_module(bld, "kupfer")
	new_module(bld, "kupfer/plugin")

	# binary
	# Subst in the python version
	# We have to put this in an intermediate build directory,
	# inside data/ not to clash with the 'kupfer' module(!)
	binary_subst_file = "kupfer-activate.sh"
	bin = bld.new_task_gen("subst",
		source = binary_subst_file,
		target = "data/kupfer",
		install_path = "${BINDIR}",
		chmod = 0755,
		dict = {"PYTHON": bld.env["PYTHON"]}
		)
	# Documentation
	if bld.env["RST2MAN"]:
		# generate man page from Quickstart.rst
		bld.new_task_gen(
			source = "Documentation/Quickstart.rst",
			target = "kupfer.1",
			rule = 'rst2man ${SRC} > ${TGT}',
		)
		bld.add_group()
		# compress and install man page
		bld.new_task_gen(
			source = "kupfer.1",
			target = "kupfer.1.gz",
			rule = 'gzip -c ${SRC} > ${TGT}',
			install_path = "${MANDIR}/man1",
		)

	bld.add_subdirs("po data extras")

def intlupdate(util):
	"""Extract new strings for localization"""
	os.chdir("po")
	for line in open("LINGUAS"):
		""" Run xgettext for all listed languages
		to extract translatable strings and merge with
		the old file """
		if line.startswith("#"):
			continue
		lang = line.strip()

		lang_file = "%s.po" % lang
		if not os.path.exists(lang_file):
			print "Creating %s" % lang_file
			os.popen("xgettext -D .. -f POTFILES.in --output=%s -F" % lang_file)
			os.popen("intltool-update %s" % lang)
		else:
			print "Processing", lang
			os.popen("intltool-update %s" % lang)
			os.popen("msgfmt --check %s" % lang_file)

def test(bld):
	# find all files with doctests
	python = os.getenv("PYTHON", "python")
	paths = os.popen("git grep -l 'doctest.testmod()' kupfer/").read().split()
	all_success = True
	verbose = ("-v" in sys.argv)
	for p in paths:
		print p
		cmd = [python, p]
		if verbose:
			cmd.append("-v")
		sin, souterr = os.popen4(cmd)
		sin.close()
		res = souterr.read()
		souterr.close()
		print (res or "OK")
		all_success = all_success and bool(res)
	return all_success

def shutdown():
	pass


