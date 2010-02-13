import hashlib
import pickle
import os

import gio
import glib

from kupfer import pretty
from kupfer import puid
from kupfer import conspickle

KUPFER_COMMAND_SHEBANG="#!/usr/bin/env kupfer-exec\n"

class ExecutionError (Exception):
	pass

def execute_file(filepath):
	"""Execute serialized command inside @filepath

	The file must be executable (comparable to a shell script)
	>>> execute_file(__file__)  # doctest: +ELLIPSIS
	Traceback (most recent call last):
	    ...
	ExecutionError: ... (not executable)
	"""
	if not os.path.exists(filepath):
		raise IOError('"%s" does not exist' % (filepath, ))
	if not os.access(filepath, os.X_OK):
		raise ExecutionError(_('No permission to run "%s" (not executable)') %
				glib.filename_display_basename(filepath))

	# strip shebang away
	data = open(filepath).read()
	if data.startswith("#!") and "\n" in data:
		shebang, data = data.split("\n", 1)

	try:
		id_ = conspickle.BasicUnpickler.loads(data)
		command_object = puid.resolve_unique_id(id_)
	except pickle.UnpicklingError, err:
		raise ExecutionError("Could not parse: %s" % unicode(err))
	except Exception:
		raise ExecutionError('"%s" is not a saved command' %
				os.path.basename(filepath))
	if command_object is None:
		raise ExecutionError(_('Command in "%s" is not available') %
				glib.filename_display_basename(filepath))

	command_object.run()
	glib.idle_add(update_icon, command_object, filepath)

def save_to_file(command_leaf, filename):
	fd = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o777)
	wfile = os.fdopen(fd, "wb")
	try:
		wfile.write(KUPFER_COMMAND_SHEBANG)
		pickle.dump(puid.get_unique_id(command_leaf), wfile, 0)
	finally:
		wfile.close()

def _write_thumbnail(gfile, pixbuf):
	uri = gfile.get_uri()
	hashname = hashlib.md5(uri).hexdigest()
	thumb_dir = os.path.expanduser("~/.thumbnails/normal")
	if not os.path.exists(thumb_dir):
		os.makedirs(thumb_dir, 0700)
	thumb_filename = os.path.join(thumb_dir, hashname + ".png")
	pixbuf.save(thumb_filename, "png")
	return thumb_filename

def update_icon(kobj, filepath):
	"Give @filepath a custom icon taken from @kobj"
	icon_key = "metadata::custom-icon"

	gfile = gio.File(filepath)
	finfo = gfile.query_info(icon_key)
	custom_icon_uri = finfo.get_attribute_string(icon_key)
	if custom_icon_uri and gio.File(custom_icon_uri).query_exists():
		return
	pretty.print_debug(__name__, "Updating icon for", filepath)
	thumb_filename = _write_thumbnail(gfile, kobj.get_pixbuf(128))
	if any(N.name == "metadata" for N in gfile.query_writable_namespaces()):
		gfile.set_attribute_string("metadata::custom-icon",
				gio.File(thumb_filename).get_uri())


if __name__ == '__main__':
	import doctest
	doctest.testmod()
