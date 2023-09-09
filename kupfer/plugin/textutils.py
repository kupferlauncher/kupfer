from __future__ import annotations

__kupfer_name__ = _("Textutils")
__kupfer_actions__ = (
    "Convert",
    "LineConvert",
    "CaseConvert",
    "Format",
)
__kupfer_sources__ = ("Generators",)
__description__ = _("Action for text, useful text generators and converters.")
__version__ = "2023.1"
__author__ = "Karol Będkowski"

import base64
from gettext import gettext as _
import urllib.parse
import secrets
import string
import uuid
import typing as ty
import datetime
import json
from contextlib import suppress
import xml.dom.minidom
from functools import partial

from kupfer import icons
from kupfer.obj import (
    Action,
    TextLeaf,
    RunnableLeaf,
    Source,
    Leaf,
    OperationError,
)


TextConverter = ty.Callable[[str], str]


class _Converter(Leaf):
    object: TextConverter

    def __init__(
        self, func: TextConverter, name: str, description: str | None = None
    ):
        super().__init__(func, name)
        self.description = description

    def get_description(self) -> str | None:
        return self.description


class _ConvertersSource(Source):
    def __init__(
        self,
        items_gen: ty.Callable[[Leaf], ty.Iterator[_Converter]],
        for_item: Leaf,
    ) -> None:
        super().__init__("Converters")
        self.items_gen = items_gen
        self.for_item = for_item

    def get_items(self):
        yield from self.items_gen(self.for_item)


