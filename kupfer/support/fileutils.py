""" File-related support functions.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import itertools
import os
import tempfile
import typing as ty
from os import path as os_path
from pathlib import Path

from kupfer.support import pretty

FilterFunc = ty.Callable[[str], bool]


def get_dirlist(
    folder: str,
    max_depth: int = 0,
    include: FilterFunc | None = None,
    exclude: FilterFunc | None = None,
) -> ty.Iterator[str]:
    """Return a list of absolute paths in folder include, exclude: a function
    returning a boolean

    def include(filename):
        return ShouldInclude
    """

    h_include: FilterFunc = include or (lambda x: True)
    h_exclude: FilterFunc = exclude or (lambda x: False)

    def accept_file(file):
        return h_include(file) and not h_exclude(file)

    for dirname, dirnames, fnames in os.walk(folder):
        # skip deep directories
        depth = len(os.path.relpath(dirname, folder).split(os.path.sep)) - 1
        if depth >= max_depth:
            # this stop processing subfolders
            dirnames.clear()
            continue

        excl_dir = []
        for directory in dirnames:
            if accept_file(directory):
                yield os_path.join(dirname, directory)
            else:
                excl_dir.append(directory)

        yield from (
            os_path.join(dirname, file) for file in fnames if accept_file(file)
        )

        # do not process excluded dirs
        for directory in reversed(excl_dir):
            dirnames.remove(directory)


def is_directory_writable(dpath: str | Path) -> bool:
    """If directory path @dpath is a valid destination to write new files?"""
    if isinstance(dpath, str):
        dpath = Path(dpath)

    if not dpath.is_dir():
        return False

    return os.access(dpath, os.R_OK | os.W_OK | os.X_OK)


def is_file_writable(dpath: str | Path) -> bool:
    """If @dpath is a valid, writable file

    UNUSED
    """
    if isinstance(dpath, str):
        dpath = Path(dpath)

    if not dpath.is_file():
        return False

    return os.access(dpath, os.R_OK | os.W_OK)


def get_destpath_in_directory(
    directory: str, filename: str, extension: str | None = None
) -> str:
    """Find a good destpath for a file named @filename in path @directory
    Try naming the file as filename first, before trying numbered versions
    if the previous already exist.

    If @extension, it is used as the extension. Else the filename is split and
    the last extension is used
    """
    # find a nonexisting destname
    if extension:
        basename = filename + extension
        root, ext = filename, extension
    else:
        basename = filename
        root, ext = os_path.splitext(filename)

    ctr = itertools.count(1)
    destpath = Path(directory, basename)
    while destpath.exists():
        num = next(ctr)
        basename = f"{root}-{num}{ext}"
        destpath = Path(directory, basename)

    return str(destpath)


def get_destfile_in_directory(
    directory: str, filename: str, extension: str | None = None
) -> tuple[ty.BinaryIO | None, str | None]:
    """Find a good destination for a file named @filename in path @directory.

    Like get_destpath_in_directory, but returns an open file object, opened
    atomically to avoid race conditions.

    Return (fileobj, filepath)
    """
    # retry if it fails
    for _retry in range(3):
        destpath = get_destpath_in_directory(directory, filename, extension)
        try:
            fileno = os.open(
                destpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666
            )
        except OSError as exc:
            pretty.print_error(__name__, exc)
        else:
            return (os.fdopen(fileno, "wb"), destpath)

    return (None, None)


def get_destfile(
    destpath: str | Path,
) -> tuple[ty.BinaryIO | None, str | None]:
    """Open file object for full file path. Return the same object
    like get_destfile_in_directory.

    Return (fileobj, filepath).
    """
    # retry if it fails
    for _retry in range(3):
        try:
            fileno = os.open(
                destpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666
            )
        except OSError as exc:
            pretty.print_error(__name__, exc)
        else:
            return (os.fdopen(fileno, "wb"), str(destpath))

    return (None, None)


def get_safe_tempfile() -> tuple[ty.BinaryIO, str]:
    """Return (fileobj, filepath) pointing to an open temporary file"""

    fileno, path = tempfile.mkstemp()
    return (os.fdopen(fileno, "wb"), path)


def lookup_exec_path(exename: str) -> str | None:
    """Return path for @exename in $PATH or None"""
    env_path = os.environ.get("PATH") or os.defpath
    for execdir in env_path.split(os.pathsep):
        exepath = Path(execdir, exename)
        if os.access(exepath, os.R_OK | os.X_OK) and exepath.is_file():
            return str(exepath)

    return None
