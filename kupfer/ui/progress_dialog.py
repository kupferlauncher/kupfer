import gtk

from kupfer import version, config, kupferstring


_HEADER_MARKUP = '<span weight="bold" size="larger">%s</span>'

class ProgressDialogController():
	def __init__(self, title, header=None, label=None, max_value=100):
		"""Load ui from data file"""
		builder = gtk.Builder()
		builder.set_translation_domain(version.PACKAGE_NAME)
		ui_file = config.get_data_file("progress_dialog.ui")

		builder.add_from_file(ui_file)
		builder.connect_signals(self)
		self.window = builder.get_object("window_progress")
		self.button_abort = builder.get_object('button_abort')
		self.progressbar = builder.get_object('progressbar')
		self.label_info = builder.get_object('label_info')
		self.label_header = builder.get_object('label_header')

		self.aborted = False
		self.max_value = float(max_value)

		self.window.set_title(title)
		if header:
			self.label_header.set_markup(_HEADER_MARKUP % header)
		else:
			self.label_header.hide()

		self.update(0, label or '')

	def on_button_abort_clicked(self, widget):
		self.aborted = True
		self.button_abort.set_sensitive(False)

	def show(self):
		return self.window.present()

	def hide(self):
		return self.window.hide()

	def update(self, value, label):
		self.progressbar.set_fraction(min(value/self.max_value, 1.0))
		self.label_info.set_markup(kupferstring.toutf8(label))
		return self.aborted

