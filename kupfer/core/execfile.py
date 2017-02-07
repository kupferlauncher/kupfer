import hashlib
import pickle
import os

from gi.repository import Gio, GLib

from kupfer import pretty
from kupfer import puid
from kupfer import conspickle

KUPFER_COMMAND_SHEBANG=b"#!/usr/bin/env kupfer-exec\n"

class ExecutionError (Exception):
    pass

def parse_kfcom_file(filepath):
    """Extract the serialized command inside @filepath

    The file must be executable (comparable to a shell script)
    >>> parse_kfcom_file(__file__)  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ExecutionError: ... (not executable)

    Return commands triple
    """
    fobj = open(filepath, "rb")
    if not os.access(filepath, os.X_OK):
        raise ExecutionError(_('No permission to run "%s" (not executable)') %
                GLib.filename_display_basename(filepath))

    # strip shebang away
    data = fobj.read()
    if data.startswith(b"#!") and b"\n" in data:
        shebang, data = data.split(b"\n", 1)

    try:
        id_ = conspickle.BasicUnpickler.loads(data)
        command_object = puid.resolve_unique_id(id_)
    except pickle.UnpicklingError as err:
        raise ExecutionError("Could not parse: %s" % str(err))
    except Exception:
        raise ExecutionError('"%s" is not a saved command' %
                os.path.basename(filepath))
    if command_object is None:
        raise ExecutionError(_('Command in "%s" is not available') %
                GLib.filename_display_basename(filepath))

    try:
        return tuple(command_object.object)
    except (AttributeError, TypeError):
        raise ExecutionError('"%s" is not a saved command' %
                os.path.basename(filepath))
    finally:
        GLib.idle_add(update_icon, command_object, filepath)

def save_to_file(command_leaf, filename):
    fd = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o777)
    wfile = os.fdopen(fd, "wb")
    try:
        wfile.write(KUPFER_COMMAND_SHEBANG)
        pickle.dump(puid.get_unique_id(command_leaf), wfile, protocol=3)
    finally:
        wfile.close()

def _write_thumbnail(gfile, pixbuf):
    uri = gfile.get_uri()
    hashname = hashlib.md5(uri.encode("utf-8")).hexdigest()
    thumb_dir = os.path.expanduser("~/.thumbnails/normal")
    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir, 0o700)
    thumb_filename = os.path.join(thumb_dir, hashname + ".png")
    pixbuf.savev(thumb_filename, "png", [], [])
    return thumb_filename

def update_icon(kobj, filepath):
    "Give @filepath a custom icon taken from @kobj"
    icon_key = "metadata::custom-icon"

    gfile = Gio.File.new_for_path(filepath)
    finfo = gfile.query_info(icon_key, Gio.FileQueryInfoFlags.NONE, None)
    custom_icon_uri = finfo.get_attribute_string(icon_key)
    if custom_icon_uri and Gio.File.new_for_uri(custom_icon_uri).query_exists():
        return
    namespace = gfile.query_writable_namespaces() # FileAttributeInfoList
    if namespace.n_infos > 0:
        pretty.print_debug(__name__, "Updating icon for", filepath)
        thumb_filename = _write_thumbnail(gfile, kobj.get_pixbuf(128))
        try:
            gfile.set_attribute_string(icon_key,
                    Gio.File.new_for_path(thumb_filename).get_uri(),
                    Gio.FileQueryInfoFlags.NONE,
                    None)
        except GLib.GError:
            pretty.print_exc(__name__)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
