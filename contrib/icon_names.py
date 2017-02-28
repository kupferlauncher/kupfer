"""
A quick hack to search the icons of the `Icon Naming Specification`__, shown
as available on the current system.
"""
__kupfer_name__ = _("Icon Names")
__kupfer_sources__ = (
        "StandardIconsSource",
        "IconThemeSource",
    )
__description__ = _("Browse the icons of the Icon Naming Specification")
__version__ = "2017.1"
__author__ = "US"


import urllib.request, urllib.parse, urllib.error
from xml.etree import cElementTree as ET

from gi.repository import Gtk

from kupfer.objects import Leaf, Action, Source, SourceLeaf
from kupfer import uiutils


ICON_SPEC_ADDRESS = "https://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-0.8.90.xml"

class ShowDescription(Action):
    def __init__(self):
        Action.__init__(self, _("Show Full Description"))
    def activate(self, leaf):
        uiutils.show_text_result(leaf.description)

class IconName (Leaf):
    def __init__(self, obj, desc, category):
        Leaf.__init__(self, obj, obj)
        self.description = desc
        if desc:
            self.kupfer_add_alias(desc.splitlines()[0])
    def get_actions(self):
        yield ShowDescription()
    def get_description(self):
        return self.description.splitlines()[0] if self.description else None
    def get_icon_name(self):
        return self.object
    # So that it can be copied to clipboard
    def get_text_representation(self):
        return self.object

class IconNamesSource (Source):
    def get_items(self):
        for name, desc, info in self._get_all_items():
            yield IconName(name, desc, info)

class StandardIconsSource (IconNamesSource):
    def __init__(self):
        return Source.__init__(self, _("Standard Icon Names"))
    def _get_all_items(self):
        parsed = ET.parse(urllib.request.urlopen(ICON_SPEC_ADDRESS))
        root = parsed.getroot()

        icon_names = {}
        def first(lst):
            return next(iter(lst))

        def flatten(tag):
            """return text of @tag and its immediate children"""
            return tag.text + "".join(c.text+c.tail for c in tag.getchildren())

        names = first(s for s in root.findall("sect1") if s.get("id") == "names")
        for table in names.findall("table"):
            category_name = table.get("id")
            rows = table.find("tgroup").find("tbody")
            for row in rows:
                icon_names.setdefault(category_name, []).append(
                        tuple(flatten(e).strip() for e in row.findall("entry")))

        for category in icon_names:
            for name, desc in icon_names[category]:
                yield name, desc, category

    def get_icon_name(self):
        return "emblem-photos"

class IconThemeCategorySource (IconNamesSource):
    def __init__(self, category):
        IconNamesSource.__init__(self, category or "All Icons")
        self.category = category

    def repr_key(self):
        return self.category
    def _get_all_items(self):
        it = Gtk.IconTheme.get_default()
        for icon_name in it.list_icons(self.category):
            desc = str(it.get_icon_sizes(icon_name))
            yield icon_name, desc, self.category

    def should_sort_lexically(self):
        return True

class IconThemeSource (Source):
    def __init__(self):
        Source.__init__(self, _("All Icon Theme Icons"))
    def get_items(self):
        it = Gtk.IconTheme.get_default()
        yield SourceLeaf(IconThemeCategorySource(None))
        for ctx in it.list_contexts():
            yield SourceLeaf(IconThemeCategorySource(ctx))
    def get_icon_name(self):
        it = Gtk.IconTheme.get_default()
        return it.get_example_icon_name()
