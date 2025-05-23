"""
Kupfer's Contacts API

Main definition and *constructor* classes.

Constructor classes such as EmailContact are used to conveniently construct
contacts with common traits. To *use* contacts, always use ContactLeaf, asking
for specific slots to be filled.
"""

from __future__ import annotations

import typing as ty

from kupfer import icons
from kupfer.obj.grouping import GroupingLeaf, Slots
from kupfer.support import validators

if ty.TYPE_CHECKING:
    from gettext import gettext as _

    from gi.repository import GdkPixbuf

    from kupfer.obj.base import Leaf

__author__ = (
    "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>, "
    "Karol Będkowski <karol.bedkowsk+gh@gmail.com>, "
    "Adi Sieker <adi@sieker.info>"
)

__all__ = (
    "AIMContact",
    "AddressContact",
    "ContactLeaf",
    "EmailContact",
    "GoogleTalkContact",
    "ICQContact",
    "IMContact",
    "JabberContact",
    "MSNContact",
    "PhoneContact",
    "QQContact",
    "SkypeContact",
    "YahooContact",
    "email_from_leaf",
)

EMAIL_KEY = "EMAIL"
NAME_KEY = "NAME"
PHONE_KEY = "PHONE"
ADDRESS_KEY = "ADDRESS"
LABEL_KEY = "LABEL"
JABBER_JID_KEY = "JID"
JABBER_STATUS_KEY = "JABBER_STATUS"
JABBER_RESOURCE_KEY = "JABBER_RESOURCE"
AIM_KEY = "AIM"
GOOGLE_TALK_KEY = "GOOGLE_TALK"
ICQ_KEY = "ICQ"
MSN_KEY = "MSN"
QQ_KEY = "QQ"
SKYPE_KEY = "SKYPE"
YAHOO_KEY = "YAHOO"


class ContactLeaf(GroupingLeaf):
    """Represent "human" contact leaf, like email, im address and so."""

    grouping_slots: tuple[str, ...] = ()

    def __init__(self, obj: ty.Any, name: str, image: ty.Any = None) -> None:
        self.image = image
        GroupingLeaf.__init__(self, obj, name)

    def get_icon_name(self) -> str:
        return "stock_person"

    def get_text_representation(self) -> str | None:
        return self.get_description()

    def get_thumbnail(
        self, width: int, height: int
    ) -> GdkPixbuf.Pixbuf | None:
        if self.image:
            return icons.get_pixbuf_from_data(self.image, width, height)

        return GroupingLeaf.get_thumbnail(self, width, height)


## E-mail convenience and constructors


def _get_email_from_url(url: str) -> str:
    """convert http://foo@bar.pl -> foo@bar.pl"""
    *_dummy, email = url.partition("://")
    return email or url


def email_from_leaf(leaf: Leaf) -> str | None:
    """Return an email address string if @leaf has a valid email address.

    @leaf may also be a TextLeaf or UrlLeaf.
    Return a false value if no valid email is found.
    """
    if isinstance(leaf, ContactLeaf):
        return leaf.get(EMAIL_KEY)  # type: ignore

    email = _get_email_from_url(str(leaf.object))
    return email if validators.is_valid_email(email) else None


class EmailContact(ContactLeaf):
    grouping_slots = (*ContactLeaf.grouping_slots, EMAIL_KEY)

    def __init__(self, email: str, name: str, image: ty.Any = None) -> None:
        slots = {EMAIL_KEY: email, NAME_KEY: name}
        ContactLeaf.__init__(self, slots, name, image)

    def repr_key(self) -> ty.Any:
        return self.object[EMAIL_KEY]

    def get_description(self) -> str:
        return self.object[EMAIL_KEY]  #  type:ignore

    def get_gicon(self) -> icons.GIcon:
        return icons.ComposedIconSmall(self.get_icon_name(), "stock_mail")


class IMContact(ContactLeaf):
    grouping_slots = (*ContactLeaf.grouping_slots, EMAIL_KEY)

    def __init__(
        self,
        im_id_kind: str,
        im_id: str,
        name: str,
        label: str | None = None,
        other_slots: Slots = None,
        image: ty.Any = None,
    ) -> None:
        self.im_id_kind = im_id_kind
        slots = {im_id_kind: im_id, NAME_KEY: name, LABEL_KEY: label}
        if other_slots:
            slots.update(other_slots)

        ContactLeaf.__init__(self, slots, name, image)
        self.kupfer_add_alias(im_id)

    def repr_key(self) -> ty.Any:
        return self.object[self.im_id_kind]

    def get_description(self) -> str:
        return (  # type:ignore
            self.object[LABEL_KEY] or self.object[self.im_id_kind]
        )


