"""
This module contains Helper constructs

This module is a part of the program Kupfer, see the main program file for
more information.
"""

import weakref

class WeakCallback (object):
	"""A Weak Callback object that will keep a reference to
	the connecting object with weakref semantics.

	This allows to connect to gobject signals without it keeping
	the connecting object alive forever.
	"""
	def __init__(self, obj, attr):
		"""Create a new Weak Callback calling the method @obj.@attr"""
		self.wref = weakref.ref(obj)
		self.callback_attr = attr

	def __call__(self, *args, **kwargs):
		obj = self.wref()
		if obj:
			attr = getattr(obj, self.callback_attr)
			attr(*args, **kwargs)
		else:
			self.default_callback(*args, **kwargs)

	def default_callback(self, *args, **kwargs):
		"""The default callback will replace
		the callback if the object is deleted
		"""
		pass

