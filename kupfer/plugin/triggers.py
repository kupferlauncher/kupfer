import gtk


from kupfer import keybindings

from kupfer.objects import Leaf, Action, Source, TextSource
from kupfer.objects import ComposedLeaf, TextLeaf, RunnableLeaf
from kupfer import puid

__kupfer_name__ = _("Triggers")
__kupfer_sources__ = ("Triggers", )
__kupfer_actions__ = (
	"AddTrigger",
)
__description__ = _("Assign global keybindings (triggers) to objects created "
                    "with 'Compose Command' (Ctrl+R).")
__version__ = "2009-12-30"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

# we import the keybinder module for its side-effects --
# this plugin needs this module, lest it shall not function.
import keybinder

_PRIVATE_KEYBINDING_MASK = 0xFF00

class Trigger (RunnableLeaf):
	def get_actions(self):
		for act in RunnableLeaf.get_actions(self):
			yield act
		yield RemoveTrigger()
	def run(self):
		Triggers.perform_trigger(self.object)

class Triggers (Source):
	instance = None

	def __init__(self):
		Source.__init__(self, _("Triggers"))
		self.trigger_table = {}
	
	def initialize(self):
		Triggers.instance = self
		keybindings.GetKeyboundObject().connect("keybinding", self._callback)
		for target, (keystr, name, id_) in self.trigger_table.iteritems():
			keybindings.bind_key(keystr, target)
		self.output_debug(self.trigger_table)

	def _callback(self, keyobj, target, event_time):
		self.perform_trigger(target)

	def get_items(self):
		for target, (keystr, name, id_) in self.trigger_table.iteritems():
			label = gtk.accelerator_get_label(*gtk.accelerator_parse(keystr))
			yield Trigger(target, u"%s (%s)" % (label or keystr, name))

	def should_sort_lexically(self):
		return True

	@classmethod
	def perform_trigger(cls, target):
		try:
			keystr, name, id_ = cls.instance.trigger_table[target]
		except KeyError:
			return
		obj = puid.resolve_unique_id(id_)
		if obj is None:
			return
		obj.run()

	@classmethod
	def add_trigger(cls, leaf, keystr):
		Triggers.instance._add_trigger(leaf, keystr)

	@classmethod
	def remove_trigger(cls, target):
		Triggers.instance._remove_trigger(target)
	
	def _add_trigger(self, leaf, keystr):
		X = _PRIVATE_KEYBINDING_MASK
		for target in xrange(X, X + 1000):
			if target not in self.trigger_table:
				break
		keybindings.bind_key(keystr, target)
		name = unicode(leaf)
		self.trigger_table[target] = (keystr, name, puid.get_unique_id(leaf))
		self.mark_for_update()

	def _remove_trigger(self, target):
		self.trigger_table.pop(target, None)
		keybindings.bind_key(None, target)
		self.mark_for_update()

	def get_icon_name(self):
		return "key_bindings"

def _accelerator_label(keystr):
	return gtk.accelerator_get_label(*gtk.accelerator_parse(keystr))

def _valid_accelerator(keystr):
	val, mod = gtk.accelerator_parse(keystr)
	return val or mod

class AcceleratorSuggestionsSource (TextSource):
	def __init__(self):
		TextSource.__init__(self, _("Triggers"))

	def get_text_items(self, text):
		if not text or not _valid_accelerator(text):
			return
		pfix = ["<Ctrl><Alt>", "<Ctrl><Shift>", "<Ctrl><Alt><Shift>", "<Super>"]
		texts = [text] + [p + text for p in pfix]
		for accel in texts:
			if not _valid_accelerator(accel):
				continue
			yield TextLeaf(accel, _accelerator_label(accel))

	def get_items(self, text):
		return self.get_text_items(text)

	def provides(self):
		yield TextLeaf

class AddTrigger (Action):
	def __init__(self):
		Action.__init__(self, _("Add Trigger..."))
	
	def activate(self, leaf, iobj):
		Triggers.add_trigger(leaf, iobj.object)

	def item_types(self):
		yield ComposedLeaf

	def requires_object(self):
		return True
	def object_types(self):
		yield TextLeaf
	def object_source(self, for_item=None):
		return AcceleratorSuggestionsSource()

	def valid_object(self, iobj, for_item=None):
		return len(iobj.object) > 1 and _valid_accelerator(iobj.object)

	def get_icon_name(self):
		return "list-add"

class RemoveTrigger (Action):
	def __init__(self):
		Action.__init__(self, _("Remove Trigger"))

	def activate(self, leaf):
		Triggers.remove_trigger(leaf.object)

	def get_icon_name(self):
		return "list-remove"

