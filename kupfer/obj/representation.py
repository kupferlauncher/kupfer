#! /usr/bin/env python3
"""
Interfaces that may implements objects.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
import typing as ty

__all__ = ("TextRepresentation", "UriListRepresentation")


# pylint: disable=too-few-public-methods
class TextRepresentation:
    """
    Kupfer Objects that implement this interface have a plain text
    representation that can be used for Copy & Paste etc
    """

    def get_text_representation(self) -> str:
        """The default implementation returns the represented object"""
        # pylint: disable=no-member
        return str(self.object)  # type: ignore


# pylint: disable=too-few-public-methods
class UriListRepresentation:
    """
    Kupfer Objects that implement this interface have a uri-list
    representation that can be used for Copy & Paste etc

    get_urilist_representation should return a sequence of bytestring
    URIs.
    """

    def get_urilist_representation(self) -> list[ty.AnyStr]:
        """The default implementation raises notimplementederror"""
        raise NotImplementedError
