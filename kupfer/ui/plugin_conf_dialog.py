import gtk

class PluginConfDialogController:
	def __init__(self, parent, title):
		self.dialog = gtk.Dialog(title, parent,
				gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
				(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
				gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		self.dialog.set_border_width(12)
		self.dialog.set_has_separator(False)
		self.dialog.vbox.set_spacing(12)

	@property
	def vbox(self):
		return self.dialog.vbox

	def add_header(self, markup):
		title = gtk.Label()
		title.set_markup(markup)
		title.show()
		self.dialog.vbox.pack_start(title)
		return title

	def add_scrolled_wnd(self, content):
		scrolledwnd = gtk.ScrolledWindow()
		scrolledwnd.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		scrolledwnd.set_size_request(200, 300)
		scrolledwnd.add(content)
		scrolledwnd.show()
		self.dialog.vbox.pack_start(scrolledwnd)
		return scrolledwnd

	def run(self):
		response = self.dialog.run()
		self.dialog.destroy()
		return response == gtk.RESPONSE_ACCEPT


