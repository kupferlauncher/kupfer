import sys
import gobject

from kupfer import data
from kupfer import objects
from kupfer import extensions
import debug

class Test (object):
	def __init__(self, dc):
		dc.connect("search-result", self.got_result)
		dc.connect("predicate-result", self.got_predicates)
		dc.connect("launched-action", self.cont)
		self.Leaf = None
		self.Action = None
		self.dc = dc

	def cont(self, sender, leaf, action):
		gobject.idle_add(self.loop)

	def got_predicates(self, sender, result, matchview, ctx):
		for m in reversed(list(matchview)):
			print m
		if result:
			self.Action = result.object
		gobject.idle_add(self.loop)

	def got_result(self, sender, result, matchview, ctx):
		for m in reversed(list(matchview)):
			print m
		obj = result and result.object or None
		self.Leaf = obj
		print obj
		gobject.idle_add(self.loop)

	def loop(self):
		try:
			key = raw_input("kupfer> ")
		except EOFError:
			raise SystemExit
		key = key.lower()
		parts = key.split(" ", 1)
		if self.Leaf and parts[0] == "a":
			if len(parts) > 1:
				key = parts[1]
			else:
				key = None
			dc.search_predicate(self.Leaf, key)
		elif key == "x" and self.Action:
			gobject.idle_add(self.dc.eval_action, self.Leaf, self.Action)
		else:
			self.Leaf = None
			self.Action = None
			dc.search(key)
		print self.Leaf, self.Action

def waiting(msg):
	print msg
	return True

if __name__ == '__main__':
	import readline
	srcs = []
	srcs.append(objects.FileSource(["/home/ulrik",], depth=1))
	srcs.append(objects.AppSource())
	srcs.append(extensions.screen.ScreenSessionsSource())
	if len(srcs) == 1:
		src = srcs[0]
	else:
		src = objects.MultiSource(srcs)
	dc = data.DataController(src)
	print dc
	gobject.threads_init()
	gobject.set_application_name("kupfer-mini")
	t = Test(dc)

	gobject.idle_add(t.loop)
	ml = gobject.MainLoop()
	ml.run()
