"""
This is a simple plugin demonstration, how to add single, simple actions
"""

__kupfer_name__ = _("Wikipedia")
__kupfer_sources__ = ()
__kupfer_actions__ = ("WikipediaSearch",)
__description__ = _("Search in Wikipedia")
__version__ = "2017.1"
__author__ = "US"

import urllib.parse

from kupfer import launch, plugin_support
from kupfer.obj import Action, Leaf, Source, TextLeaf

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "lang",
        "label": _("Wikipedia languages (separated by ';')"),
        "type": str,
        # TRANS: Default wikipedia language code
        "value": _("en"),
    },
)


class Lang(Leaf):
    def __init__(self, lang):
        super().__init__(lang, name=f"{lang}.wikipedia.org")

    def get_icon_name(self):
        return self.object


class LangSource(Source):
    def __init__(self, languages):
        super().__init__("Languages")
        self.languages = languages

    def get_items(self):
        return map(Lang, self.languages)


class WikipediaSearch(Action):
    action_accelerator = "w"

    def __init__(self):
        Action.__init__(self, _("Search in Wikipedia"))
        self._update_settings()

    def initialize(self):
        __kupfer_settings__.connect_settings_changed_cb(self._update_settings)
        self._update_settings()

    def _update_settings(self, *_args):
        languages: tuple[str, ...] = tuple(
            filter(
                None,
                (
                    lang.strip()
                    for lang in __kupfer_settings__["lang"].split(";")
                ),
            )
        )

        if not languages:
            languages = (_("en"),)

        self._languages = languages

    def activate(self, leaf, iobj=None, ctx=None):
        # Send in UTF-8 encoding
        if iobj:
            lang_code = iobj.object
        else:
            lang_code = self._languages[0]

        search_url = f"https://{lang_code}.wikipedia.org/w/index.php?title=Special:Search&go=Go&"
        # will encode search=text, where `text` is escaped
        query_url = search_url + urllib.parse.urlencode({"search": leaf.object})
        launch.show_url(query_url)

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        if len(self._languages) == 1:
            lang_code = self._languages[0]
            return _("Search for this term in %s.wikipedia.org") % lang_code

        return _("Search for this term in %s.wikipedia.org") % ""

    def get_icon_name(self):
        return "edit-find"

    def requires_object(self):
        return len(self._languages) > 1

    def object_source(self, for_item=None):
        return LangSource(self._languages)

    def object_types(self):
        yield Lang
