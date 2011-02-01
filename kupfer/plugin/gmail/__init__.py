# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Gmail")
__kupfer_sources__ = ("GoogleContactsSource", )
__kupfer_actions__ = ('NewMailAction', )
__description__ = _("Load contacts and compose new email in Gmail")
__version__ = "2010-04-06"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import urllib
import time

import gdata.service
import gdata.contacts.service

from kupfer.objects import Action, TextLeaf, UrlLeaf
from kupfer.obj.special import PleaseConfigureLeaf, InvalidCredentialsLeaf
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.contacts import ContactLeaf, email_from_leaf
from kupfer.obj.contacts import JabberContact, AddressContact, PhoneContact
from kupfer.obj.contacts import IMContact, EmailContact
from kupfer import plugin_support, pretty, utils, icons, kupferstring
from kupfer.plugin.skype import Contact as SkypeContact

plugin_support.check_keyring_support()

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		'key': 'userpass',
		'label': '',
		'type': plugin_support.UserNamePassword,
		'value': '',
	},
	{
		'key': 'loadicons',
		'label': _("Load contacts' pictures"),
		'type': bool,
		'value': True,
	}
)

GMAIL_NEW_MAIL_URL = \
	"https://mail.google.com/mail/?view=cm&ui=2&tf=0&to=%(emails)s&fs=1"

GMAIL_EDIT_CONTACT_URL = "https://mail.google.com/mail/#contact/%(contact)s"

REL_TYPE_EMAIL = "email"
REL_TYPE_ADDRESS = "address"
REL_TYPE_PHONE = "phone"
REL_TYPE_IM = "im"
REL_LIST = {}

REL_LIST[REL_TYPE_EMAIL] = {gdata.contacts.REL_WORK: _("Work email"),
                            gdata.contacts.REL_HOME: _("Home email"),
                            gdata.contacts.REL_OTHER: _("Other email")
}

REL_LIST[REL_TYPE_ADDRESS] = {gdata.contacts.REL_WORK: _("Work address"),
                              gdata.contacts.REL_HOME: _("Home address"),
                              gdata.contacts.REL_OTHER: _("Other address")
}

REL_LIST[REL_TYPE_PHONE] = {gdata.contacts.PHONE_CAR: _("Car phone"),
                            gdata.contacts.PHONE_FAX: _("Fax"),
                            gdata.contacts.PHONE_GENERAL: _("General"),
                            gdata.contacts.PHONE_HOME: _("Home phone"),
                            gdata.contacts.PHONE_HOME_FAX: _("Home fax"),
                            gdata.contacts.PHONE_INTERNAL: _("Internal phone"),
                            gdata.contacts.PHONE_MOBILE: _("Mobile"),
                            gdata.contacts.PHONE_OTHER: _("Other"),
                            gdata.contacts.PHONE_VOIP: _("VOIP"),
                            gdata.contacts.PHONE_WORK: _("Work phone"),
                            gdata.contacts.PHONE_WORK_FAX: _("Work fax")
}

REL_LIST[REL_TYPE_IM] = {gdata.contacts.IM_AIM: _("Aim"),
                         gdata.contacts.IM_GOOGLE_TALK: _("Google Talk"),
                         gdata.contacts.IM_ICQ: _("ICQ"),
                         gdata.contacts.IM_JABBER: _("Jabber"),
                         gdata.contacts.IM_MSN: _("MSN"),
                         gdata.contacts.IM_QQ: _("QQ"),
                         gdata.contacts.IM_SKYPE: _("Skype"),
                         gdata.contacts.IM_YAHOO: _("Yahoo")
}

def is_plugin_configured():
	''' Check if plugin is configured (user name and password is configured) '''
	upass = __kupfer_settings__['userpass']
	return bool(upass and upass.username and upass.password)


class NewMailAction(Action):
	''' Create new mail to selected leaf'''
	def __init__(self):
		Action.__init__(self, _('Compose Email in Gmail'))

	def activate(self, obj):
		self.activate_multiple((obj, ))

	def activate_multiple(self, objects):
		recipients = ",".join(urllib.quote(email_from_leaf(L)) for L in objects)
		url = GMAIL_NEW_MAIL_URL % dict(emails=recipients)
		utils.show_url(url)

	def get_gicon(self):
		return icons.ComposedIcon("mail-message-new", "gmail")

	def item_types(self):
		yield ContactLeaf
		# we can enter email
		yield TextLeaf
		yield UrlLeaf

	def valid_for_item(self, item):
		return bool(email_from_leaf(item))

	def get_description(self):
		return _("Open web browser and compose new email in Gmail")


