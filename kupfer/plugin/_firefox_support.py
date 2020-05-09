"""Firefox common functions."""

import os
from configparser import RawConfigParser

from kupfer import pretty


def make_absolute_and_check(firefox_dir, path):
    """Helper, make path absolute and check is exist."""
    if not path.startswith("/"):
        path = os.path.join(firefox_dir, path)

    if os.path.isdir(path):
        return path

    return None


def _find_default_profile(firefox_dir):
    """Try to find default/useful profile in firefox located in `firefox_dir`
    """
    config = RawConfigParser({"Default" : 0})
    config.read(os.path.join(firefox_dir, "profiles.ini"))
    path = None

    # find Instal.* section and default profile
    for section in config.sections():
        if section.startswith("Install"):
            if not config.has_option(section, "Default"):
                continue

            # found default profile
            path = make_absolute_and_check(firefox_dir,
                                           config.get(section, "Default"))
            if path:
                pretty.print_debug(__name__, "found install default profile",
                                   path)
                return path

            break

    pretty.print_debug("Install* default profile not found")

    # not found default profile, iterate profiles, try to find default
    for section in config.sections():
        if not section.startswith("Profile"):
            continue

        if config.has_option(section, "Default") and \
                config.get(section, "Default") == "1":
            path = make_absolute_and_check(firefox_dir,
                                           config.get(section, "Path"))
            if path:
                pretty.print_debug(__name__, "Found profile with default=1",
                                   section, path)
                break

        if not path and config.has_option(section, "Path"):
            path = make_absolute_and_check(firefox_dir,
                                           config.get(section, "Path"))

    return path


def get_firefox_home_file(needed_file, profile_dir=None):
    """Get path to `needed_file` in `profile_dir`.

        When no `profile_dir` is not given try to find default profile
        in profiles.ini. `profile_dir` may be only profile name and is relative
        to ~/.mozilla/firefox or may be full path to profile dir.
    """
    if profile_dir:
        profile_dir = os.path.expanduser(profile_dir)
        if not os.path.isabs(profile_dir):
            profile_dir = os.path.join(
                os.path.expanduser("~/.mozilla/firefox"), profile_dir)

        if not os.path.isdir(profile_dir):
            pretty.print_debug(__name__,
                               "Firefox custom profile_dir not exists",
                               profile_dir)
            return None

        return os.path.join(profile_dir, needed_file)

    firefox_dir = os.path.expanduser("~/.mozilla/firefox")
    if not os.path.exists(firefox_dir):
        pretty.print_debug(__name__, "Firefox dir not exists", firefox_dir)
        return None

    if not os.path.isfile(os.path.join(firefox_dir, "profiles.ini")):
        pretty.print_debug(__name__, "Firefox profiles.ini not exists",
                           firefox_dir)
        return None

    pretty.print_debug(__name__, "Firefox dir", firefox_dir)

    path = _find_default_profile(firefox_dir)
    pretty.print_debug(__name__, "Profile path", path)

    return os.path.join(path, needed_file) if path else None
