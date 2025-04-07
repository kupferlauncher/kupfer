import os

from kupfer import config
from kupfer.support import pretty


def _extend_path():
    # Inside a function to not leak variables to module namespace
    if not config.has_capability("CUSTOM_PLUGINS"):
        return

    # Add plugins in data directories
    __path__.extend(config.get_data_dirs("plugins"))

    # Add .zip files in plugins directories
    for directory in __path__.copy():
        try:
            with os.scandir(directory) as entries:
                if zipnames := [f for f in entries if f.name.endswith(".zip")]:
                    pretty.print_debug(__name__, "Adding", directory, zipnames)
                    __path__.extend(z.path for z in zipnames)

        except OSError as error:  # noqa: PERF203
            pretty.print_error(__name__, error)
            continue


_extend_path()
