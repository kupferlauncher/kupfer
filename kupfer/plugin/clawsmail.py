__kupfer_name__ = _("Claws Mail")
__kupfer_sources__ = ("ClawsContactsSource",)
__kupfer_actions__ = ("NewMailAction", "SendFileByMail")
__description__ = _("Claws Mail Contacts and Actions")
__version__ = "2018-10-07"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import xml
from pathlib import Path
from xml.dom import minidom
import typing as ty

from kupfer import launch, plugin_support
from kupfer.obj import Action, FileLeaf, RunnableLeaf, TextLeaf, UrlLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.contacts import ContactLeaf, EmailContact, email_from_leaf
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.helplib import FilesystemWatchMixin

if ty.TYPE_CHECKING:
    from gettext import gettext as _


plugin_support.check_command_available("claws-mail")


class ComposeMail(RunnableLeaf):
    """Create new mail without recipient"""

    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Compose New Email"))

    def run(self, ctx=None):
        launch.spawn_async(["claws-mail", "--compose"])

    def get_description(self):
        return _("Compose a new message in Claws Mail")

    def get_icon_name(self):
        return "mail-message-new"


class ReceiveMail(RunnableLeaf):
    """Receive all new mail from all accounts"""

    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Receive All Email"))

    def run(self, ctx=None):
        launch.spawn_async(["claws-mail", "--receive-all"])

    def get_description(self):
        return _("Receive new messages from all accounts in ClawsMail")

    def get_icon_name(self):
        return "mail-send-receive"


class NewMailAction(Action):
    """Create new mail to selected leaf"""

    def __init__(self):
        Action.__init__(self, _("Compose Email"))

    def activate(self, leaf, iobj=None, ctx=None):
        self.activate_multiple((leaf,))

    def activate_multiple(self, objects):
        recipients = ",".join(filter(None, map(email_from_leaf, objects)))
        launch.spawn_async(["claws-mail", "--compose", recipients])

    def get_icon_name(self):
        return "mail-message-new"

    def item_types(self):
        yield ContactLeaf
        # we can enter email
        yield TextLeaf
        yield UrlLeaf

    def valid_for_item(self, leaf):
        return bool(email_from_leaf(leaf))


class SendFileByMail(Action):
    """Create new e-mail and attach selected file"""

    def __init__(self):
        Action.__init__(self, _("Send in Email To..."))

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        self.activate_multiple((leaf,), (iobj,))

    def activate_multiple(self, objects, iobjects):
        recipients = ",".join(filter(None, map(email_from_leaf, iobjects)))
        attachlist = ["--attach"] + [L.object for L in objects]
        launch.spawn_async(["claws-mail", "--compose", recipients] + attachlist)

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

    def get_description(self):
        return _("Compose new message in Claws Mail and attach file")

    def get_icon_name(self):
        return "document-send"


class ClawsContactsSource(
    AppLeafContentMixin, ToplevelGroupingSource, FilesystemWatchMixin
):
    appleaf_content_id = "claws-mail"
    source_scan_interval: int = 3600

    def __init__(self, name=_("Claws Mail Address Book")):
        super().__init__(name, "Contacts")
        self._claws_addrbook_dir = Path("~/.claws-mail/addrbook").expanduser()
        self._claws_addrbook_index = self._claws_addrbook_dir.joinpath(
            "addrbook--index.xml"
        )
        self._version = 5
        self.monitor_token = None

    def initialize(self):
        ToplevelGroupingSource.initialize(self)
        if not self._claws_addrbook_dir.is_dir():
            return

        self.monitor_token = self.monitor_directories(
            str(self._claws_addrbook_dir)
        )

    def monitor_include_file(self, gfile):
        # monitor only addrbook-*.xml files
        return (
            gfile
            and gfile.get_basename().endswith(".xml")
            and gfile.get_basename().startswith("addrbook-")
        )

    def mark_for_update(self, postpone=False):
        super().mark_for_update(postpone=True)

    def get_items(self):
        if self._claws_addrbook_index.is_file():
            for addrbook_file in self._load_address_books():
                addrbook_filepath = self._claws_addrbook_dir.joinpath(
                    addrbook_file
                )
                if not addrbook_filepath.exists():
                    continue

                try:
                    dtree = minidom.parse(str(addrbook_filepath))
                    persons = dtree.getElementsByTagName("person")
                    for person in persons:
                        commonname = person.getAttribute("cn")
                        addresses = person.getElementsByTagName("address")
                        for address in addresses:
                            email = address.getAttribute("email")
                            yield EmailContact(email, commonname)

                except (Exception, xml.parsers.expat.ExpatError) as err:
                    self.output_error(err)

        yield ComposeMail()
        yield ReceiveMail()

    def should_sort_lexically(self):
        # since it is a grouping source, grouping and non-grouping will be
        # separate and only grouping leaves will be sorted
        return True

    def get_description(self):
        return _("Contacts from Claws Mail Address Book")

    def get_icon_name(self):
        return "claws-mail"

    def provides(self):
        yield RunnableLeaf
        yield ContactLeaf

    def _load_address_books(self):
        """load list of address-book files"""
        try:
            dtree = minidom.parse(str(self._claws_addrbook_index))
            for book in dtree.getElementsByTagName("book"):
                yield book.getAttribute("file")

        except (Exception, xml.parsers.expat.ExpatError) as err:
            self.output_error(err)
