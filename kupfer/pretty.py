

debug = False

import sys
import traceback
from time import time as timestamp

class OutputMixin (object):
    """
    A mixin class providing prefixed output
    standard output and debug output
    """
    def _output_category(self):
        return "[%s] %s:" % (type(self).__module__, type(self).__name__)

    def _output_core(self, prefix, sep, end, stream, *items):
        category = self._output_category()
        print(prefix+category, *items, sep=sep, end=end, file=stream)

    def output_info(self, *items, **kwargs):
        """
        Output given items using @sep as separator,
        ending the line with @end
        """
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        self._output_core("", sep, end, sys.stdout, *items)

    def output_exc(self, exc_info=None):
        """Output current exception, or use @exc_info if given"""
        etype, value, tb = (exc_info or sys.exc_info())
        if debug:
            self._output_core("Exception in ", "", "\n", sys.stderr)
            traceback.print_exception(etype, value, tb, file=sys.stderr)
        else:
            msg = "%s: %s" % (etype.__name__, value)
            self._output_core("Exception in ", " ", "\n", sys.stderr, msg)

    def output_debug(self, *items, **kwargs):
        if debug:
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")
            self._output_core("D ", sep, end, sys.stderr, *items)

    def output_error(self, *items, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        self._output_core("Error ", sep, end, sys.stderr, *items)

class _StaticOutput (OutputMixin):
    current_calling_module = None
    def _output_category(self):
        return "[%s]:" % (self.current_calling_module, )

    def print_info(self, modulename, *args, **kwargs):
        self.current_calling_module = modulename
        self.output_info(*args, **kwargs)

    def print_error(self, modulename, *args, **kwargs):
        self.current_calling_module = modulename
        self.output_error(*args, **kwargs)

    def print_exc(self, modulename, *args, **kwargs):
        self.current_calling_module = modulename
        self.output_exc(*args, **kwargs)

    def print_debug(self, modulename, *args, **kwargs):
        if debug:
            self.current_calling_module = modulename
            self.output_debug(*args, **kwargs)
_StaticOutput = _StaticOutput()

print_info = _StaticOutput.print_info
print_debug = _StaticOutput.print_debug
print_error = _StaticOutput.print_error
print_exc = _StaticOutput.print_exc


def timing_start():
    if debug:
        return [timestamp()]
    else:
        return None

def timing_step(modulename, start, label):
    if debug:
        t = timestamp()
        print_debug(modulename, label, "in %.6f s" % (t - start[0], ))
        start[0] = t