class JabberContact(IMContact):
    """Minimal class for all Jabber contacts."""

    grouping_slots = (*IMContact.grouping_slots, JABBER_JID_KEY)

    def __init__(
        self,
        jid: str,
        name: str,
        status: str | None = None,
        resource: str | None = None,
        slots: Slots = None,
        image: ty.Any = None,
    ) -> None:
        IMContact.__init__(
            self,
            JABBER_JID_KEY,
            jid,
            name or jid,
            other_slots=slots,
            image=image,
        )
        self._description: str = _("[%(status)s] %(userid)s/%(service)s") % {
            # TRANS: unknown user status
            "status": status or _("unknown"),
            "userid": jid,
            "service": resource or "",
        }

    def get_description(self) -> str:
        return self._description


class AIMContact(IMContact):
    grouping_slots = (*IMContact.grouping_slots, AIM_KEY)

    def __init__(
        self,
        id_: str,
        name: str,
        slots: Slots = None,
        image: ty.Any = None,
    ) -> None:
        IMContact.__init__(self, AIM_KEY, id_, name, _("Aim"), slots, image)


class GoogleTalkContact(IMContact):
    grouping_slots = (*IMContact.grouping_slots, GOOGLE_TALK_KEY)

    def __init__(
        self, id_: str, name: str, slots: Slots = None, image: ty.Any = None
    ) -> None:
        IMContact.__init__(
            self, GOOGLE_TALK_KEY, id_, name, _("Google Talk"), slots, image
        )


class ICQContact(IMContact):
    grouping_slots = (*IMContact.grouping_slots, ICQ_KEY)

    def __init__(
        self, id_: str, name: str, slots: Slots = None, image: ty.Any = None
    ) -> None:
        IMContact.__init__(self, ICQ_KEY, id_, name, _("ICQ"), slots, image)


class MSNContact(IMContact):
    grouping_slots = (*IMContact.grouping_slots, MSN_KEY)

    def __init__(
        self, id_: str, name: str, slots: Slots = None, image: ty.Any = None
    ) -> None:
        IMContact.__init__(self, MSN_KEY, id_, name, _("MSN"), slots, image)


class QQContact(IMContact):
    grouping_slots = (*IMContact.grouping_slots, QQ_KEY)

    def __init__(
        self, id_: str, name: str, slots: Slots = None, image: ty.Any = None
    ) -> None:
        IMContact.__init__(self, QQ_KEY, id_, name, _("QQ"), slots, image)


class YahooContact(IMContact):
    grouping_slots = (*IMContact.grouping_slots, YAHOO_KEY)

    def __init__(
        self, id_: str, name: str, slots: Slots = None, image: ty.Any = None
    ) -> None:
        IMContact.__init__(
            self, YAHOO_KEY, id_, name, _("Yahoo"), slots, image
        )


class SkypeContact(IMContact):
    grouping_slots = (*IMContact.grouping_slots, SKYPE_KEY)

    def __init__(
        self, id_: str, name: str, slots: Slots = None, image: ty.Any = None
    ) -> None:
        IMContact.__init__(
            self, SKYPE_KEY, id_, name, _("Skype"), slots, image
        )


class PhoneContact(ContactLeaf):
    grouping_slots = (*ContactLeaf.grouping_slots, EMAIL_KEY)

    def __init__(
        self,
        number: str,
        name: str,
        label: str,
        slots: Slots = None,
        image: ty.Any = None,
    ) -> None:
        pslots = {PHONE_KEY: number, NAME_KEY: name, LABEL_KEY: label}
        if slots:
            pslots.update(slots)

        ContactLeaf.__init__(self, pslots, name, image)

    def repr_key(self) -> ty.Any:
        return self.object[PHONE_KEY]

    def get_description(self) -> str:
        return f"{self.object[LABEL_KEY]}: {self.object[PHONE_KEY]}"


class AddressContact(ContactLeaf):
    grouping_slots = (*ContactLeaf.grouping_slots, EMAIL_KEY)

    def __init__(
        self,
        address: str,
        name: str,
        label: str,
        slots: Slots = None,
        image: ty.Any = None,
    ) -> None:
        aslots = {ADDRESS_KEY: address, NAME_KEY: name, LABEL_KEY: label}
        if slots:
            aslots.update(slots)

        ContactLeaf.__init__(self, aslots, name, image)

    def repr_key(self) -> ty.Any:
        return self.object[ADDRESS_KEY]
