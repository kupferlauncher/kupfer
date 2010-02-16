# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Twitter")
__kupfer_sources__ = ("FriendsSource", "TimelineSource")
__kupfer_actions__ = ("PostUpdate", "PostDirectMessage", 
		'PostAsDirectMessageToFriend' )
__description__ = _("Microblogging with Twitter: send updates and show friends' tweets")
__version__ = "2010-02-04"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import urllib2
import time

import twitter as twitter

from kupfer import icons, pretty
from kupfer import plugin_support
from kupfer import kupferstring
from kupfer.objects import Action, TextLeaf, Source, Leaf, SourceLeaf
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.contacts import ContactLeaf, NAME_KEY
from kupfer.obj.special import PleaseConfigureLeaf
from kupfer.obj.helplib import background_loader


__kupfer_settings__ = plugin_support.PluginSettings(
	{
		'key': 'userpass',
		'label': '',
		'type': plugin_support.UserNamePassword,
		'value': '',
	},
	{
		'key': 'loadicons',
		'label': _("Load users' pictures"), 
		'type': bool,
		'value': True
	},
	{
		'key': 'loadtweets',
		'label': _("Load friends' public tweets"),
		'type': bool,
		'value': False,
	},
	{
		'key': 'loadtimeline',
		'label': _('Load timeline'),
		'type': bool,
		'value': False,
	}
)

MAX_STATUSES_COUNT = 10
MAX_TIMELINE_STATUSES_COUNT = MAX_STATUSES_COUNT * 2
TWITTER_USERNAME_KEY = 'twitter_username'

# friends
UPDATE_FR_INTERVAL_S = 20*60 # 15 min
UPDATE_FR_STARTUP_S = 7 #sec

# timeline
UPDATE_TL_START_S = 13 # sec
UPDATE_TL_INTERVAL_S = 15 * 60 # 20 min


def get_twitter_api():
	upass = __kupfer_settings__['userpass']
	api = None
	if upass:
		api = twitter.Api(username=upass.username, password=upass.password)
		api.SetXTwitterHeaders('Kupfer', '', __version__)
	return api


def send_direct_message(user, message):
	api = get_twitter_api()
	if api and user:
		api.PostDirectMessage(user, trunc_message(message))


def trunc_message(message):
	if len(message) > 140:
		message = message[:137] + '...'
	return message


def download_image(url):
	result = None
	try:
		f = urllib2.urlopen(url)
		result = f.read()
	except urllib2.HTTPError, err:
		pretty.print_error(__name__, 'download_image', url, err)
	return result


def _load_tweets(api, user, count):
	pretty.print_debug(__name__, '_load_tweets', user, count)
	try:
		if user:
			timeline = api.GetUserTimeline(user, count)
		else:
			timeline = api.GetFriendsTimeline(count=count)
		for status in timeline:
			text = kupferstring.tounicode(status.text)
			name = kupferstring.tounicode(status.user.name)
			yield StatusLeaf(text, name, status.relative_created_at, 
					status.id)
	except urllib2.HTTPError, err:
		pretty.print_error(__name__, '_load_tweets', user, count, err)


@background_loader(interval=UPDATE_FR_INTERVAL_S, name='twitter', 
		delay=UPDATE_FR_STARTUP_S)
def load_data():
	pretty.print_debug(__name__, 'load_data: start')
	start_time = time.time()
	api = get_twitter_api()
	result = []
	if api:
		for friend in api.GetFriends():
			image = None
			if __kupfer_settings__['loadicons']:
				image = download_image(friend.profile_image_url)
			screen_name = kupferstring.tounicode(friend.screen_name)
			name = kupferstring.tounicode(friend.name)
			fobj = Friend(screen_name, name, image)
			if __kupfer_settings__['loadtweets']:
				fobj.tweets = list(_load_tweets(api, friend.screen_name, 
						MAX_STATUSES_COUNT))
			result.append(fobj)
	else:
		confl = PleaseConfigureLeaf('microbloging_twitter', __kupfer_name__)
		result = [ confl ]

	pretty.print_debug(__name__, 'load_data: finished; load', len(result), 
			time.time()-start_time)
	return result


@background_loader(interval=UPDATE_TL_INTERVAL_S, name='twitter-timeline', 
		delay=UPDATE_TL_START_S)
def load_data_timeline():
	if not __kupfer_settings__['loadtimeline']:
		return None

	pretty.print_debug(__name__, 'load_data_timeline: start')
	start_time = time.time()
	api = get_twitter_api()

	result = None
	if api:
		result = list(_load_tweets(api, None, MAX_TIMELINE_STATUSES_COUNT))
	else:
		result = [PleaseConfigureLeaf('microbloging_twitter', __kupfer_name__)]

	pretty.print_debug(__name__, 'load_data_timeline: finished; load', 
			len(result), time.time()-start_time)
	return result


class FriendsTimeline(Leaf):
	rank_adjust = 15
	def __init__(self, tweets, name=_('<Friend Tweets>')):
		Leaf.__init__(self, tweets, name)
		self.tweets = self.object

	def has_content(self):
		return bool(self.object)

	def content_source(self, alternate=False):
		return FriendStatusesSource(self)

	def get_description(self):
		return _("All friends timeline")

	def get_icon_name(self):
		return 'twitter'


