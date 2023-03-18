#! /usr/bin/env python3
# Distributed under terms of the GPLv3 license.

"""
System related functions
"""

import functools
import os.path
import socket
import sys

from . import pretty


@functools.cache
def get_hostname() -> str:
    """Get cached host name"""
    try:
        return socket.gethostname()
    except Exception:
        pretty.print_exc(__name__)

    return ""


@functools.cache
def get_homedir() -> str:
    return os.path.expanduser("~")


@functools.cache
def get_application_filename() -> str:
    return os.path.basename(sys.argv[0])
