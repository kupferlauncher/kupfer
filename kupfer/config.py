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
		os.makedirs(cache_dir, mode=0700)
	return cache_dir
