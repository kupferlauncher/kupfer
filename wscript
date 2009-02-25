#! /usr/bin/env python
# encoding: utf-8
# Gustavo Carneiro, 2007

import sys
import Configure

# the following two variables are used by the target "waf dist"
VERSION='0.0.1'
APPNAME="kupfer"

# these variables are mandatory ('/' are converted automatically)
srcdir = '.'
blddir = 'build'

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
	# first compile a few pyc and pyo files
	new_module(bld, "kupfer")
	new_module(bld, "kupfer/extensions")

def shutdown():
	pass


