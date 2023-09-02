"""
Thunderbird  plugin.

Changes:
    2012-03-15: Karol Będkowski
        + activate_multiple for new mail action
"""
__kupfer_name__ = _("Thunderbird")
__kupfer_sources__ = ("ContactsSource",)
__kupfer_actions__ = (
    "NewMailAction",
    "AttachToNewMail",
    "NewMailWithBody",
)
__description__ = _("Thunderbird/Icedove Contacts and Actions")
__version__ = "2017.2"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>, US"

from kupfer import icons, launch, plugin_support
from kupfer.obj import Action, FileLeaf, RunnableLeaf, TextLeaf, UrlLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.contacts import ContactLeaf, EmailContact, email_from_leaf
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.plugin import thunderbird_support as support

plugin_support.check_any_command_available("thunderbird", "icedove")


class ComposeMail(RunnableLeaf):
    """Create new mail without recipient"""

    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Compose New Email"))

    def run(self, ctx=None):
        if not launch.spawn_async(["thunderbird", "--compose"]):
            launch.spawn_async(["icedove", "--compose"])

    def get_description(self):
        return _("Compose a new message in Thunderbird")

    def get_icon_name(self):
        return "mail-message-new"


class NewMailAction(Action):
    """Createn new mail to selected leaf (Contact or TextLeaf)"""

    def __init__(self):
        Action.__init__(self, _("Compose Email To"))

    def activate(self, leaf, iobj=None, ctx=None):
        self.activate_multiple((leaf,))

    def activate_multiple(self, objects):
        recipients = ",".join(
            filter(None, (email_from_leaf(L) for L in objects))
        )
        if not recipients:
            return

        if not launch.spawn_async(["thunderbird", f"mailto:{recipients}"]):
            launch.spawn_async(["icedove", f"mailto:{recipients}"])

    def get_icon_name(self):
        return "mail-message-new"

    def item_types(self):
        yield ContactLeaf
        # we can enter email
        yield TextLeaf
        yield UrlLeaf

    def valid_for_item(self, leaf):
        return bool(email_from_leaf(leaf))


class AttachToNewMail(Action):
    def __init__(self):
        super().__init__(_("Attach in Email To..."))

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        self.activate_multiple((leaf,), (iobj,))

    def activate_multiple(self, objects, iobjects):
        attachments = ",".join(L.object for L in objects)
        recipients = ",".join(
            filter(None, (email_from_leaf(L) for L in iobjects))
        )
        if not recipients:
            return

        args = ["-compose", f"to='{recipients}',attachment='{attachments}'"]
        if not launch.spawn_async(["thunderbird"] + args):
            launch.spawn_async(["icedove"] + args)

    def get_icon_name(self):
        return "mail-message-new"

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        return not leaf.is_dir()

    def requires_object(self):
        return True

    def object_types(self):
        yield ContactLeaf
        # we can enter email
        yield TextLeaf
        yield UrlLeaf

    def valid_object(self, iobj, for_item=None):
        return bool(email_from_leaf(iobj))


class NewMailWithBody(Action):
    def __init__(self):
        super().__init__(_("Compose Email With"))

    def activate(self, leaf, iobj=None, ctx=None):
        args = ["-compose", f"body='{leaf.object}'"]
        if not launch.spawn_async(["thunderbird"] + args):
            launch.spawn_async(["icedove"] + args)

    def get_icon_name(self):
        return "mail-message-new"

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Compose a new message using the text as body")


class ContactsSource(
    AppLeafContentMixin, ToplevelGroupingSource, FilesystemWatchMixin
):
    appleaf_content_id = ("thunderbird", "icedove")
    source_scan_interval: int = 3600

    def __init__(self, name=_("Thunderbird Address Book")):
        ToplevelGroupingSource.__init__(self, name, "Contacts")
        self._version = 2
        self.monitor_token = None

    def initialize(self):
        ToplevelGroupingSource.initialize(self)
        if abook_dirs := list(support.get_addressbook_dirs()):
            self.monitor_token = self.monitor_directories(*abook_dirs)

    def monitor_include_file(self, gfile):
        return gfile and (
            gfile.get_basename().endswith(".mab")
            or gfile.get_basename() == "localstore.rdf"
        )

    def mark_for_update(self, postpone=False):
        super().mark_for_update(postpone=True)

    def get_items(self):
        for name, email in support.get_contacts():
            yield EmailContact(email, name)

        yield ComposeMail()

    def should_sort_lexically(self):
        return True

    def get_description(self):
        return _("Contacts from Thunderbird Address Book")

    def get_gicon(self):
        return icons.get_gicon_with_fallbacks(None, ("thunderbird", "icedove"))

    def provides(self):
        yield ContactLeaf
        yield RunnableLeaf
