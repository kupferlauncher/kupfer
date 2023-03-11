"""
Support object/functions that are independent from other parts of Kupfer.
"""

from __future__ import annotations

from . import desktop_parse


def argv_for_commandline(cli: str) -> list[str]:
    return desktop_parse.parse_argv(cli)
