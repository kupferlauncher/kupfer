from __future__ import annotations

import re
import urllib.parse
from contextlib import suppress


def _validate_port(port: str) -> bool:
    if not port:
        return False

    with suppress(ValueError):
        numport = int(port)
        return 0 <= numport <= 65535

    return False


def _is_ipv4(string: str) -> bool:
    if len(octets := string.split(".")) == 4:
        with suppress(ValueError):
            if all(0 <= int(o) <= 255 for o in octets):
                return True

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


def validate_netloc(netloc: str) -> bool:
    """Validate is netlocation valid.
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
    if re.match(r".+:\d{1,5}$", netloc):
        # check is port valid
        host, port = netloc.rsplit(":", 1)
        if not _validate_port(port):
            return False

    if not host:
        return False

    if host == "localhost":
        return True

    return _is_ipv4(host) or _is_valid_domain(host) or _is_ipv6(host)


def _is_http_domain(netloc: str) -> bool:
    """Guess is netloc is some kind of real domain.
    It's not accurate"""
    if netloc == "localhost":
        return True

    parts = list(filter(None, netloc.split(".")))
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


def is_url(text: str) -> str | None:
    """If @text is an URL, return a cleaned-up URL, else return None"""
    text = text.strip()
    url = urllib.parse.urlparse(text)
    netloc = url.netloc
    scheme = url.scheme
    path = url.path

    if scheme and netloc:
        # if we have schema and valid domain - it's ok
        if validate_netloc(netloc):
            return text

        return None

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
        if (
            _is_ipv4(netloc)
            or _is_ipv6(netloc)
            or path
            or url.query
            or _is_http_domain(netloc)
        ):
            if netloc.startswith("ftp.") or "@ftp." in netloc:
                schema = "ftp"
            elif "localhost" in netloc:
                schema = "http"
            else:
                schema = "https"

            return f"{schema}://{text}"

    return None


def is_valid_email(text: str) -> bool:
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
