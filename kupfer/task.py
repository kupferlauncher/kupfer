import threading

from kupfer import scheduler, pretty

class Task (object):
	"""Represent a task that can be done in the background"""
	def __init__(self, name):
		self.name = name

	def is_thread(self):
		return False

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

class ThreadTask (Task, threading.Thread):
	"""Run in a thread"""
	def __init__(self, name):
		Task.__init__(self, name)
		threading.Thread.__init__(self)
		self.__thread_done = False
		self.__thread_started = False

	def is_thread(self):
		return True

	def thread_do(self):
		"""Override this to run what should be done in the thread"""
		raise NotImplementedError

	def __thread_run(self):
		try:
			self.__retval = self.thread_do()
		finally:
			self.__thread_done = True

	def run(self):
		while True:
			if not self.__thread_started:
				# swizzle the methods for Thread
				self.run = self.__thread_run
				self.start()
				self.__thread_started = True
			elif self.__thread_done:
				return
			yield

class TaskRunner (pretty.OutputMixin):
	"""Run Tasks in the idle Loop"""
	def __init__(self, end_on_finish):
		self.task_iters = []
		self.thread_iters = []
		self.idle_timer = scheduler.Timer(True)
		if end_on_finish:
			scheduler.GetScheduler().connect("finish", self._finish_cleanup)

	def add_task(self, task):
		"""Register @task to be run"""
		if task.is_thread():
			# start thread
			thread = task.run()
			self.thread_iters.append(thread)
			# run through all threads
			self._step_tasks(self.thread_iters)
		else:
			self.task_iters.append(task.run())
		self._setup_timers()

	def _setup_timers(self):
		if self.task_iters:
			self.idle_timer.set_idle(self._step_tasks, self.task_iters)

	def _step_tasks(self, tasks):
		for task in list(tasks):
			try:
				task.next()
			except StopIteration:
				self.output_debug("Task done:", task)
				tasks.remove(task)
		self._setup_timers()

	def _finish_cleanup(self, sched):
		del self.task_iters[:]
		del self.thread_iters[:]