class Friend(ContactLeaf):
	grouping_slots = ContactLeaf.grouping_slots + (TWITTER_USERNAME_KEY, )
	def __init__(self, username, name, image=None):
		slots = {TWITTER_USERNAME_KEY: username, NAME_KEY: name}
		ContactLeaf.__init__(self, slots, name)
		self.kupfer_add_alias(username)
		self.image = image
		self.tweets = None

	def repr_key(self):
		return self.object[TWITTER_USERNAME_KEY]

	def has_content(self):
		return bool(self.tweets)

	def content_source(self, alternate=False):
		return FriendStatusesSource(self)

	def get_description(self):
		return self[TWITTER_USERNAME_KEY]

	def get_gicon(self):
		return icons.ComposedIconSmall(self.get_icon_name(), "twitter")

	def get_thumbnail(self, width, height):
		if self.image:
			return icons.get_pixbuf_from_data(self.image, width, height)
		return ContactLeaf.get_thumbnail(self, width, height)


class PostUpdate(Action):
	''' send update status '''
	def __init__(self):
		Action.__init__(self, _('Post Update to Twitter'))

	def activate(self, leaf):
		api = get_twitter_api()
		if api:
			api.PostUpdate(trunc_message(leaf.object))

	def item_types(self):
		yield TextLeaf

	def valid_for_item(self, item):
		return bool(item.object)

	def get_gicon(self):
		return icons.ComposedIcon("mail-message-new", "twitter")


class PostDirectMessage(Action):
	''' send direct message to contact '''
	def __init__(self):
		Action.__init__(self, _('Post Direct Message'))

	def activate(self, leaf, iobj):
		user = TWITTER_USERNAME_KEY in leaf and leaf[TWITTER_USERNAME_KEY]
		if iobj.object:
			send_direct_message(user, iobj.object)

	def item_types(self):
		yield ContactLeaf

	def valid_for_item(self, item):
		return TWITTER_USERNAME_KEY in item and item[TWITTER_USERNAME_KEY]

	def requires_object(self):
		return True

	def object_types(self):
		yield TextLeaf

	def get_gicon(self):
		return icons.ComposedIcon("mail-message-new", "twitter")


class PostAsDirectMessageToFriend(Action):
	''' send text to friend '''
	def __init__(self):
		Action.__init__(self, _('Post Direct Message To...'))

	def activate(self, leaf, iobj):
		user = TWITTER_USERNAME_KEY in iobj and iobj[TWITTER_USERNAME_KEY]
		send_direct_message(user, leaf.object)

	def item_types(self):
		yield TextLeaf

	def valid_for_item(self, item):
		return bool(item.object)

	def requires_object(self):
		return True

	def object_types(self):
		yield ContactLeaf

	def object_source(self, for_item=None):
		return FriendsSource()

	def get_gicon(self):
		return icons.ComposedIcon("mail-message-new", "twitter")


class PostReply(Action):
	''' send reply to the message '''
	def __init__(self):
		Action.__init__(self, _('Reply'))

	def activate(self, leaf, iobj):
		if iobj.object:
			api = get_twitter_api()
			message = trunc_message(iobj.object)
			api.PostUpdate(message, in_reply_to_status_id=leaf.status_id)

	def item_types(self):
		yield StatusLeaf

	def requires_object(self):
		return True

	def object_types(self):
		yield TextLeaf

	def get_gicon(self):
		return icons.ComposedIcon("mail-message-reply", "twitter")


class StatusLeaf(TextLeaf):
	def __init__(self, text, user, created_at, status_id):
		TextLeaf.__init__(self, text)
		self._description = _("%(user)s %(when)s") % dict(
				user=user, when=created_at)
		self.status_id = status_id

	def get_description(self):
		return self._description

	def get_actions(self):
		yield PostReply()


class InvisibleSourceLeaf (SourceLeaf):
	"""Hack to hide this source"""
	def is_valid(self):
		return False


class TimelineSource(Source):
	""" Source for main user timeline """
	def __init__(self, name=_("Twitter Timeline")):
		Source.__init__(self, name)

	def initialize(self):
		if self._is_valid():
			load_data_timeline.fill_cache(self.cached_items)
			load_data_timeline.bind_and_start(self.mark_for_update)

	def get_items(self):
		return load_data_timeline() or []

	def get_icon_name(self):
		return 'twitter'

	def provides(self):
		yield FriendsTimeline

	def get_leaf_repr(self):
		return None if self._is_valid() else InvisibleSourceLeaf(self) 

	def _is_valid(self):
		return __kupfer_settings__['loadtimeline']


class FriendsSource(ToplevelGroupingSource):
	def __init__(self, name=_('Twitter Friends')):
		super(FriendsSource, self).__init__(name, "Contacts")
		self._version = 1

	def initialize(self):
		ToplevelGroupingSource.initialize(self)
		load_data.fill_cache(self.cached_items)
		load_data.bind_and_start(self.mark_for_update)

	def get_items(self):
		return load_data() or []

	def get_icon_name(self):
		return 'twitter'

	def provides(self):
		yield ContactLeaf
		yield PleaseConfigureLeaf

	def should_sort_lexically(self):
		return True


class FriendStatusesSource(Source):
	def __init__(self, friend, name=_('Friend Statuses')):
		Source.__init__(self, name)
		self.friend = friend

	def get_items(self):
		return self.friend.tweets

	def get_icon_name(self):
		return 'twitter'

	def provides(self):
		yield StatusLeaf

	def should_sort_lexically(self):
		return False

	def has_parent(self):
		return True

	def get_parent(self):
		return self.friend
