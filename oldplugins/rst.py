__kupfer_name__ = _("reStructuredText")
__kupfer_actions__ = ("RenderView", )
__description__ = _("Render reStructuredText and show the result")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os

from kupfer.objects import Action, FileLeaf
from kupfer import utils, icons


# docutils is a critical import -- not a core kupfer dependency
import docutils.core

class RenderView (Action):
    def __init__(self):
        Action.__init__(self, _("View as HTML Document"))

    def activate(self, leaf):
        finput = open(leaf.object, "rb")
        (foutput, fpath) = utils.get_safe_tempfile()
        try:
            docutils.core.publish_file(finput,
                    destination=foutput,
                    writer_name="html")
        finally:
            finput.close()
            foutput.close()
        utils.show_path(fpath)
    def item_types(self):
        yield FileLeaf
    def valid_for_item(self, leaf):
        root, ext = os.path.splitext(leaf.object)
        return ext.lower() in (".rst", ".rest", ".txt")
    def get_description(self):
        return __description__
    def get_gicon(self):
        return icons.ComposedIcon(Action.get_icon_name(self), "python")
