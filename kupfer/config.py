"""
Module for confiugration and misc things
"""

import xdg.BaseDirectory as base
import os

PACKAGE_NAME="kupfer"

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

def get_data_file(filename):
	"""
	Return path to @filename if it exists
	anywhere in the data paths, else return None
	"""
	for direc in base.load_data_paths(PACKAGE_NAME):
		file_path = os.path.join(direc, filename)
		if os.path.exists(file_path):
			return file_path
	return None

def get_data_home():
	"""
	Directory where data is to be saved
	Guaranteed to exist
	"""
	return base.save_data_path(PACKAGE_NAME)

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
