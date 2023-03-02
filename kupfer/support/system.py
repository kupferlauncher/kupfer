#! /usr/bin/env python3
# Distributed under terms of the GPLv3 license.

"""
System related functions
"""

import socket
import functools

from . import pretty


@functools.cache
def get_hostname() -> str:
    """Get cached host name"""
    try:
        return socket.gethostname()
    except Exception:
        pretty.print_exc(__name__)

    return ""
