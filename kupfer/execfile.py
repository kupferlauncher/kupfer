import pickle
import os

from kupfer import pretty
from kupfer import puid
from kupfer import conspickle

KUPFER_COMMAND_SHEBANG="#!/usr/bin/env kupfer-exec\n"

def execute_file(filepath):
	"""Execute serialized command inside @filepath

	The file must be executable (comparable to a shell script)
	>>> execute_file(__file__)  # doctest: +ELLIPSIS
	Traceback (most recent call last):
	    ...
	OSError: ... is not executable
	"""
	if not os.path.exists(filepath):
		raise IOError("%s does not exist" % (filepath, ))
	if not os.access(filepath, os.X_OK):
		raise OSError("%s is not executable" % (filepath, ))
	data = open(filepath).read()
	# strip shebang away
	if data.startswith("#!") and "\n" in data:
		shebang, data = data.split("\n", 1)

	try:
		id_ = conspickle.BasicUnpickler.loads(data)
		command_object = puid.resolve_unique_id(id_)
	except pickle.UnpicklingError, err:
		pretty.print_error(__name__, "Could not read", filepath, err)
		return
	command_object.run()

def save_to_file(command_leaf, filename):
	fd = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o777)
	wfile = os.fdopen(fd, "wb")
	try:
		wfile.write(KUPFER_COMMAND_SHEBANG)
		pickle.dump(puid.get_unique_id(command_leaf), wfile, 0)
	finally:
		wfile.close()

if __name__ == '__main__':
	import doctest
	doctest.testmod()
