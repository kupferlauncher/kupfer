debug = False

import functools

class OutputMixin (object):
	"""
	A mixin class providing prefixed output
	standard output and debug output
	"""
	def output_info(self, *items, **kwargs):
		"""
		Output given items using @sep as separator,
		ending the line with @end
		"""
		sep = kwargs.get("sep", " ")
		end = kwargs.get("end", "\n")
		category = kwargs.get("category", "")
		stritems = (str(it) for it in items)
		sformat = "%s[%s] %s: %s%s"
		try:
			output = sformat % (category, type(self).__module__,
					type(self).__name__, sep.join(stritems), end)
		except Exception:
			output = sep.join(stritems) + end
		print output,

	def output_debug(self, *items, **kwargs):
		if debug:
			self.output_info(category="D ", *items, **kwargs)
	def output_error(self, *items, **kwargs):
		self.output_info(category="Error ", *items, **kwargs)

def print_info(name, *items, **kwargs):
	"""
	Output given items using @sep as separator,
	ending the line with @end
	"""
	sep = kwargs.get("sep", " ")
	end = kwargs.get("end", "\n")
	category = kwargs.get("category", "")
	stritems = (str(it) for it in items)
	sformat = "%s[%s]: %s%s"
	print sformat % (category, name, sep.join(stritems), end),

def print_debug(name, *items, **kwargs):
	if debug:
		print_info(name, category="D ", *items, **kwargs)

def print_error(name, *items, **kwargs):
	print_info(name, category="Error ", *items, **kwargs)
