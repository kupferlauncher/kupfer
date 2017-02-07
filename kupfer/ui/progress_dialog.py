import functools

import glib
from gi.repository import Gtk

from kupfer import version, config

def idle_call(func):
    @functools.wraps(func)
    def idle_wrapper(*args):
        glib.idle_add(func, *args)
    return idle_wrapper


_HEADER_MARKUP = '<span weight="bold" size="larger">%s</span>'

class ProgressDialogController (object):
    def __init__(self, title, header=None, max_value=100):
        """Create a new progress dialog

        @header: first line of dialog

        The methods show, hide and update are all wrapped to be
        safe to call from any thread.
        """
        self.aborted = False
        self.max_value = float(max_value)
        ui_file = config.get_data_file("progress_dialog.ui")
        self._construct_dialog(ui_file, title, header)

    @idle_call
    def _construct_dialog(self, ui_file, title, header):

        builder = Gtk.Builder()
        builder.set_translation_domain(version.PACKAGE_NAME)

        builder.add_from_file(ui_file)
        builder.connect_signals(self)
        self.window = builder.get_object("window_progress")
        self.button_abort = builder.get_object('button_abort')
        self.progressbar = builder.get_object('progressbar')
        self.label_info = builder.get_object('label_info')
        self.label_header = builder.get_object('label_header')

        self.window.set_title(title)
        if header:
            self.label_header.set_markup(_HEADER_MARKUP %
                    glib.markup_escape_text(header))
        else:
            self.label_header.hide()

        self.update(0, '', '')

    def on_button_abort_clicked(self, widget):
        self.aborted = True
        self.button_abort.set_sensitive(False)

    @idle_call
    def show(self):
        self.window.present()

    @idle_call
    def hide(self):
        self.window.hide()

    @idle_call
    def update(self, value, label, text):
        """ Update dialog information.

        @value: value to set for progress bar
        @label: current action (displayed in emphasized style)
        @text: current information (normal style)
        """
        self.progressbar.set_fraction(min(value/self.max_value, 1.0))
        self.label_info.set_markup("<b>%s</b> %s" %
            (
                glib.markup_escape_text(label),
                glib.markup_escape_text(text),
            ))
        return self.aborted

