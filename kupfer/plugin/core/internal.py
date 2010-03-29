
from kupfer.objects import Source
from kupfer.objects import RunnableLeaf
from kupfer import commandexec

__kupfer_sources__ = ("KupferInterals", "CommandResults", )
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class LastCommand (RunnableLeaf):
	"Represented object is the command tuple to run"
	qf_id = "lastcommand"
	def __init__(self, obj):
		RunnableLeaf.__init__(self, obj, _("Last Command"))

	def run(self):
		ctx = commandexec.DefaultActionExecutionContext()
		obj, action, iobj = self.object
		return ctx.run(obj, action, iobj, delegate=True)

class KupferInterals (Source):
	def __init__(self):
		Source.__init__(self, _("Internal Kupfer Objects"))
	def is_dynamic(self):
		return True
	def get_items(self):
		ctx = commandexec.DefaultActionExecutionContext()
		if ctx.last_command is None:
			return
		yield LastCommand(ctx.last_command)
	def provides(self):
		yield LastCommand

class CommandResults (Source):
	def __init__(self):
		Source.__init__(self, _("Command Results"))
	def is_dynamic(self):
		return True
	def get_items(self):
		ctx = commandexec.DefaultActionExecutionContext()
		for x in reversed(ctx.last_results):
			yield x
	def provides(self):
		return ()
