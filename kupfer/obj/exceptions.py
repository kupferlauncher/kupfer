"""
Common exceptions definition.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""

import typing as ty

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__all__ = (
    "Error",
    "InvalidDataError",
    "InvalidLeafError",
    "NoDefaultApplicationError",
    "NoMultiError",
    "NotAvailableError",
    "OperationError",
)


class Error(Exception):
    pass


class InvalidDataError(Error):
    """The data is wrong for the given Leaf"""


class OperationError(Error):
    """Command execution experienced an error"""


class InvalidLeafError(OperationError):
    """The Leaf passed to an Action is invalid"""


class NotAvailableError(OperationError):
    """User-visible error message when an external tool is the wrong version."""

    def __init__(self, toolname: str):
        OperationError.__init__(
            self, _("%s does not support this operation") % toolname
        )


class NoMultiError(OperationError):
    def __init__(self):
        OperationError.__init__(
            self, _("Can not be used with multiple objects")
        )


class NoDefaultApplicationError(OperationError):
    pass
