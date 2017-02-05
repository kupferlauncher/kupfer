"""
Work with Textfiles: Allow appending and writing new files,
or extracting the content of files.

All Text in Kupfer is in unicode. When we read from textfiles or write
to textfiles, we always work in the locale-defined encoding.

FIXME: Be less strict (use UTF-8 if locale says Ascii)
"""



__kupfer_name__ = _("Textfiles")
__kupfer_actions__ = (
		"AppendTo",
		"AppendText",
		"WriteTo",
		"GetTextContents",
	)
__description__ = None
__version__ = "0.1"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from gi.repository import Gio

from kupfer.objects import Action
from kupfer.objects import TextLeaf, FileLeaf
from kupfer.obj import helplib
from kupfer import kupferstring
from kupfer import utils

# FIXME: Sometimes require that the type is *exactly* text/plain?

def is_content_type(fileleaf, ctype):
	predicate = Gio.content_type_is_a
	ctype_guess, uncertain = Gio.content_type_guess(fileleaf.object, None)
	ret = predicate(ctype_guess, ctype)
	if ret or not uncertain:
		return ret
	content_attr = Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE
	gfile = Gio.File.new_for_path(fileleaf.object)
	if not gfile.query_exists(None):
		return
	info = gfile.query_info(content_attr, Gio.FileQueryInfoFlags.NONE, None)
	content_type = info.get_attribute_string(content_attr)
	return predicate(content_type, ctype)

class AppendTo (Action):
	def __init__(self, name=None):
		if not name:
			name = _("Append To...")
		Action.__init__(self, name)

	def activate(self, leaf, iobj):
		l_text = kupferstring.tolocale(leaf.object)
		with open(iobj.object, "ab") as outfile:
			outfile.write(l_text)
			outfile.write("\n")

	def item_types(self):
		yield TextLeaf

	def requires_object(self):
		return True
	def object_types(self):
		yield FileLeaf
	def valid_object(self, iobj, for_item=None):
		return is_content_type(iobj, "text/plain")

	def get_icon_name(self):
		return "list-add"

class AppendText (helplib.reverse_action(AppendTo)):
	def __init__(self):
		Action.__init__(self, _("Append..."))

class WriteTo (Action):
	def __init__(self):
		Action.__init__(self, _("Write To..."))

	def has_result(self):
		return True

	def activate(self, leaf, iobj):
		outfile, outpath = \
				utils.get_destfile_in_directory(iobj.object, _("Empty File"))
		try:
			l_text = kupferstring.tolocale(leaf.object)
			outfile.write(l_text)
			if not l_text.endswith("\n"):
				outfile.write("\n")
		finally:
			outfile.close()
		return FileLeaf(outpath)

	def item_types(self):
		yield TextLeaf

	def requires_object(self):
		return True
	def object_types(self):
		yield FileLeaf
	def valid_object(self, iobj, for_item=None):
		return iobj.is_dir()

	def get_icon_name(self):
		return "document-new"

class GetTextContents (Action):
	def __init__(self):
		Action.__init__(self, _("Get Text Contents"))

	def has_result(self):
		return True

	def activate(self, leaf):
		with open(leaf.object, "rb") as infile:
			l_text = infile.read()
			us_text = kupferstring.fromlocale(l_text)
		return TextLeaf(us_text)

	def item_types(self):
		yield FileLeaf
	def valid_for_item(self, item):
		return is_content_type(item, "text/plain")

	def get_icon_name(self):
		return "edit-copy"