class _ConvertAction(Action):
    def has_result(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert isinstance(leaf, TextLeaf)
        assert iobj and isinstance(iobj, _Converter)

        converter = iobj.object
        try:
            return TextLeaf(converter(leaf.object))
        except Exception as err:
            raise OperationError(f"Error: {err}") from err

    def requires_object(self):
        return True

    def object_source(self, for_item=None):
        return _ConvertersSource(self._get_converters, for_item)

    def object_types(self):
        yield _Converter

    def item_types(self):
        yield TextLeaf

    def _get_converters(self, for_leaf: Leaf) -> ty.Iterator[_Converter]:
        raise NotImplementedError

    def get_gicon(self):
        return icons.ComposedIcon("text-x-generic", "kupfer-execute")

    def get_icon_name(self):
        return "text-x-generic"


def _str_to_unix_ts(inp: str) -> str:
    """Convert int or float from `inp` do date."""
    ts = float(inp)
    # check is ns/ms precision
    if ts > 9999999999999.0:
        ts /= 1000000.0
    elif ts > 9999999999.0:
        ts /= 1000.0

    return str(datetime.datetime.fromtimestamp(ts))


class Convert(_ConvertAction):
    def __init__(self, name=_("Convert…")):
        super().__init__(name)

    def get_description(self):
        return _("Convert text with selected tool")

    def _get_converters(self, for_leaf: Leaf) -> ty.Iterator[_Converter]:
        yield _Converter(
            lambda x: base64.b64encode(x.encode()).decode(),
            _("Encode text with Base64"),
        )
        yield _Converter(
            lambda x: base64.b64decode(x.encode()).decode(),
            _("Decode text with Base64"),
        )
        yield _Converter(
            urllib.parse.quote,
            _("Quote URL"),
            _("Replace special characters in string using the %%xx escape."),
        )
        yield _Converter(
            urllib.parse.unquote,
            _("Unquote URL"),
            _("Replace %%xx escapes with their single-character equivalent."),
        )

        with suppress(ValueError):
            if float(for_leaf.object) > 0.0:
                yield _Converter(_str_to_unix_ts, _("Unix timestamp to date"))


class LineConvert(_ConvertAction):
    def __init__(self, name=_("Convert lines…")):
        super().__init__(name)

    def get_description(self):
        return _("Convert multiline text with selected tool")

    def _get_converters(self, for_leaf: Leaf) -> ty.Iterator[_Converter]:
        yield _Converter(
            lambda x: ",".join(t for i in x.split("\n") if (t := i.strip())),
            _("Join lines"),
            _("Join lines with comma"),
        )
        yield _Converter(
            lambda x: ",".join(
                f'"{t}"' for i in x.split("\n") if (t := i.strip())
            ),
            _("Quote and join lines"),
            _("Wrap with quote and join lines with comma"),
        )


def _uncamellcase(text: str) -> str:
    """Convert 'SomeTextInCamelCase' into 'some text in camel case'."""
    res: list[str] = []
    for let in text:
        if let.isupper():
            if res and res[-1] != " ":
                res.append(" ")

            res.append(let.lower())

        else:
            res.append(let)

    return "".join(res)


def _camelcase(instr: str) -> str:
    words = instr.split(" ")
    if words:
        return words[0].lower() + "".join((p.capitalize() for p in words[1:]))

    return instr


class CaseConvert(_ConvertAction):
    def __init__(self, name=_("Convert case…")):
        super().__init__(name)

    def get_description(self):
        return _("Convert text case")

    def _get_converters(self, for_leaf: Leaf) -> ty.Iterator[_Converter]:
        yield _Converter(lambda x: x.lower(), _("to lower case"))
        yield _Converter(lambda x: x.upper(), _("to upper case"))
        yield _Converter(lambda x: x.capitalize(), _("to sentence case"))
        yield _Converter(
            lambda x: " ".join((p.capitalize() for p in x.split(" "))),
            _("capitalize words"),
            _("Convert 'some string' to 'Some String'"),
        )
        yield _Converter(
            _camelcase,
            _("to camel case"),
            _("Convert 'Some string' to 'comeString'"),
        )
        yield _Converter(
            lambda x: "".join((p.capitalize() for p in x.split(" "))),
            _("to pascal case"),
            _("Convert 'Some string' to 'SomeString'"),
        )
        yield _Converter(
            lambda x: x.upper().replace(" ", "_"),
            _("to constant case"),
            _("Convert 'some string' to 'SOME_STRING'"),
        )
        yield _Converter(
            _uncamellcase,
            _("camel case to lowercase"),
            _("Convert 'SomeString' do 'some string'"),
        )
        yield _Converter(
            lambda x: x.lower().replace("_", " "),
            _("constant case to lowercase"),
            _("Convert 'SOME_STRING' do 'some string'"),
        )


class Format(_ConvertAction):
    def __init__(self, name=_("Format…")):
        super().__init__(name)

    def get_description(self):
        return _("Format text using selected formatter")

    def _get_converters(self, for_leaf: Leaf) -> ty.Iterator[_Converter]:
        yield _Converter(
            lambda x: "\n".join(line.strip() for line in x.split("\n")),
            _("strip whitespaces"),
        )
        yield _Converter(
            lambda x: json.dumps(json.loads(x), sort_keys=True, indent=4),
            _("format json"),
        )
        yield _Converter(
            lambda x: json.dumps(json.loads(x), separators=(",", ":")),
            _("compress json"),
        )
        yield _Converter(
            lambda x: xml.dom.minidom.parseString(x).toprettyxml(),
            _("format xml"),
        )


class _GeneraterLeaf(RunnableLeaf):
    def __init__(
        self,
        name: str,
        func: ty.Callable[[], str],
        description: str | None = None,
    ) -> None:
        super().__init__(func, name=name)
        self.description = description

    def has_result(self):
        return True

    def run(self, ctx=None):
        try:
            if res := self.object():
                return TextLeaf(res)

        except Exception as err:
            raise OperationError(f"Generator error: {err}") from err

        return None

    def get_description(self):
        return self.description

    def get_icon(self):
        return icons.ComposedIcon("stock_new-text", "kupfer-execute")


def _generate_alfanum_token(size: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(size))


class Generators(Source):
    serializable = None

    def __init__(self, name=_("Generators")):
        super().__init__(name)

    def is_dynamic(self):
        return True

    def get_items(self):
        for size in (16, 32, 64):
            yield _GeneraterLeaf(
                _("Random %(size)d-bytes hex token") % {"size": size},
                partial(secrets.token_hex, size),
            )

        for size in (16, 32, 64):
            yield _GeneraterLeaf(
                _("Random %(size)d-bytes alpha-numeric token") % {"size": size},
                partial(_generate_alfanum_token, size),
            )

        yield _GeneraterLeaf(
            _("UUID based on host and time"),
            lambda: str(uuid.uuid1()),
        )
        yield _GeneraterLeaf(_("Random UUID"), lambda: str(uuid.uuid4()))

        yield _GeneraterLeaf(
            _("Current time in ISO8601 format"),
            lambda: datetime.datetime.now().isoformat(),
        )
        yield _GeneraterLeaf(
            _("Current time as Unix timestamp"),
            lambda: str(int(datetime.datetime.now().timestamp())),
        )
        yield _GeneraterLeaf(
            _("Current time as timestamp"),
            lambda: str(int(datetime.datetime.now().timestamp() * 1000)),
        )

    def provides(self):
        yield RunnableLeaf

    def get_gicon(self):
        return icons.ComposedIcon("stock_new-text", "kupfer-execute")

    def get_icon_name(self):
        return "stock_new-text"

    def get_description(self):
        return _("Generate text content with selected tool")
