#! /usr/bin/env python3

"""

"""
from __future__ import annotations

from kupfer import utils, version
from kupfer.ui.uievents import GUIEnvironmentContext


def show_help(ctxenv: GUIEnvironmentContext | None = None) -> None:
    """
    Show Kupfer help pages, if possible
    """
    if not utils.show_help_url(f"help:{version.PACKAGE_NAME}"):
        utils.show_url(version.HELP_WEBSITE)
