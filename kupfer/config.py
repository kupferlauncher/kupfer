"""
Module for confiugration and misc things
"""

import xdg.BaseDirectory as base
import os

PACKAGE_NAME="kupfer"

class ResourceLookupError (StandardError):
	pass

def has_capability(cap):
	return not bool(os.getenv("KUPFER_NO_%s" % cap, False))

def get_cache_home():
	"""
	Directory where cache files should be put
	Guaranteed to exist
	"""
	cache_home = base.xdg_cache_home or os.path.expanduser("~/.cache")
	cache_dir = os.path.join(cache_home, PACKAGE_NAME)
	if not os.path.exists(cache_dir):
		try:
			os.makedirs(cache_dir, mode=0700)
		except OSError, e:
			print e
			return None
	return cache_dir

def get_cache_file(path=()):
	cache_home = base.xdg_cache_home or os.path.expanduser("~/.cache")
	cache_dir = os.path.join(cache_home, *path)
	if not os.path.exists(cache_dir):
		return None
	return cache_dir

def get_data_file(filename, package=PACKAGE_NAME):
	"""
	Return path to @filename if it exists
	anywhere in the data paths, else raise ResourceLookupError.
	"""
	data_paths = []
	try:
		from . import version_subst
	except ImportError:
		first_datadir = "./data"
	else:
		first_datadir = os.path.join(version_subst.DATADIR, package)

	data_paths.append(first_datadir)
	for data_path in base.load_data_paths(package):
		if not data_path in data_paths:
			data_paths.append(data_path)

	for direc in data_paths:
		file_path = os.path.join(direc, filename)
		if os.path.exists(file_path):
			return file_path
	if package == PACKAGE_NAME:
		raise ResourceLookupError("Resource %s not found" % filename)
	else:
		raise ResourceLookupError("Resource %s in package %s not found" %
			(filename, package))

def save_data_file(filename):
	"""
	Return filename in the XDG data home directory, where the
	directory is guaranteed to exist
	"""
	direc = base.save_data_path(PACKAGE_NAME)
	if not direc:
		return None
	filepath = os.path.join(direc, filename)
	return filepath

def get_data_home():
	"""
	Directory where data is to be saved
	Guaranteed to exist
	"""
	return base.save_data_path(PACKAGE_NAME)

def get_data_dirs(name="", package=PACKAGE_NAME):
	"""
	Iterate over all data dirs of @name that exist
	"""
	return base.load_data_paths(os.path.join(package, name))

def get_config_file(filename, package=PACKAGE_NAME):
	"""
	Return path to @package/@filename if it exists anywhere in the config
	paths, else return None
	"""
	return base.load_first_config(package, filename)

def get_config_files(filename):
	"""
	Iterator to @filename in all
	config paths, with most important (takes precendence)
	files first
	"""
	return base.load_config_paths(PACKAGE_NAME, filename) or ()

def save_config_file(filename):
	"""
	Return filename in the XDG data home directory, where the
	directory is guaranteed to exist
	"""
	direc = base.save_config_path(PACKAGE_NAME)
	if not direc:
		return None
	filepath = os.path.join(direc, filename)
	return filepath

def get_config_paths():
	'''Return iterator to config paths'''
	return base.load_config_paths(PACKAGE_NAME)

def get_plugin_data_file(plugin_name, filename):
	'''Return path to @filename data file for @plugin_name.
	File can be stored in plugin dir or in 'data' subdir in plugin dir.
	'''
	from kupfer import plugin
	base_plugin_path = plugin.__path__[0]
	plugin_id = plugin_name.split('.')[-1]
	plugin_path = os.path.join(base_plugin_path, plugin_id)
	data_file = os.path.join(plugin_path, filename)
	if os.path.isfile(data_file):
		return data_file
	data_file = os.path.join(plugin_path, 'data', filename)
	if os.path.isfile(data_file):
		return data_file
	return None
