#! /usr/bin/env python3

"""
Show application help.
"""
from __future__ import annotations

from kupfer import launch, version
from kupfer.ui.uievents import GUIEnvironmentContext


def show_help(ctxenv: GUIEnvironmentContext | None = None) -> None:
    """
    Show Kupfer help pages, if possible
    """
    if not launch.show_help_url(f"help:{version.PACKAGE_NAME}"):
        launch.show_url(version.HELP_WEBSITE)
