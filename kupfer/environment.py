from __future__ import annotations

import os

try:
    from gi.repository import Wnck
except ImportError:
    Wnck = None

from kupfer import config
from kupfer.support import pretty, datatools

__all__ = ("is_kwin", "is_wayland", "allows_keybinder")


@datatools.evaluate_once
def is_kwin() -> bool:
    """Try to figure out if KWin is the current window manager.
    If Wnck unavailable try guess from environment variables.
    """
    if Wnck and (screen := Wnck.Screen.get_default()) is not None:
        winmgr: str | None = screen.get_window_manager_name()
        pretty.print_debug(__name__, "window manager is", winmgr)
        if winmgr:
            return winmgr.lower() == "kwin"

    return _desktop_environment_guess().lower() == "kde"


def _desktop_environment_guess() -> str:
    ret = os.getenv("XDG_CURRENT_DESKTOP") or ""
    pretty.print_debug(__name__, "desktop environment is", ret)
    return ret


def is_wayland() -> bool:
    """Check is Wayland is current graphics environment"""
    return bool(os.getenv("WAYLAND_DISPLAY"))


def allows_keybinder() -> bool:
    """Check is keybinder available."""
    return config.has_capability("KEYBINDER") and not is_wayland()
