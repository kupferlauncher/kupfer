from __future__ import annotations

import re
import urllib.parse
from contextlib import suppress


__all__ = ("is_url", "is_valid_email", "is_valid_file_path", "validate_netloc")


def _validate_port(port: str) -> bool:
    if not port:
        return False

    with suppress(ValueError):
        return 0 <= int(port) <= 65535

    return False


def _is_ipv4(string: str) -> bool:
    if len(octets := string.split(".")) == 4:
        with suppress(ValueError):
            return all(0 <= int(o) <= 255 for o in octets)

    return False


def _is_ipv6(netloc: str) -> bool:
    # quick and not perfect ipv6 address validation
    if netloc[0] != "[" or netloc[-1] != "]":
        return False

    netloc = netloc[1:-1]
    if not (2 <= len(netloc) <= 39):
        return False

    parts = netloc.split(":")
    if not (3 <= len(parts) <= 8):
        return False

    return all(re.match(r"[0-9a-fA-F]{1,4}", part) for part in parts if part)


def _is_valid_domain(domain: str) -> bool:
    if not domain:
        return False

    domain_re = (
        # hostname
        r"[a-z\u00a1-\uffff0-9](?:[a-z\u00a1-\uffff0-9-]{0,61}"
        r"[a-z\u00a1-\uffff0-9])?"
        # domain
        r"(?:\.(?!-)[a-z\u00a1-\uffff0-9-]{1,63}(?<!-))*"
        # tld
        r"\."  # dot
        r"(?!-)"  # can't start with a dash
        r"(?:[a-z\u00a1-\uffff-]{2,63}"  # domain label
        r"|xn--[a-z0-9]{1,59})"  # or punycode label
        r"(?<!-)"  # can't end with a dash
        r"\.?"  # may have a trailing dot
    )
    return bool(re.match(domain_re, domain, re.IGNORECASE))


def _is_valid_hostname(name: str) -> bool:
    return bool(
        re.match(
            r"[a-z\u00a1-\uffff0-9](?:[a-z\u00a1-\uffff0-9-]{0,61}"
            r"[a-z\u00a1-\uffff0-9])?",
            name,
            re.IGNORECASE,
        )
    )


def validate_netloc(netloc: str) -> bool:
    """Check if `netloc` is valid netlocation.

    Accepted forms [<user>[:<pass>]@]<hostname with domain|ipv4|ipv6>[:port]

    based on django.validator
    https://github.com/django/django/blob/main/django/core/validators.py
    """
    if not netloc:
        return False

    # netlock may contain user:pass
    if "@" in netloc:
        user_pass, _s, netloc = netloc.partition("@")
        if user_pass and not re.match(r"[^\s:@/]+(?::[^\s:@/]*)?", user_pass):
            return False

    host = netloc
    # is there domain:port?
    if re.match(r".+:\d{1,5}$", netloc):
        # check is port valid
        host, _s, port = netloc.rpartition(":")
        if not _validate_port(port):
            return False

    if not host:
        return False

    return (
        host == "localhost"
        or _is_ipv4(host)
        or _is_valid_domain(host)
        or _is_ipv6(host)
    )


def _guess_schema(netloc: str) -> str:
    """Guess schema for network location `netloc`."""
    if netloc.startswith("ftp.") or "@ftp." in netloc:
        return "ftp"

    # assume localhost is http
    if "localhost" in netloc or re.match(r"^127\.\d+\.\d+\.\d+$", netloc):
        return "http"

    return "https"


def _is_http_domain(netloc: str) -> bool:
    """Guess is `netloc` is some kind of real domain. It's not accurate"""

    if netloc == "localhost":
        return True

    parts = netloc.split(".")
    if not all(parts):
        return False

    len_parts = len(parts)
    if len_parts == 1:
        return False

    if len_parts > 2:
        return True

    if "localhost" in parts:
        return True

    lpart = parts[-1]
    if len(lpart) == 2:  # natonal code (mostly)
        return True

    return lpart in ("com", "org", "net", "gov", "local")


# from https://www.iana.org/assignments/uri-schemes/uri-schemes.xhtml
# schemes that not require / not have netloc. Skipped exotic/historic.
_schema_wo_netloc = {
    "android",
    "admin",  # unofficial, gnome
    "apt",
    "bitcoin",
    "bitcoincash",
    "callto",
    "dab",
    "dvb",
    "ethereum",
    "file",
    "fm",
    "gg",
    "gtalk",
    "ipfs",
    "ipns",
    "jabber",
    "lastfm",
    "magnet",
    "mailto",
    "maps",
    "market",
    "message",
    "nntp",
    "news",
    "skype",
    "sms",
    "steam",
}


def is_url(text: str) -> str | None:
    """If `text` is an URL, return a cleaned-up URL, else return `None`

    Ref:
        https://en.wikipedia.org/wiki/Uniform_Resource_Identifier
        https://www.iana.org/assignments/uri-schemes/uri-schemes.xhtml
        https://en.wikipedia.org/wiki/List_of_URI_schemes
    """
    text = text.strip()

    # quick check is text contain valid for url characters
    if not re.match(
        r"^[a-z\u00a1-\uffff0-9-:/?#\[\]@!$&;()*+.,;=~_-]+$",
        text,
        re.IGNORECASE,
    ):
        return None

    url = urllib.parse.urlparse(text)
    netloc = url.netloc
    scheme = url.scheme
    path = url.path

    if scheme and netloc:
        # if we have schema and valid domain - it's ok
        if validate_netloc(netloc):
            return text

        # accept also non-fqdn hostname
        if _is_valid_hostname(netloc):
            return text

        return None

    if scheme and path:
        # this is valid for mailto:, news: and other urls that not have netloc
        if scheme in _schema_wo_netloc:
            return text

        # spacial case for mail: replace mail: -> mailto:
        if scheme == "mail":
            return f"mailto{text[4:]}"

    if not netloc:
        # if there is no schema and no '//' on begin of netloc urlparse
        # put this in path value. Also when for address like 'abc:a@kks' 'abc'
        # is in schema and rest in path.
        # try to fix this:
        if scheme and "://" not in text:
            netloc, _d, path = text.partition("/")
            schema = ""
        elif path:
            netloc, _d, path = path.partition("/")

    if netloc and validate_netloc(netloc):
        # valid netloc
        if path or url.query or _is_http_domain(netloc):
            schema = _guess_schema(netloc)
            return f"{schema}://{text}"

    return None


def is_valid_email(text: str) -> bool:
    """Check if `text` is valid email address."""
    if not text:
        return False

    local_part, _dummy, domain = text.partition("@")
    if not _is_valid_domain(domain):
        return False

    re_local_part = r"[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+"
    return bool(re.match(re_local_part, local_part))


_UNPRINTABLE = (
    "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0e\x0f"
    "\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a"
    "\x1b\x1c\x1d\x1e\x1f\x7f"
)


def is_valid_file_path(path: str | None) -> bool:
    """Not perfect path validation"""
    if not path:
        return False

    if len(path) > 256:
        return False

    if re.match(r"^[a-z]+://", path) or path.startswith("//"):
        return False

    return not any(c in _UNPRINTABLE for c in path)
