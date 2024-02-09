"""Firefox common functions."""

from __future__ import annotations

from configparser import RawConfigParser
from pathlib import Path
from contextlib import closing, suppress
import itertools
import sqlite3
import typing as ty
import time

from kupfer.support import pretty
from kupfer.obj import UrlLeaf

MAX_ITEMS = 10000
_BOOKMARKS_SQL = """
SELECT moz_places.url, moz_bookmarks.title
FROM moz_places, moz_bookmarks
WHERE moz_places.id = moz_bookmarks.fk
    AND moz_bookmarks.keyword_id IS NULL
ORDER BY visit_count DESC
LIMIT ?"""


def make_absolute_and_check(firefox_dir: Path, path: str) -> Path | None:
    """Helper, make path absolute and check is exist."""
    dpath = firefox_dir.joinpath(path)

    if dpath.is_dir():
        return dpath

    return None


def _find_default_profile(firefox_dir: Path) -> Path | None:
    """Try to find default/useful profile in firefox located in `firefox_dir`"""
    config = RawConfigParser({"Default": "0"})
    config.read(firefox_dir.joinpath("profiles.ini"))
    path = None

    # find Instal.* section and default profile
    for section in config.sections():
        if section.startswith("Install"):
            if not config.has_option(section, "Default"):
                continue

            # found default profile
            if path := make_absolute_and_check(
                firefox_dir, config.get(section, "Default")
            ):
                pretty.print_debug(
                    __name__, "Found install default profile", path
                )
                return path

            break

    pretty.print_debug(__name__, "Install* default profile not found")

    # not found default profile, iterate profiles, try to find default
    for section in config.sections():
        if not section.startswith("Profile"):
            continue

        if (
            config.has_option(section, "Default")
            and config.get(section, "Default") == "1"
        ):
            if path := make_absolute_and_check(
                firefox_dir, config.get(section, "Path")
            ):
                pretty.print_debug(
                    __name__, "Found profile with default=1", section, path
                )
                return path

        # if section has path - remember it and use if default is not found
        if not path and config.has_option(section, "Path"):
            path = make_absolute_and_check(
                firefox_dir, config.get(section, "Path")
            )

    # not found default profile, return any found path (if any)
    return path


def _get_home_file(
    needed_file: str,
    profile_dir: str | Path | None,
    firefox_dir: Path,
) -> Path | None:
    """Get path to `needed_file` in `profile_dir`.

    When no `profile_dir` is not given try to find default profile
    in profiles.ini. `profile_dir` may be only profile name and is relative
    to ~/.mozilla/firefox or may be full path to profile dir.
    """
    if profile_dir:
        # user define profile name or dir, check it and if valid use id
        with suppress(RuntimeError, IOError):
            profile_dir = Path(profile_dir).expanduser()
            if not profile_dir.is_absolute():
                profile_dir = firefox_dir.joinpath(profile_dir)

            if not profile_dir.is_dir():
                # fail; given profile not exists
                pretty.print_debug(
                    __name__, "Firefox custom profile_dir not exists", profile_dir
                )
                return None

            return profile_dir.joinpath(needed_file)

    if not firefox_dir.exists():
        pretty.print_debug(__name__, "Firefox dir not exists", firefox_dir)
        return None

    if not firefox_dir.joinpath("profiles.ini").is_file():
        pretty.print_debug(
            __name__, "Firefox profiles.ini not exists", firefox_dir
        )
        return None

    pretty.print_debug(__name__, "Firefox dir", firefox_dir)

    path = _find_default_profile(firefox_dir)
    pretty.print_debug(__name__, "Profile path", path)

    return path.joinpath(needed_file) if path else None


def get_firefox_home_file(
    needed_file: str, profile_dir: str | Path | None = None
) -> Path | None:
    """Get path to `needed_file` in `profile_dir`.

    When no `profile_dir` is not given try to find default profile
    in profiles.ini. `profile_dir` may be only profile name and is relative
    to ~/.mozilla/firefox or may be full path to profile dir.
    """
    firefox_dir = Path("~/.mozilla/firefox").expanduser()
    return _get_home_file(needed_file, profile_dir, firefox_dir)


def get_librewolf_home_file(
    needed_file: str, profile_dir: str | Path | None = None
) -> Path | None:
    """Get path to `needed_file` in `profile_dir`.

    When no `profile_dir` is not given try to find default profile
    in profiles.ini. `profile_dir` may be only profile name and is relative
    to ~/.librewolf or may be full path to profile dir.
    """
    firefox_dir = Path("~/.librewolf").expanduser()
    return _get_home_file(needed_file, profile_dir, firefox_dir)


def query_database(
    db_file_path: Path | str, sql: str, args: tuple[ty.Any, ...] = ()
) -> ty.Iterable[tuple[ty.Any, ...]]:
    """Query firefox database. Iterator must be exhausted to prevent hanging
    connection."""

    fpath = str(db_file_path).replace("?", "%3f").replace("#", "%23")
    fpath = "file:" + fpath + "?immutable=1&mode=ro"

    for _ in range(2):
        try:
            pretty.print_debug(__name__, "Query Firefox db", db_file_path, sql)
            with closing(sqlite3.connect(fpath, uri=True, timeout=1)) as conn:
                cur = conn.cursor()
                cur.execute(sql, args)
                yield from cur
                return

        except sqlite3.Error as err:
            # Something is wrong with the database
            # wait short time and try again
            pretty.print_error(__name__, "Query Firefox db error:", str(err))
            time.sleep(1)


def get_bookmarks(
    path: Path | None, max_items: int = MAX_ITEMS
) -> list[UrlLeaf]:
    """Load bookmarks from given `path` database."""

    if not path:
        return []

    return list(
        itertools.starmap(
            UrlLeaf,
            query_database(path, _BOOKMARKS_SQL, (max_items,)),
        )
    )
