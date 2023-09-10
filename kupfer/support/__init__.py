"""
Support object/functions that are independent from other parts of Kupfer.
"""

from __future__ import annotations

from kupfer.support import desktop_parse

__all__ = ("argv_for_commandline",)


def argv_for_commandline(cli: str) -> list[str]:
    return desktop_parse.parse_argv(cli)
