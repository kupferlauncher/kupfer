"""
Module for configuration and misc things
"""

from __future__ import annotations

import os
import typing as ty
from pathlib import Path

from xdg import BaseDirectory

try:
    from kupfer import version_subst  # type:ignore
except ImportError:
    version_subst = None

PACKAGE_NAME = "kupfer"

__all__ = (
    "ResourceLookupError",
    "get_cache_file",
    "get_cache_home",
    "get_config_file",
    "get_config_files",
    "get_data_dirs",
    "get_data_file",
    "get_data_home",
    "get_kupfer_env",
    "has_capability",
    "save_config_file",
    "save_data_file",
)


class ResourceLookupError(Exception):
    pass


def has_capability(cap: str) -> bool:
    """Check is @cap capability is not disabled by environment variable"""
    return not bool(os.getenv(f"KUPFER_NO_{cap}"))


def get_kupfer_env(name: str, default: str = "") -> str:
    """Get valaue of KUPFER_<name> environment variable or default"""
    return os.getenv(f"KUPFER_{name}", default)


def get_cache_home() -> str | None:
    """Directory where cache files should be put.  Guaranteed to exist."""
    cache_home = BaseDirectory.xdg_cache_home or os.path.expanduser("~/.cache")
    cache_dir = Path(cache_home, PACKAGE_NAME)
    if not cache_dir.exists():
        try:
            cache_dir.mkdir(mode=0o700)
        except OSError as exc:
            print(exc)
            return None

    return str(cache_dir)


def get_cache_file(path: tuple[str, ...] = ()) -> str | None:
    """Get file by @path from cache directory.  Return None when no exists."""
    cache_home = BaseDirectory.xdg_cache_home or os.path.expanduser("~/.cache")
    cache_path = Path(cache_home, *path)
    if not cache_path.exists():
        return None

    return str(cache_path)


def get_data_file(filename: str, package: str = PACKAGE_NAME) -> str:
    """Return path to @filename if it exists anywhere in the data paths, else
    raise ResourceLookupError."""
    if version_subst:
        first_datadir = os.path.join(version_subst.DATADIR, package)
    else:
        first_datadir = "./data"

    file_path = Path(first_datadir, filename)
    if file_path.exists():
        return str(file_path)

    for data_path in BaseDirectory.load_data_paths(package):
        file_path = Path(data_path, filename)
        if file_path.exists():
            return str(file_path)

    if package == PACKAGE_NAME:
        raise ResourceLookupError(f"Resource {filename} not found")

    raise ResourceLookupError(
        f"Resource {filename} in package {package} not found"
    )


def save_data_file(filename: str) -> str | None:
    """Return filename in the XDG data home directory, where the directory is
    guaranteed to exist."""
    if direc := BaseDirectory.save_data_path(PACKAGE_NAME):
        return os.path.join(direc, filename)

    return None


def get_data_home() -> str:
    """Directory where data is to be saved. Guaranteed to exist."""
    return BaseDirectory.save_data_path(PACKAGE_NAME)  # type: ignore


def get_data_dirs(
    name: str = "", package: str = PACKAGE_NAME
) -> ty.Iterable[str]:
    """Iterate over all data dirs of @name that exist."""
    return ty.cast(
        ty.Iterable[str],
        BaseDirectory.load_data_paths(os.path.join(package, name)),
    )


def get_config_file(filename: str, package: str = PACKAGE_NAME) -> str | None:
    """Return path to @package/@filename if it exists anywhere in the config
    paths, else return None"""
    return ty.cast(
        ty.Union[str, None], BaseDirectory.load_first_config(package, filename)
    )


def get_config_files(filename: str) -> ty.Iterable[str]:
    """Iterator to @filename in all config paths, with most important (takes
    precedence) files first."""
    return BaseDirectory.load_config_paths(PACKAGE_NAME, filename) or ()


def save_config_file(filename: str) -> str | None:
    """Return filename in the XDG data home directory, where the directory
    is guaranteed to exist."""
    if direc := BaseDirectory.save_config_path(PACKAGE_NAME):
        return os.path.join(direc, filename)

    return None
