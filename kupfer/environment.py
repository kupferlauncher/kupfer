
import functools
import os
from kupfer import pretty, config

@functools.lru_cache(maxsize=1)
def is_kwin():
    """ Try to figure out if KWin is the current window manager.  """
    global Wnck

    try:
        from gi.repository import Wnck
    except ImportError:
        pass
    else:
        screen = Wnck.Screen.get_default()
        if screen is not None:
            wm = screen.get_window_manager_name()
            pretty.print_debug(__name__, "window manager is", wm)
            if wm:
                return wm.lower() == "kwin"
    return _desktop_environment_guess().lower() == "kde"

def _desktop_environment_guess():
    ret = os.getenv("XDG_CURRENT_DESKTOP") or ""
    pretty.print_debug(__name__, "desktop environment is", ret)
    return ret

def is_wayland():
    return bool(os.getenv("WAYLAND_DISPLAY"))

def allows_keybinder():
    return config.has_capability("KEYBINDER") and not is_wayland()
