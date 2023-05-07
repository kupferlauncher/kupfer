#! /usr/bin/env python3

"""
About dialog.
"""
from __future__ import annotations

import typing as ty

from gi.repository import Gtk

from kupfer import version

from .uievents import GUIEnvironmentContext


# pylint: disable=too-few-public-methods
class _AboutDialog:
    _instance: _AboutDialog | None = None

    @classmethod
    def instance(cls) -> _AboutDialog:
        if cls._instance is None:
            cls._instance = _AboutDialog()

        assert cls._instance
        return cls._instance

    def __init__(self):
        self._dlg = abdlg = Gtk.AboutDialog()
        abdlg.set_program_name(version.PROGRAM_NAME)
        abdlg.set_icon_name(version.ICON_NAME)
        abdlg.set_logo_icon_name(version.ICON_NAME)
        abdlg.set_version(version.VERSION)
        abdlg.set_comments(version.SHORT_DESCRIPTION)
        abdlg.set_copyright(version.COPYRIGHT)
        abdlg.set_website(version.WEBSITE)
        abdlg.set_license(version.LICENSE)
        abdlg.set_authors(version.AUTHORS)
        if version.DOCUMENTERS:
            abdlg.set_documenters(version.DOCUMENTERS)

        if version.TRANSLATOR_CREDITS:
            abdlg.set_translator_credits(version.TRANSLATOR_CREDITS)

        if version.ARTISTS:
            abdlg.set_artists(version.ARTISTS)

        abdlg.connect("response", self._response_callback)

    def show(self, ctxenv: ty.Optional[GUIEnvironmentContext] = None) -> None:
        if ctxenv:
            ctxenv.present_window(self._dlg)
        else:
            self._dlg.present()

    def _response_callback(
        self, dialog: Gtk.Dialog, response_id: ty.Any
    ) -> bool:
        dialog.destroy()
        _AboutDialog._instance = None
        return True


def show_about_dialog(
    ctxenv: ty.Optional[GUIEnvironmentContext] = None,
) -> None:
    """Create an about dialog and show it."""
    dlg = _AboutDialog.instance()
    dlg.show()
