from __future__ import division

import cmath
import math

from kupfer.objects import Source, Action, TextLeaf
from kupfer import pretty

__kupfer_name__ = _("Calculator")
__kupfer_actions__ = ("Calculate", )
__description__ = _("Calculate expressions starting with '='")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class IgnoreResultException (Exception):
	pass

class KupferSurprise (float):
	def __call__(self, *args):
		from kupfer import utils, version
		utils.show_url(version.WEBSITE)
		raise IgnoreResultException

class Help (object):
	def __call__(self):
		import textwrap

		from kupfer import uiutils

		environment = dict(math.__dict__)
		environment.update(cmath.__dict__)
		docstrings = []
		for attr in sorted(environment):
			if attr.startswith("_"):
				continue
			val = environment[attr]
			if not callable(val):
				docstrings.append("%s = %s" % (attr, val))
				continue
			try:
				docstrings.append(val.__doc__)
			except AttributeError:
				pass
		formatted = []
		maxlen = 72
		left_margin = 4
		for docstr in docstrings:
			# Wrap the description and align continued lines
			docsplit = docstr.split("\n", 1)
			if len(docsplit) < 2:
				formatted.append(docstr)
				continue
			wrapped_lines = textwrap.wrap(docsplit[1], maxlen - left_margin)
			wrapped = (u"\n" + u" "*left_margin).join(wrapped_lines)
			formatted.append("%s\n    %s" % (docsplit[0], wrapped))
		uiutils.show_text_result("\n\n".join(formatted), _("Calculator"))
		raise IgnoreResultException

	def __complex__(self):
		return self()

def format_result(res):
	cres = complex(res)
	parts = []
	if cres.real:
		parts.append(u"%s" % cres.real)
	if cres.imag:
		parts.append(u"%s" % complex(0, cres.imag))
	return u"+".join(parts) or u"%s" % res

class Calculate (Action):
	# since it applies only to special queries, we can up the rank
	rank_adjust = 10
	def __init__(self):
		Action.__init__(self, _("Calculate"))
		self.last_result = None

	def has_result(self):
		return True
	def activate(self, leaf):
		expr = leaf.object.lstrip("= ")

		# try to add missing parantheses
		brackets_missing = expr.count("(") - expr.count(")")
		if brackets_missing > 0:
			expr += ")"*brackets_missing

		environment = dict(math.__dict__)
		environment.update(cmath.__dict__)
		# define some constants missing
		if self.last_result is not None:
			environment["_"] = self.last_result
		environment["help"] = Help()
		environment["kupfer"] = KupferSurprise("inf")
		# make the builtins inaccessible
		environment["__builtins__"] = {}

		pretty.print_debug(__name__, "Evaluating", repr(expr))
		try:
			result = eval(expr, environment)
			resultstr = format_result(result)
			self.last_result = result
		except IgnoreResultException:
			return
		except Exception, exc:
			pretty.print_error(__name__, type(exc).__name__, exc)
			resultstr = unicode(exc)
		return TextLeaf(resultstr)

	def item_types(self):
		yield TextLeaf
	def valid_for_item(self, leaf):
		text = leaf.object
		return text and text.startswith("=")

	def get_description(self):
		return None
