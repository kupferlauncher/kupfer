__kupfer_name__ = _("Show Text")
__kupfer_actions__ = (
        "ShowText",
        #"LargeType",
        "ShowNotification",
    )
__description__ = _("Display text in a window")
__version__ = ""
__author__ = "US"

from kupfer.objects import Action, Leaf, TextLeaf
from kupfer import icons, uiutils
from kupfer import textutils


class ShowText (Action):
    def __init__(self):
        Action.__init__(self, _("Show Text"))

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        uiutils.show_text_result(leaf.get_text_representation(),
            title=_("Show Text"), ctx=ctx)

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Display text in a window")
    def get_icon_name(self):
        return "format-text-bold"

class LargeType (Action):
    def __init__(self):
        Action.__init__(self, _("Large Type"))

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        return self.activate_multiple((leaf, ), ctx)

    def activate_multiple(self, objects, ctx):
        all_texts = []
        for obj in objects:
            all_texts.append(obj.get_text_representation())
        uiutils.show_large_type("\n".join(all_texts), ctx)

    def item_types(self):
        yield Leaf

    def valid_for_item(self, obj):
        return hasattr(obj, "get_text_representation")

    def get_description(self):
        return _("Display text in a window")
    def get_gicon(self):
        return icons.ComposedIcon.new("format-text-bold", "zoom-in")
    def get_icon_name(self):
        return "format-text-bold"

class ShowNotification (Action):
    def __init__(self):
        Action.__init__(self, _("Show Notification"))

    def activate(self, leaf):
        title, body = textutils.extract_title_body(leaf.object)
        if body:
            uiutils.show_notification(title, body,
                    icon_name=self.get_icon_name())
        else:
            uiutils.show_notification(title)

    def item_types(self):
        yield TextLeaf

    def get_icon_name(self):
        return "format-text-bold"

