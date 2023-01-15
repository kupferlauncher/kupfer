from __future__ import annotations

from gi.repository import Gtk

from kupfer import config, version
from kupfer.support import kupferstring


class CredentialsDialogController:
    def __init__(
        self,
        username: str | None,
        password: str | None,
        infotext: str | None = None,
    ):
        """Load ui from data file"""
        builder = Gtk.Builder()
        builder.set_translation_domain(version.PACKAGE_NAME)
        ui_file = config.get_data_file("credentials_dialog.ui")
        builder.add_from_file(ui_file)
        builder.connect_signals(self)  # pylint: disable=no-member

        self.window = builder.get_object("credentials_dialog")
        self.entry_user = builder.get_object("entry_username")
        self.entry_pass = builder.get_object("entry_password")
        if infotext:
            hbox_information = builder.get_object("hbox_information")
            label_information = builder.get_object("label_information")
            label_information.set_text(infotext)
            hbox_information.show()

        self.entry_user.set_text(username or "")
        self.entry_pass.set_text(password or "")

    def on_button_ok_clicked(self, widget: Gtk.Widget) -> None:
        self.window.response(Gtk.ResponseType.ACCEPT)
        self.window.hide()

    def on_button_cancel_clicked(self, widget: Gtk.Widget) -> None:
        self.window.response(Gtk.ResponseType.CANCEL)
        self.window.hide()

    def show(self) -> bool:
        return self.window.run()  # type: ignore

    @property
    def username(self) -> str:
        return kupferstring.tounicode(self.entry_user.get_text())  # type:ignore

    @property
    def password(self) -> str:
        return kupferstring.tounicode(self.entry_pass.get_text())  # type:ignore


def ask_user_credentials(
    user: str | None = None,
    password: str | None = None,
    infotext: str | None = None,
) -> tuple[str, str] | None:
    """Ask user for username and password.

    @user, @password - initial values
    @return:
    (user, password) when user press "change"
    None when user press "cancel" button"""
    dialog = CredentialsDialogController(user, password, infotext)
    result = None
    if dialog.show() == Gtk.ResponseType.ACCEPT:
        result = dialog.username, dialog.password

    return result
