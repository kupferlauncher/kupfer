
def _extend_path():
    # Inside a function to not leak variables to module namespace
    import os
    from kupfer import config
    from kupfer import pretty

    if not config.has_capability("CUSTOM_PLUGINS"):
        return

    # Add plugins in data directories
    __path__.extend(config.get_data_dirs("plugins"))

    # Add .zip files in plugins directories
    for directory in list(__path__):
        try:
            filenames = os.listdir(directory)
        except OSError as error:
            pretty.print_error(__name__, error)
            continue
        zipnames = [f for f in filenames if f.endswith(".zip")]
        if zipnames:
            pretty.print_debug(__name__, "Adding", directory, zipnames)
        __path__.extend(os.path.join(directory, z) for z in zipnames)

_extend_path()

