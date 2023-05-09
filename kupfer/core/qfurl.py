from __future__ import annotations

import typing as ty
import urllib.parse
from contextlib import suppress
from urllib.parse import urlparse as _urlparse
from urllib.parse import urlunparse as _urlunparse

from kupfer.obj.base import Leaf, Source
from kupfer.support import pretty

QFURL_SCHEME = "qpfer"

# One would hope that there was a better way to do this
urllib.parse.uses_netloc.append(QFURL_SCHEME)
with suppress(AttributeError):
    urllib.parse.uses_fragment.append(QFURL_SCHEME)


class QfurlError(Exception):
    pass


class Qfurl:
    """A Qfurl is a URI to locate unique objects in kupfer's catalog.

    The Qfurl is built up as follows:
    ``qpfer://mother/qfid#module_and_type_hint``

    The mother part is a mother source identifier and is optional.
    The module_and_type_hint is optional.

    A short url looks like the following:
    ``qpfer:identifier``

    This class provides methods to get the Qfurl for an object,
    and resolve the object in a catalog.

    >>> class Object (object):
    ...     qf_id = "token"
    ...
    >>> q = Qfurl(Object())
    >>> Qfurl.reduce_url(q.url)
    'qpfer:token'

    >>> class Source (object):
    ...     def get_leaves(self):
    ...         yield Object()
    ...     def provides(self):
    ...         yield Object
    ...
    >>> q.resolve_in_catalog((Source(), ))  # doctest: +ELLIPSIS
    <__main__.Object object at 0x...>
    """

    def __init__(self, obj=None, url=None):
        """Create a new Qfurl for object @obj"""
        if obj:
            typname = f"{type(obj).__module__}.{type(obj).__name__}"
            try:
                qfid = obj.qf_id
            except AttributeError as exe:
                raise QfurlError(f"{obj} has no Qfurl") from exe

            self.url = _urlunparse((QFURL_SCHEME, "", qfid, "", "", typname))
        else:
            self.url = url

    def __str__(self) -> str:
        return self.url

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: ty.Any) -> bool:
        return self.reduce_url(self.url) == self.reduce_url(other.url)

    @classmethod
    def reduce_url(cls, url: str) -> str:
        """
        >>> url = "qpfer://mother/qfid#module_and_type_hint"
        >>> Qfurl.reduce_url(url)
        'qpfer://mother/qfid'
        """
        return urllib.parse.urldefrag(url)[0].replace("///", "", 1)

    @classmethod
    def _parts_mother_id_typename(cls, url: str) -> tuple[str, str, str]:
        """
        >>> murl = "qpfer://mother/qfid#module_and_type_hint"
        >>> Qfurl._parts_mother_id_typename(murl)
        ('mother', 'qfid', 'module_and_type_hint')
        """
        scheme, mother, qfid, _ign, _ore, typname = _urlparse(url)
        if scheme != QFURL_SCHEME:
            raise QfurlError(f"Wrong scheme: {scheme}")

        qfid = qfid.lstrip("/")
        return mother, qfid, typname

    def resolve_in_catalog(self, catalog: ty.Collection[Source]) -> Leaf | None:
        """Resolve self in a catalog of sources.
        Return *immediately* on match found"""
        _mother, _qfid, typname = self._parts_mother_id_typename(self.url)
        _module, name = typname.rsplit(".", 1) if typname else (None, None)
        for src in catalog:
            if name:
                if name not in (
                    pt.__name__ for pt in src.provides()
                ) and name not in (
                    t.__name__
                    for pt in src.provides()
                    for t in pt.__subclasses__()
                ):
                    continue

            for obj in src.get_leaves() or []:
                if not hasattr(obj, "qf_id"):
                    continue

                with suppress(QfurlError):
                    if self == Qfurl(obj):
                        return obj

        pretty.print_debug(__name__, "No match found for", self)
        return None


if __name__ == "__main__":
    import doctest

    doctest.testmod()
