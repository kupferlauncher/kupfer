#! /usr/bin/env python3
"""
Helper functions - common code for core module.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import typing as ty

from kupfer.obj import Leaf


def get_leaf_members(leaf: Leaf) -> ty.Iterable[Leaf]:
    """Return an iterator to members of @leaf, if it is a multiple leaf."""

    if hasattr(leaf, "get_multiple_leaf_representation"):
        return leaf.get_multiple_leaf_representation()  # type: ignore

    return (leaf,)


def is_multiple_leaf(leaf: Leaf | None) -> bool:
    """Check is leaf represent multiple leaves."""
    return hasattr(leaf, "get_multiple_leaf_representation")
