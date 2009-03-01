#! /usr/bin/env python
# encoding: utf-8

import os
import sys
import Configure

# the following two variables are used by the target "waf dist"
APPNAME="kupfer"
VERSION = "undefined"

def get_git_version():
	""" try grab the current version number from git"""
	version = None
	if os.path.exists(".git"):
		try:
			version = os.popen("git describe").read().strip()
		except Exception, e:
			print e
	return version

def read_git_version():
	"""Read version from git repo, or from GIT_VERSION"""
	version = get_git_version()
	if not version and os.path.exists("GIT_VERSION"):
		f = open("GIT_VERSION", "r")
		version = f.read().strip()
		f.close()
	if version:
		global VERSION
		VERSION = version

read_git_version()

VERSION_MAJOR_MINOR = ".".join(VERSION.split(".")[0:2])

# these variables are mandatory ('/' are converted automatically)
srcdir = '.'
blddir = 'build'

def dist():
	"""
	Make the dist tarball
	and print its sha1sum
	"""
	def write_git_version():
		""" Write the revision to a file called GIT_VERSION,
		to grab the current version number from git when
		generating the dist tarball."""
		version = get_git_version()
		if not version:
			return False
		version_file = open("GIT_VERSION", "w")
		version_file.write(version + "\n")
		version_file.close()
		return True

	import Scripting
	write_git_version()
	Scripting.g_gz = "gz"
	filename = Scripting.dist(APPNAME, VERSION)
	os.spawnlp(os.P_WAIT, "sha1sum", "sha1sum", filename)

def set_options(opt):
	# options for disabling pyc or pyo compilation
	opt.tool_options("python")

def configure(conf):
	conf.check_tool('python')
	conf.check_python_version((2,4,2))

	python_modules = """
		gio
		gtk
		gnomedesktop
		wnck
		xdg
		"""
	for module in python_modules.split():
		conf.check_python_module(module)

	# no "optimized" bytecode
	conf.env["PYO"] = 0
	print "Using PYTHONDIR: %s" % conf.env["PYTHONDIR"]

def new_module(bld, name, sources=None):
	if not sources: sources = name
	obj = bld.new_task_gen("py")
	obj.find_sources_in_dirs(sources)
	obj.install_path = "${PYTHONDIR}/%s" % name
	return obj

def build(bld):
	# modules
	new_module(bld, "kupfer")
	new_module(bld, "kupfer/extensions")
	# binaries
	bld.install_as("${PREFIX}/bin/kupfer", "main.py", chmod=0755)
	bld.install_as("${PREFIX}/bin/kupfer-activate", "kupfer-activate.sh", chmod=0755)

def shutdown():
	pass


