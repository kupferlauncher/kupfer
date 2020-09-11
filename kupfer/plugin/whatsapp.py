""" This plugin opens WhatsApp Web in the browser, and can send messages to numbers that are not scheduled 
"""

__kupfer_name__ = _("WhatsApp Web")
__kupfer_sources__ = ()
__kupfer_actions__ = ("WhatsApp",)
__description__ = _("""Open a new number in WhatsApp Web

The number format must respect:
"Country Code" + "Area Code" + "Number"

Example for a New York number: 12129999999
Country Code: 1
Area Code: 212
Number: 9999999

WhatsApp Web will open in the browser.

For help visit https://faq.whatsapp.com/general/chats/how-to-use-click-to-chat/

""")
__version__ = "1.0"
__author__ = "Leonardo Masuero <leom255255@gmail.com>"

from kupfer.objects import Action, TextLeaf
from kupfer import utils

class WhatsApp (Action):
	def __init__(self):
		Action.__init__(self, _("WhatsApp Web"))

	def activate(self, leaf):
		url_w = "https://web.whatsapp.com/send?phone="
		url_number = url_w + leaf.object
		utils.show_url(url_number)

	def item_types(self):
		yield TextLeaf

	def valid_for_item(self, leaf):
		try:
			text = leaf.object
			return text and int(text)
		except:
			pass

	def get_description(self):
		return _("Send a WhatsApp to a new number.")

	def get_icon_name(self):
		return "message-new"
