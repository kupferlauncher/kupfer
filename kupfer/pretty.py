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
		stritems = (str(it) for it in items)
		try:
			output = "[%s] %s: %s%s" % (type(self).__module__,
					type(self).__name__, sep.join(stritems), end)
		except Exception:
			output = sep.join(stritems) + end
		print output,

	def output_debug(self, *items, **kwargs):
		if debug:
			self.output_info(*items, **kwargs)