class EditContactAction(Action):
	''' Edit contact in Gmail'''
	def __init__(self):
		Action.__init__(self, _('Edit Contact in Gmail'))

	def activate(self, obj):
		url = GMAIL_EDIT_CONTACT_URL % dict(contact=obj.google_contact_id)
		utils.show_url(url)

	def get_icon_name(self):
		return 'document-properties'

	def get_description(self):
		return _("Open web browser and edit contact in Gmail")



def get_gclient():
	''' create gdata client object and login do google service '''
	if not is_plugin_configured():
		return None
	upass = __kupfer_settings__['userpass']
	gd_client = gdata.contacts.service.ContactsService()
	gd_client.email = upass.username
	gd_client.password = upass.password
	gd_client.source = 'kupfer.gmail'
	gd_client.ProgrammaticLogin()
	return gd_client

def get_label(rel_type, key):
	try:
		return REL_LIST[rel_type][key]
	except KeyError:
		return u''

def get_contacts():
	''' load all contacts '''
	pretty.print_debug(__name__, 'get_contacts start')
	start_time = time.time()
	num_contacts = 0
	try:
		gd_client = get_gclient()

		if gd_client is None:
			return

		query = gdata.contacts.service.ContactsQuery()
		query.max_results = 9999 # load all contacts
		for entry in gd_client.GetContactsFeed(query.ToUri()).entry:
			num_contacts += 1
			common_name = kupferstring.tounicode(entry.title.text)
			contact_id = None
			try:
				contact_id = entry.id.text.split('/')[-1]
			except:
				pass
			for email in entry.email:
				if email.address:
					image = None
					if __kupfer_settings__['loadicons']:
						# Sometimes GetPhoto can't find appropriate image (404)
						try:
							image = gd_client.GetPhoto(entry)
						except:
							pass
					email = email.address
					yield GoogleContact(email, common_name or email, image, contact_id)

			for phone in entry.phone_number:
				if not phone.text:
					continue
				yield PhoneContact(phone.text, common_name, get_label(REL_TYPE_PHONE, phone.rel))

			for address in entry.postal_address:
				if not address.text:
					continue
				yield AddressContact(address.text, common_name, get_label(REL_TYPE_ADDRESS, address.rel))

			for im in entry.im:
				if not im.text:
					continue
				if im.rel == gdata.contacts.IM_SKYPE:
					yield SkypeContact(common_name, im.text, "Unknown")
				elif im.rel == gdata.contacts.IM_JABBER:
					yield JabberContact(im.text, common_name, "Unknown", None)
				else:
					yield IMContact(im.text, common_name, get_label(REL_TYPE_IM, im.rel))

	except (gdata.service.BadAuthentication, gdata.service.CaptchaRequired), err:
		pretty.print_error(__name__, 'get_contacts error',
				'authentication error', err)
		yield InvalidCredentialsLeaf(__name__, __kupfer_name__)

	except gdata.service.Error, err:
		pretty.print_error(__name__, 'get_contacts error', err)

	else:
		pretty.print_debug(__name__, 'get_contacts finished; load contacts:',
				num_contacts, 'in:', time.time()-start_time, 'load_icons:',
				__kupfer_settings__['loadicons'])


class GoogleContact(EmailContact):
	def __init__(self, email, name, image, contact_id):
		EmailContact.__init__(self, email, name)
		self.image = image
		self.google_contact_id = contact_id

	def get_thumbnail(self, width, height):
		if self.image:
			return icons.get_pixbuf_from_data(self.image, width, height)
		return EmailContact.get_thumbnail(self, width, height)

	def get_actions(self):
		if self.google_contact_id:
			yield EditContactAction()


class GoogleContactsSource(ToplevelGroupingSource):
	source_user_reloadable = True

	def __init__(self, name=_("Gmail")):
		super(GoogleContactsSource, self).__init__(name, "Contacts")
		self._version = 4
		self._contacts = []

	def initialize(self):
		ToplevelGroupingSource.initialize(self)
		__kupfer_settings__.connect("plugin-setting-changed", self._changed)

	def _changed(self, settings, key, value):
		if key == "userpass":
			self._contacts = []
			self.mark_for_update()

	def get_items(self):
		if is_plugin_configured():
			return self._contacts
		return [PleaseConfigureLeaf(__name__, __kupfer_name__)]

	def get_items_forced(self):
		if is_plugin_configured():
			self._contacts = list(get_contacts())
			return self._contacts
		return [PleaseConfigureLeaf(__name__, __kupfer_name__)]

	def should_sort_lexically(self):
		return True

	def provides(self):
		yield ContactLeaf
		yield PleaseConfigureLeaf

	def get_description(self):
		return _("Contacts from Google services (Gmail)")

	def get_icon_name(self):
		return "gmail"

