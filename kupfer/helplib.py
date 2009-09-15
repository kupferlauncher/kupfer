"""
This module contains Helper constructs

This module is a part of the program Kupfer, see the main program file for
more information.
"""

import weakref

import gio

class PicklingHelperMixin (object):
	""" This pickling helper will define __getstate__/__setstate__
	acting simply on the class dictionary; it is up to the inheriting
	class to set up:
	pickle_prepare:
		Modify the instance dict to remove any unpickleable attributes,
		the resulting dict will be pickled
	unpickle_finish:
		Finish unpickling by restoring nonpickled attributes from the
		saved class dict, or setting up change callbacks or similar
	"""
	def pickle_prepare(self):
		pass
	def unpickle_finish(self):
		pass
	def __getstate__(self):
		"""On pickle, getstate will call self.pickle_prepare(),
		then it will return the class' current __dict__
		"""
		self.pickle_prepare()
		return self.__dict__

	def __setstate__(self, state):
		"""On unpickle, setstate will restore the class' __dict__,
		then call self.unpickle_finish()
		"""
		self.__dict__.update(state)
		self.unpickle_finish()

class NonpersistentToken (PicklingHelperMixin):
	"""A token will keep a reference until pickling, when it is deleted"""
	def __init__(self, data):
		self.data = data
	def __nonzero__(self):
		return self.data
	def pickle_prepare(self):
		self.data = None

class FilesystemWatchMixin (object):
	"""A mixin for Sources watching directories"""

	def monitor_directories(self, *directories):
		"""Register @directories for monitoring;

		On changes, the Source will be marked for update.
		This method returns a monitor token that has to be
		stored for the monitor to be active.

		The token will be a false value if nothing could be monitored.

		Nonexisting directories are skipped.
		"""
		tokens = []
		for directory in directories:
			gfile = gio.File(directory)
			if not gfile.query_exists():
				continue
			monitor = gfile.monitor_directory(gio.FILE_MONITOR_NONE, None)
			if monitor:
				monitor.connect("changed", self.__directory_changed)
				tokens.append(monitor)
		return NonpersistentToken(tokens)

	def monitor_include_file(self, gfile):
		"""Return whether @gfile should trigger an update event
		by default, files beginning with "." are ignored
		"""
		return not (gfile and gfile.get_basename().startswith("."))

	def __directory_changed(self, monitor, file1, file2, evt_type):
		if (evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
				gio.FILE_MONITOR_EVENT_DELETED) and
				self.monitor_include_file(file1)):
			self.mark_for_update()

class WeakCallback (object):
	"""A Weak Callback object that will keep a reference to
	the connecting object with weakref semantics.

	This allows object A to pass a callback method to object S,
	without object S keeping A alive.
	"""
	def __init__(self, mcallback):
		"""Create a new Weak Callback calling the method @mcallback"""
		obj = mcallback.im_self
		attr = mcallback.im_func.__name__
		self.wref = weakref.ref(obj, self.object_deleted)
		self.callback_attr = attr
		self.token = None

	def __call__(self, *args, **kwargs):
		obj = self.wref()
		if obj:
			attr = getattr(obj, self.callback_attr)
			attr(*args, **kwargs)
		else:
			self.default_callback(*args, **kwargs)

	def default_callback(self, *args, **kwargs):
		"""Called instead of callback when expired"""
		pass

	def object_deleted(self, wref):
		"""Called when callback expires"""
		pass

class DbusWeakCallback (WeakCallback):
	"""
	Will use @token if set as follows:
		token.remove()
	"""
	def object_deleted(self, wref):
		if self.token:
			self.token.remove()
			self.token = None

class GobjectWeakCallback (WeakCallback):
	"""
	Will use @token if set as follows:
		sender.disconnect(token)
	"""
	__senders = {}

	def object_deleted(self, wref):
		sender = self.__senders.pop(self.token, None)
		if sender:
			sender.disconnect(self.token)

	@classmethod
	def _connect(cls, sender, signal, mcallback, *user_args):
		# We save references to the sender in a class variable,
		# this is the only way to have it accessible when obj expires.
		wc = cls(mcallback)
		wc.token = sender.connect(signal, wc, *user_args)
		cls.__senders[wc.token] = sender

def gobject_connect_weakly(sender, signal, mcallback, *user_args):
	"""Connect weakly to GObject @sender's @signal,
	with a callback method @mcallback
	"""
	GobjectWeakCallback._connect(sender, signal, mcallback, *user_args)
