__kupfer_name__ = _("Calculator")
__kupfer_actions__ = ("Calculate",)
__description__ = _("Calculate mathematical expressions")
__version__ = "2017.1"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import cmath
import inspect
import math
import textwrap
import typing as ty
from contextlib import suppress

from kupfer import launch, version
from kupfer.obj import Action, TextLeaf
from kupfer.support import pretty
from kupfer.ui import uiutils

if ty.TYPE_CHECKING:
    from gettext import gettext as _


class IgnoreResultError(Exception):
    pass


class KupferSurprise(float):
    """kupfer

    cleverness to the inf**inf
    """

    def __call__(self, *args):
        launch.show_url(version.WEBSITE)
        raise IgnoreResultError


# pylint: disable=too-few-public-methods
class DummyResult:
    def __str__(self):
        return "<Result of last expression>"


class Help:
    """help()

    Show help about the calculator
    """

    def __call__(self):
        environment = make_environment(last_result=DummyResult())
        docstrings = []
        for attr in sorted(environment):
            if attr != "_" and attr.startswith("_"):
                continue

            val = environment[attr]
            if not callable(val):
                docstrings.append(f"{attr} = {val}")
                continue

            with suppress(AttributeError):
                try:
                    # use .replace() to remove unimportant '/' marker in signature
                    sig = str(inspect.signature(val)).replace(", /)", ")")
                    doc = f"{attr}{sig}\n{val.__doc__}"
                except ValueError:
                    doc = val.__doc__

                docstrings.append(doc)

        formatted = []
        maxlen = 72
        left_margin = 4
        for docstr in docstrings:
            # Wrap the description and align continued lines
            docsplit = docstr.split("\n", 1)
            if len(docsplit) <= 1:
                formatted.append(docstr)
                continue

            wrapped_lines = textwrap.wrap(
                docsplit[1].strip(), maxlen - left_margin
            )
            wrapped = ("\n" + " " * left_margin).join(wrapped_lines)
            formatted.append(f"{docsplit[0]}\n    {wrapped}")

        uiutils.show_text_result("\n\n".join(formatted), _("Calculator"))
        raise IgnoreResultError

    def __complex__(self):
        return self()


def make_environment(last_result=None):
    "Return a namespace for the calculator's expressions to be executed in."
    environment = dict(vars(math))
    environment.update(vars(cmath))
    # define some constants missing
    if last_result is not None:
        environment["_"] = last_result

    environment["help"] = Help()
    environment["kupfer"] = KupferSurprise("inf")
    # make the builtins inaccessible
    environment["__builtins__"] = {}
    return environment


def format_result(res):
    cres = complex(res)
    parts = []
    if cres.real:  # pylint: disable=using-constant-test
        parts.append(str(cres.real))

    if cres.imag:  # pylint: disable=using-constant-test
        parts.append(str(complex(0, cres.imag)))

    return "+".join(parts) or str(res)


class Calculate(Action):
    # since it applies only to special queries, we can up the rank
    rank_adjust = 10
    # global last_result
    last_result: ty.ClassVar[dict[str, ty.Any]] = {"last": None}

    def __init__(self):
        Action.__init__(self, _("Calculate"))

    def has_result(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        expr = leaf.object.lstrip("= ")

        # try to add missing parentheses
        brackets_missing = expr.count("(") - expr.count(")")
        if brackets_missing > 0:
            expr += ")" * brackets_missing

        # hack: change all decimal points (according to current locale) to '.'
        # expr = expr.replace(locale.localeconv()['decimal_point'], '.')
        environment = make_environment(self.last_result["last"])
        pretty.print_debug(__name__, "Evaluating", expr)
        try:
            result = eval(expr, environment)  # pylint: disable=eval-used
            resultstr = format_result(result)
            self.last_result["last"] = result
        except IgnoreResultError:
            return None
        except Exception as exc:
            pretty.print_error(__name__, type(exc).__name__, exc)
            resultstr = str(exc)

        return TextLeaf(resultstr)

    def item_types(self):
        yield TextLeaf

    def valid_for_item(self, leaf):
        text = leaf.object
        return bool(text) and text.startswith("=")

    def get_description(self):
        return None
