from __future__ import annotations

import typing as ty

from gi.repository import Gdk, Gtk

from kupfer.obj.base import KupferObject

# NOTE: TextRepresentation moved into obj.representation
from kupfer.obj.representation import TextRepresentation, UriListRepresentation


def get_text_representation(obj: ty.Any) -> str | None:
    """
    Get text representation from any @obj.
    """
    try:
        return obj.get_text_representation()  # type: ignore
    except AttributeError:
        return None


def copy_to_clipboard(obj: KupferObject, clipboard: Gtk.Clipboard) -> bool:
    """
    Copy @obj to @clipboard, a Gtk.Clipboard

    Return True if successful
    """
    ## support copying text to clipboard
    ## as well as files in both the general uri-list representation
    ## and in nautilus' file copy clipboard type
    (uri_id, text_id, nautilus_id) = (80, 81, 82)
    nautilus_target = Gdk.Atom.intern("x-special/gnome-copied-files", False)

    # udata is the data dict
    # def store(clipboard, sdata, info, udata):
    #     if info == uri_id:
    #         sdata.set_uris(udata[uri_id])
    #     if info == text_id:
    #         sdata.set_text(udata[text_id])
    #     if info == nautilus_id:
    #         str_data_format = 8
    #         sdata.set(nautilus_target, str_data_format, udata[nautilus_id])

    # def clear(clipboard, udata):
    #     pass

    data: dict[int, ty.Any] = {}
    try:
        urilist = obj.get_urilist_representation()  # type: ignore
    except AttributeError:
        pass
    else:
        if urilist:
            targets = Gtk.TargetList.new(None)
            targets.add_uri_targets(uri_id)
            # targets = Gtk.target_list_add_uri_targets(targets, uri_id)
            targets.add(nautilus_target, 0, nautilus_id)
            data[uri_id] = urilist
            data[nautilus_id] = "copy\n" + "\n".join(urilist)

    try:
        text = obj.get_text_representation()  # type: ignore
    except AttributeError:
        pass
    else:
        targets = Gtk.TargetList.new(None)
        targets.add_text_targets(text_id)
        clipboard.set_text(text, -1)  # -1 for computed string length
        data[text_id] = text

    if data:
        # FIXME: How to set URIs on clipboard?
        # clipboard.set_with_data(targets, store, clear, data)
        # store all targets
        # clipboard.set_can_store(targets)
        return True

    return False
