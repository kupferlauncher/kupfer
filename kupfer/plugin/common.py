from kupfer.objects import Leaf, Action, Source

import gtk

class RunnableLeaf (Leaf):
	def __init__(self, obj=None, name=None):
		super(RunnableLeaf, self).__init__(obj, name)
	def get_actions(self):
		yield Run()
	def run(self):
		pass

class Quit (RunnableLeaf):
	def run(self):
		gtk.main_quit()
	def get_description(self):
		return "Quit Kupfer"
	def get_icon_name(self):
		return gtk.STOCK_QUIT

class Run (Action):
	def activate(self, leaf):
		print leaf
		leaf.run()
	def get_icon_name(self):
		return gtk.STOCK_EXECUTE

class CommonSource (Source):
	def __init__(self, name="Special items"):
		super(CommonSource, self).__init__(name)
	def is_dynamic(self):
		return True
	def get_items(self):
		yield Quit()
	def get_icon_name(self):
		return "emblem-system"
