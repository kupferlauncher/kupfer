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
		dc.connect("new-source", self.cont)
		self.Leaf = None
		self.Action = None
		self.dc = dc
		self.waiting = []

	def cont(self, *args, **kwargs):
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
		gobject.idle_add(self.loop)

	def wait(self, context=None):
		ret = gobject.timeout_add_seconds(2, self._waited, context)
		self.waiting.append(ret)

	def _waited(self, context=None):
		if self.waiting:
			print "No response"
			self.loop()

	def loop(self):
		# clear waiting state
		for ret in self.waiting:
			gobject.source_remove(ret)
		del self.waiting[:]

		if self.Leaf:
			print "%s -- %s" % (self.Leaf, self.Action)
			print '"%s"' % self.Leaf.get_description()
		try:
			key = raw_input("kupfer> ")
		except EOFError:
			raise SystemExit
		key = key.lower().strip()
		if key == "//" and self.Action:
			gobject.idle_add(self.dc.eval_action, self.Leaf, self.Action)
		elif self.Leaf and key and key[0] == "/":
			key = key[1:]
			if key == "/": key = ""
			dc.search_predicate(self.Leaf, key)
		elif key == "<":
			dc.browse_up()
		elif key == ">" and self.Leaf:
			dc.browse_down(self.Leaf)
		else:
			self.Leaf = None
			self.Action = None
			dc.search(key)
		self.wait()

def waiting(msg):
	print msg
	return True

if __name__ == '__main__':
	import readline
	srcs = []
	srcs.append(objects.FileSource(["/home/ulrik",], depth=1))
	srcs.append(objects.AppSource())
	srcs.append(extensions.screen.ScreenSessionsSource())
	dc = data.DataController()
	dc.set_sources(srcs, [])
	print dc
	gobject.threads_init()
	gobject.set_application_name("kupfer-mini")
	t = Test(dc)

	gobject.idle_add(t.loop)
	ml = gobject.MainLoop()
	ml.run()
