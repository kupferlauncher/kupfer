__kupfer_name__ = _("Brotab")
__kupfer_sources__ = ("TabSource",)
__kupfer_actions__ = ("TabActivate", "TabClose", "TabGetUrl",)
__description__ = _("Firefox Tabs")
__version__ = "2020.1"
__author__ = "Peter Stuifzand <peter@p83.nl>"

from kupfer.obj.objects import UrlLeaf
from kupfer.objects import Source, Leaf, Action
from brotab.main import create_clients
from brotab.api import MultipleMediatorsAPI


def get_api():
    clients = create_clients()
    return MultipleMediatorsAPI(clients)


def get_active_tab():
    api = get_api()
    tabs = api.get_active_tabs(None)
    return tabs[0]


def get_tabs():
    api = get_api()
    tabs = api.list_tabs([])
    result = []
    for tab in tabs:
        yield tab.split('\t')


class TabLeaf(Leaf):
    """
    Tab leaf

    This Leaf represents a tab from Brotab in Firefox
    """

    def __init__(self, tab_id, title, url):
        self.title = title
        self.url = url
        super(TabLeaf, self).__init__(tab_id, title)

    def get_description(self):
        return self.url

    def get_icon_name(self):
        return "web-browser"


class TabSource(Source):
    """
    Tab source

    This Source contains all Tabs from Firefox (as given by Brotab)
    """
    source_use_cache = False
    task_update_interval_sec = 5

    def __init__(self, name=None):
        super().__init__(name or _("Firefox Tabs"))

    def get_items(self):
        cache = {}
        for tab in get_tabs():
            cache[tab[0]] = tab
            yield TabLeaf(tab[0], tab[1], tab[2])

        active_tabs = get_api().get_active_tabs([])
        for active_tab in active_tabs[0]:
            tab = cache[active_tab]
            yield TabLeaf(tab[0], tab[1], tab[2])

    def get_description(self):
        return _("Firefox browser tabs")

    def provides(self):
        yield TabLeaf

    def get_icon_name(self):
        return "web-browser"


class TabActivate(Action):

    def __init__(self):
        super().__init__(_("Activate Tab"))

    def activate(self, obj, iobj=None, ctx=None):
        get_api().activate_tab([obj.object], True)

    def item_types(self):
        yield TabLeaf

    def get_icon_name(self):
        return "go-jump"


class TabClose(Action):

    def __init__(self):
        super().__init__(_("Close Tab"))

    def activate(self, obj, iobj=None, ctx=None):
        get_api().close_tabs([obj.object])

    def item_types(self):
        yield TabLeaf

    def get_icon_name(self):
        return "window-close"


class TabGetUrl(Action):

    def __init__(self):
        super().__init__(_("Get URL"))

    def has_result(self):
        return True

    def activate(self, obj, iobj=None, ctx=None):
        return UrlLeaf(obj.url, obj.title)

    def item_types(self):
        yield TabLeaf
