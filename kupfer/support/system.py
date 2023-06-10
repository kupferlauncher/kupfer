#! /usr/bin/env python3
# Distributed under terms of the GPLv3 license.

"""
System related functions
"""

import os.path
import socket
import sys

from kupfer.support import pretty, datatools


@datatools.evaluate_once
def get_hostname() -> str:
    """Get cached host name"""
    try:
        return socket.gethostname()
    except Exception:
        pretty.print_exc(__name__)

    return ""


@datatools.evaluate_once
def get_homedir() -> str:
    return os.path.expanduser("~")


@datatools.evaluate_once
def get_application_filename() -> str:
    return os.path.basename(sys.argv[0])
