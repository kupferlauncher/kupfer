import sys
import threading

import gobject

from kupfer import scheduler, pretty

class Task (object):
	"""Represent a task that can be done in the background"""
	def __init__(self, name=None):
		self.name = name

	def __unicode__(self):
		return self.name

	def start(self, finish_callback):
		raise NotImplementedError

class ThreadTask (Task):
	"""Run in a thread"""
	def __init__(self, name=None):
		Task.__init__(self, name)
		self._finish_callback = None

	def thread_do(self):
		"""Override this to run what should be done in the thread"""
		raise NotImplementedError

	def thread_finish(self):
		"""This finish function runs in the main thread after thread
		completion, and can be used to communicate with the GUI.
		"""
		pass

	def thread_finally(self, exc_info):
		"""Always run at thread finish"""
		pass

	def _thread_finally(self, exc_info):
		try:
			self.thread_finally(exc_info)
		finally:
			self._finish_callback(self)

	def _run_thread(self):
		try:
			self.thread_do()
			gobject.idle_add(self.thread_finish)
		except:
			exc_info = sys.exc_info()
			raise
		else:
			exc_info = None
		finally:
			gobject.idle_add(self._thread_finally, exc_info)

	def start(self, finish_callback):
		self._finish_callback = finish_callback
		thread = threading.Thread(target=self._run_thread)
		thread.start()


class TaskRunner (pretty.OutputMixin):
	"""Run Tasks in the idle Loop"""
	def __init__(self, end_on_finish):
		self.tasks = set()
		self.end_on_finish = end_on_finish
		scheduler.GetScheduler().connect("finish", self._finish_cleanup)

	def _task_finished(self, task):
		self.output_debug("Task finished", task)
		self.tasks.remove(task)

	def add_task(self, task):
		"""Register @task to be run"""
		self.tasks.add(task)
		task.start(self._task_finished)

	def _finish_cleanup(self, sched):
		if self.end_on_finish:
			self.tasks.clear()
			return
		if self.tasks:
			self.output_info("Uncompleted tasks:")
			for task in self.tasks:
				self.output_info(task)


class _BackgroundTask (ThreadTask):
	def __init__(self, job, name, result_callback, error_callback):
		ThreadTask.__init__(self, name)
		self.job = job
		self.result_callback = result_callback
		self.error_callback = error_callback
		self.error_occurred = True

	def thread_do(self):
		ret = self.job()
		self.error_occurred = False
		gobject.idle_add(self.result_callback, ret)

	def thread_finally(self, exc_info):
		if exc_info:
			self.error_callback(exc_info)


class BackgroundTaskRunner(pretty.OutputMixin):
	""" Background job for load some data and cache it. """

	def __init__(self, job, interval, delay=10, name=None):
		""" Constr.

		@job: function to run
		@interval: time between reloading data (run job function, in seconds)
		@delay: startup delay in second
		@name: name of thread
		"""
		self.name = name or repr(job)
		# function to run
		self._job = job
		self.interval = interval
		# optional interval after error running job
		self.interval_after_error = interval
		self.startup_delay = delay
		# function called after run job
		self.result_callback = None
		self.error_callback = None
		self.next_run_timer = scheduler.Timer()
		self._active = False

	def start(self):
		''' Start thread.'''
		self.output_info('Start task', self.name,
				'delay:', self.startup_delay,
				'interval:', self.interval)
		self._active = True
		self.next_run_timer.set(self.startup_delay, self._run)

	@property
	def is_running(self):
		return not self.next_run_timer.is_valid()

	def _task_finished(self, task):
		if not self._active:
			# task is stoped
			return
		# wait for next run
		interval = (self.interval_after_error if task.error_occurred
				else self.interval)
		self.next_run_timer.set(interval, self._run)

	def _run(self):
		self.output_debug('_run task', self.name)
		task = _BackgroundTask(self._job, self.name, self.result_callback,
				self.error_callback)
		task.start(self._task_finished)

	def activate(self):
		''' Force run job (break waiting phase). '''
		if not self.is_running:
			self.next_run_timer.set(0, self._run)

	def stop(self):
		''' Stop background task '''
		self.output_info('Stop task', self.name)
		self._active = False
		self.next_run_timer.invalidate()

