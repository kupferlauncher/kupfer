from __future__ import annotations

import sys
import traceback
import typing as ty
from time import time as timestamp

if ty.TYPE_CHECKING:
    from kupfer.support.types import ExecInfo

__all__ = (
    "OutputMixin",
    "print_debug",
    "print_error",
    "print_exc",
    "print_info",
    "timing_start",
    "timing_step",
)

DEBUG = False
COLORS = True

_COLOR_INFO = "\033[96m"
_COLOR_WARNING = "\033[93m"
_COLOR_FAIL = "\033[91m"
_COLOR_STD = "\033[0m"


class OutputMixin:
    """A mixin class providing prefixed output standard output and DEBUG output."""

    def _output_category(self) -> str:
        return f"[{type(self).__module__}] {type(self).__name__}:"

    def _output_core(
        self,
        prefix: str,
        sep: str,
        end: str,
        stream: ty.TextIO | None,
        *items: ty.Any,
    ) -> None:
        category = self._output_category()
        pitems = [
            item if isinstance(item, (str, int, float)) else repr(item)
            for item in items
        ]
        print(f"{prefix}{category}", *pitems, sep=sep, end=end, file=stream)

    def output_info(
        self, *items: ty.Any, sep: str = " ", end: str = "\n", **kwargs: ty.Any
    ) -> None:
        """Output given items using @sep as separator, ending the line with @end"""
        if COLORS:
            self._output_core(
                f"{_COLOR_INFO}INF{_COLOR_STD} ", sep, end, sys.stdout, *items
            )
        else:
            self._output_core("INF ", sep, end, sys.stdout, *items)

    def output_exc(self, exc_info: ExecInfo | None = None) -> None:
        """Output current exception, or use @exc_info if given"""
        etype, value, tback = exc_info or sys.exc_info()
        assert etype
        if DEBUG:
            if COLORS:
                self._output_core(
                    f"{_COLOR_FAIL}EXC{_COLOR_STD} ",
                    "",
                    "\n",
                    sys.stderr,
                )
            else:
                self._output_core("EXC ", "", "\n", sys.stderr)

            traceback.print_exception(etype, value, tback, file=sys.stderr)

            return

        msg = f"{etype.__name__}: {value}"
        if COLORS:
            self._output_core(
                f"{_COLOR_FAIL}EXC{_COLOR_STD} ",
                " ",
                "\n",
                sys.stderr,
                msg,
            )
        else:
            self._output_core("EXC ", " ", "\n", sys.stderr, msg)

    def output_debug(
        self, *items: ty.Any, sep: str = " ", end: str = "\n", **kwargs: ty.Any
    ) -> None:
        if DEBUG:
            self._output_core("DBG ", sep, end, sys.stderr, *items)

    def output_error(
        self, *items: ty.Any, sep: str = " ", end: str = "\n", **kwargs: ty.Any
    ) -> None:
        if COLORS:
            self._output_core(
                f"{_COLOR_WARNING}ERR{_COLOR_STD} ",
                sep,
                end,
                sys.stderr,
                *items,
            )
        else:
            self._output_core("ERR ", sep, end, sys.stderr, *items)


class _StaticOutput(OutputMixin):
    current_calling_module: str | None = None

    def _output_category(self) -> str:
        return f"[{self.current_calling_module}]:"

    def print_info(
        self, modulename: str, *args: ty.Any, **kwargs: ty.Any
    ) -> None:
        self.current_calling_module = modulename
        self.output_info(*args, **kwargs)

    def print_error(
        self, modulename: str, *args: ty.Any, **kwargs: ty.Any
    ) -> None:
        self.current_calling_module = modulename
        self.output_error(*args, **kwargs)

    def print_exc(
        self, modulename: str, *args: ty.Any, **kwargs: ty.Any
    ) -> None:
        self.current_calling_module = modulename
        self.output_exc(*args, **kwargs)

    def print_debug(
        self, modulename: str, *args: ty.Any, **kwargs: ty.Any
    ) -> None:
        if DEBUG:
            self.current_calling_module = modulename
            self.output_debug(*args, **kwargs)


_StaticOutputInst = _StaticOutput()

print_info = _StaticOutputInst.print_info
print_debug = _StaticOutputInst.print_debug
print_error = _StaticOutputInst.print_error
print_exc = _StaticOutputInst.print_exc


def timing_start() -> float | None:
    """In debug get current timestamp; return None otherwise"""
    if DEBUG:
        return timestamp()

    return None


def timing_step(
    modulename: str, start: float | None, label: str, *args: str
) -> float | None:
    """In debug printtime from `start`."""
    if DEBUG and start:
        cts = timestamp()
        print_debug(modulename, label, f"in {cts - start:.6f} s", *args)
        return cts

    return None
