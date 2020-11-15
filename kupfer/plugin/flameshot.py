__kupfer_name__ = _("Flameshot")
__kupfer_sources__ = ("FlameshotSource",)
__kupfer_actions__ = ()
__description__ = _("Take screenshot with Flameshot")
__version__ = ""
__author__ = "Peter Stuifzand <peter@p83.nl>"

from kupfer import utils
from kupfer.objects import RunnableLeaf, Source


class FlameshotTakeScreenshot(RunnableLeaf):
    def __init__(self):
        super().__init__(self, name=_("Take Screenshot"))

    def run(self):
        utils.spawn_async(["flameshot", "gui"])

    def get_icon_name(self):
        return "flameshot"


class FlameshotSource(Source):
    def __init__(self):
        super().__init__(_("Flameshot"))

    def get_items(self):
        yield FlameshotTakeScreenshot()

    def get_description(self):
        return None

    def get_icon_name(self):
        return "flameshot"
