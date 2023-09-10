__kupfer_name__ = _("Instapaper")
__kupfer_sources__ = ()
__kupfer_actions__ = ("SaveToInstapaper",)
__description__ = _("Save url to Instapaper")
__version__ = "2020-11-15"
__author__ = "Peter Stuifzand <peter@p83.nl>"
import typing as ty

from kupfer import launch
from kupfer.obj import Action, TextLeaf, UrlLeaf

if ty.TYPE_CHECKING:
    from gettext import gettext as _


class SaveToInstapaper(Action):
    def __init__(self):
        Action.__init__(self, _("Save to Instapaper"))

    def activate(self, leaf, iobj=None, ctx=None):
        launch.show_url(f"https://www.instapaper.com/edit?url={leaf.object}")

    def item_types(self):
        yield UrlLeaf
        yield TextLeaf

    def get_description(self):
        return _("Save url to Instapaper")
