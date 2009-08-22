from kupfer import scheduler, pretty

class Task (object):
	"""Represent a task that can be done in the background"""
	def __init__(self, name):
		self.name = name

	def run(self):
		raise NotImplementedError

class StepTask (Task):
	"""A step task runs a part of the task in StepTask.step,
	doing final cleanup in StepTask.finish, which is guaranteed to
	be called regardless of exit or failure mode
	"""
	def step(self):
		pass
	def finish(self):
		pass
	def run(self):
		try:
			while True:
				if not self.step():
					break
				yield
		finally:
			self.finish()


def _step_task(task):
	try:
		task.next()
	except StopIteration:
		return False
	else:
		return True

class TaskRunner (pretty.OutputMixin):
	"""Run Tasks in the idle Loop"""
	def __init__(self, end_on_finish):
		scheduler.GetScheduler().connect("finish", self._on_finish)
		self.task_iters = []
		self.timer = scheduler.Timer(True)
		self.end_on_finish = end_on_finish
	def add_task(self, task):
		"""Register @task to be run"""
		self.task_iters.append(task.run())
		self.timer.set_idle(self._step_tasks)
	def _step_tasks(self):
		for task in list(self.task_iters):
			if not _step_task(task):
				self.output_debug("Task done:", task)
				self.task_iters.remove(task)
		if self.task_iters:
			self.timer.set_idle(self._step_tasks)

	def _on_finish(self, sched):
		if self.end_on_finish:
			del self.task_iters[:]

