from __future__ import annotations

import re
import urllib.parse


def _validate_port(port: str) -> bool:
    if not port:
        return False

    try:
        numport = int(port)
        return 0 <= numport <= 65535
    except ValueError:
        pass

    return False


def validate_netloc(netloc: str) -> bool:
    """Validate is netlocation is valid.
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

    if host == "localhost":
        return True

    # quick check ip4
    if len(octets := host.split(".")) == 4:
        try:
            if all(0 <= int(o) <= 255 for o in octets):
                return True
        except ValueError:
            pass

    host_re = (
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
    if re.match(host_re, host):
        return True

    # quick and not perfect ipv6 address validation
    if re.match(r"\[[0-9a-fA-F:.]+\]", host):
        colon_cnt = host.count(":")
        other_cnt = len(host) - colon_cnt - 2
        if 2 <= colon_cnt <= 7 and other_cnt <= 32:
            return True

    return False


def is_url(text: str) -> str | None:
    """If @text is an URL, return a cleaned-up URL, else return None"""
    text = text.strip()
    url = urllib.parse.urlparse(text)
    if url.scheme:
        # if we have schema and valid domain - it's ok
        if validate_netloc(url.netloc):
            return text

        return None

    # no schema
    if validate_netloc(url.netloc):
        # valid netloc, so guess schema
        schema = "https"
        if "localhost" in url.netloc:
            schema = "http"
        # assume for now - everything else is http
        return f"{schema}://{text}"

    # only path, guess - is file
    if not url.netloc and url.path and not url.query:
        return f"file:{text}"

    return None
