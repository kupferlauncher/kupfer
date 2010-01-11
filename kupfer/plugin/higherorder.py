from kupfer.objects import Action, Leaf

__kupfer_name__ = _("Higher-order Actions")
__kupfer_actions__ = (
	"Select",
)
__description__ = _("Tools to work with Kupfer commands as objects")
__version__ = "2010-01-11"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class Select (Action):
	rank_adjust = -15
	def __init__(self):
		Action.__init__(self, _("Select in Kupfer"))

	def has_result(self):
		return True
	def activate(self, leaf):
		return leaf
	def item_types(self):
		yield Leaf
