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
    _dialog: _AboutDialog | None = None

    @classmethod
    def get(cls) -> _AboutDialog:
        if cls._dialog is None:
            cls._dialog = cls._create()

        assert cls._dialog
        return cls._dialog

    @classmethod
    def _create(cls):
        abdlg = Gtk.AboutDialog()
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

        abdlg.connect("response", cls._response_callback)
        abdlg.connect("delete-event", cls._close_callback)

        return abdlg

    @staticmethod
    def _response_callback(dialog: Gtk.Dialog, response_id: ty.Any) -> None:
        dialog.hide()

    @classmethod
    def _close_callback(cls, *_args):
        cls._dialog = None
        return True


def show_about_dialog(
    ctxenv: ty.Optional[GUIEnvironmentContext] = None,
) -> None:
    """
    create an about dialog and show it
    """
    dlg = _AboutDialog.get()
    if ctxenv:
        ctxenv.present_window(dlg)
    else:
        dlg.present()  # type: ignore
