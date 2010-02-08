import os

from kupfer import config
from kupfer import pretty

# Add plugins in data directories
__path__.extend(config.get_data_dirs("plugins"))

# Add .zip files in plugins directories
for directory in list(__path__):
	try:
		filenames = os.listdir(directory)
	except OSError, err:
		pretty.print_error(__name__, err)
		continue
	zipnames = [f for f in filenames if f.endswith(".zip")]
	if zipnames:
		pretty.print_debug(__name__, "Adding", directory, zipnames)
	__path__.extend(os.path.join(directory, z) for z in zipnames)
