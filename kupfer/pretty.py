debug = False

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
		debug = kwargs.get("debug", False)
		stritems = (str(it) for it in items)
		sformat = "[%s] %s: %s%s" if debug else "[[%s]] %s: %s%s"
		try:
			output = sformat % (type(self).__module__,
					type(self).__name__, sep.join(stritems), end)
		except Exception:
			output = sep.join(stritems) + end
		print output,

	def output_debug(self, *items, **kwargs):
		if debug:
			kwargs["debug"] = True
			self.output_info(*items, **kwargs)

def print_info(name, *items, **kwargs):
	"""
	Output given items using @sep as separator,
	ending the line with @end
	"""
	sep = kwargs.get("sep", " ")
	end = kwargs.get("end", "\n")
	debug = kwargs.get("debug", False)
	stritems = (str(it) for it in items)
	sformat = "[%s]: %s%s" if debug else "[[%s]]: %s%s"
	print sformat % (name, sep.join(stritems), end),

def print_debug(name, *items, **kwargs):
	if debug:
		kwargs["debug"] = True
		print_info(name, *items, **kwargs)
