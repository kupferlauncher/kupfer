# -*- encoding: UTF-8 -*-
"""
Classes used to provide grouping leaves mechanism.
"""
import copy
import time
import weakref

from kupfer.objects import Leaf, Source

__author__ = ("Karol Będkowski <karol.bedkowsk+gh@gmail.com>, "
              "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>" )


EMAIL_KEY = "EMAIL"
NAME_KEY = "NAME"

CONTACTS_CATEGORY = "Contacts"
HOSTS_CATEGORY = "Hosts"

class GroupingLeaf (Leaf):
	"""
	A Leaf that groups with other leaves inside Grouping Sources

	The represented object of a GroupedLeaf is a
	dictionary of (slot, value) pairs, where
	slot identifies the slot, and the value is something that
	must be equal to be grouped.
	"""
	def __init__(self, obj, name):
		Leaf.__init__(self, obj, name)
		self.links = [self]

	def slots(self):
		return self.object

	def has_content(self):
		return len(self.links) > 1

	def content_source(self, alternate=False):
		return _GroupedItemsSource(self)

	def __len__(self):
		return len(self.links)

	def __contains__(self, key):
		"Return True if GroupedLeaf has value for @key"
		return any(key in leaf.object for leaf in self.links)

	def __getitem__(self, key):
		"Return iterator of all values for @key"
		return [leaf.object[key] for leaf in self.links if key in leaf.object]

class GroupingSource (Source):
	grouping_keys = [EMAIL_KEY, NAME_KEY]

	def __init__(self, name, sources):
		Source.__init__(self, name)
		self.sources = sources
		print "making", self

	def get_leaves(self, force_update=False):
		st = time.time()
		self.output_debug("START")

		# map (slot, value) -> group
		groups = {}
		for src in self.sources:
			self.output_debug("Merging", src)
			leaves = Source.get_leaves(src, force_update)
			for leaf in leaves:
				try:
					slots = leaf.slots()
				except AttributeError:
					# Let through Non-grouping leaves
					yield leaf
					continue
				for slot in self.grouping_keys:
					slots = leaf.slots()
					if slot not in slots:
						continue
					groups.setdefault((slot, slots[slot]), set()).add(leaf)

		def merge_groups(key1, key2):
			if groups[key1] is groups[key2]:
				return
			print "Merging", key1, "and", key2
			groups[key1].update(groups[key2])
			groups[key2] = groups[key1]

		# Find all values that have more than one value
		# and we merge those groups
		for (slot, value), leaves in groups.iteritems():
			#leaves = slotdicts[slot][value]
			if len(leaves) <= 1:
				continue
			for leaf in list(leaves):
				for slot2 in self.grouping_keys:
					for value2 in leaf[slot2]:
						merge_groups((slot, value), (slot2, value2))

		idset = set()
		for group in groups.itervalues():
			if id(group) in idset:
				continue
			idset.add(id(group))
			leaf = self._make_group_leader(group)
			yield leaf
		self.output_debug("END", time.time() - st)

	@classmethod
	def _make_group_leader(cls, leaves):
		obj = copy.copy(iter(leaves).next())
		obj.links = list(leaves)
		obj.name_aliases = set(obj.name_aliases)
		for other in leaves:
			if other is not obj:
				obj.name_aliases.add(unicode(other))
				# adding the other's aliases can be misleading
				# since the matched email address might not be
				# what we are e-mailing
				# obj.name_aliases.update(other.name_aliases)
		obj.name_aliases.discard(unicode(obj))
		return obj

class ToplevelGroupingSource (GroupingSource):
	"""
	Sources of this type group their leaves with others in the toplevel
	of the catalog.
	"""
	_sources = {}

	def __init__(self, name, category):
		GroupingSource.__init__(self, name, [self])
		self.category = category

	def toplevel_source(self):
		sources = self._sources[self.category].keys()
		return GroupingSource(self.category, sources)

	def initialize(self):
		if not self.category in self._sources:
			self._sources[self.category] = weakref.WeakKeyDictionary()
		self._sources[self.category][self] = 1
		self.output_debug("Register %s source %s" % (self.category, self))

class _GroupedItemsSource(Source):
	def __init__(self, leaf):
		Source.__init__(self, unicode(leaf))
		self._leaf = leaf

	def get_items(self):
		for leaf in self._leaf.links:
			yield leaf

class ContactLeaf(GroupingLeaf):
	def get_icon_name(self):
		return "stock_person"


class HostLeaf(GroupingLeaf):
	def get_icon_name(self):
		return "stock_host"


