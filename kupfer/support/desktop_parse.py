"""
Implementation of unescaping and unquoting of the Exec= key in
the Desktop Entry Specification (As of March 2011, version 1.1-draft)
http://standards.freedesktop.org/desktop-entry-spec/latest/ar01s06.html
http://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-1.1.html#exec-variables

The unescaping we are doing is only one way.. so we unescape according to the
rules, but we accept everything, if validly quoted or not.
"""

from __future__ import annotations

import shlex
import typing as ty

from kupfer.support import itertools as kitertools

__all__ = ("parse_argv", "parse_unesc_argv")

# This is the "string" type encoding escapes
# this is unescaped before we process anything..
_ESCAPE_TABLE = {
    r"\s": " ",
    r"\n": "\n",
    r"\t": "\t",
    r"\r": "\r",
    "\\\\": "\\",
}

# quoted are those chars that need a backslash in front
# (inside a double-quoted section, that is)
# not in use
# quoted = r""" " ` $ \ """.split()
# quoted_table = {
#     r"\"": '"',
#     r"\`": "`",
#     r"\$": "$",
#     "\\\\": "\\",
# }

# reserved are those that need to be inside quotes
# note that all the quoted are also reserved, of course
# We don't use these at all
# reserved = r""" " ' \ > < ~ | & ; $ * ? # ( ) ` """.split()
# reserved.extend([' ', '\t', '\n'])


def _two_part_unescaper(string: str, reptable: dict[str, str]) -> str:
    """Scan @s two characters at a time and replace using @reptable"""
    if not string:
        return string

    def repfunc(instr: str) -> str | None:
        return reptable.get(instr)

    return kitertools.two_part_mapper(string, repfunc)


T = ty.TypeVar("T", str, bytes)


def _custom_shlex_split(
    string: T, comments: bool = False, posix: bool = True
) -> list[T]:
    """Wrapping shlex.split."""
    ustring: str
    if isinstance(string, str):
        ustring = string
    elif isinstance(string, bytes):
        ustring = string.decode("UTF-8", "replace")
    else:
        raise TypeError

    lex = shlex.shlex(ustring, posix=posix)
    lex.whitespace_split = True
    if not comments:
        lex.commenters = ""

    try:
        lex_output = tuple(lex)
    except ValueError:
        lex_output = (ustring,)

    ## extra-unescape  ` and $ that are not handled by shlex
    quoted_shlex = {r"\`": "`", r"\$": "$"}
    output = (_two_part_unescaper(x, quoted_shlex) for x in lex_output)
    if isinstance(string, str):
        return list(output)

    return list(map(str.encode, output))


def _unescape(string: str) -> str:
    """Primary unescape of control sequences"""
    return _two_part_unescaper(string, _ESCAPE_TABLE)


def parse_argv(instr: str) -> list[str]:
    r"""Parse quoted @instr into an argv

    This is according to the spec
    >>> parse_argv('env "VAR=is good" ./program')
    ['env', 'VAR=is good', './program']
    >>> parse_argv('env "VAR=\\\\ \\$ @ x" ./program')
    ['env', 'VAR=\\ $ @ x', './program']
    >>> parse_argv('"\\$" "\\`"  "\\""')
    ['$', '`', '"']
    >>> parse_argv('/usr/bin/x-prog -q %F')
    ['/usr/bin/x-prog', '-q', '%F']
    >>> parse_argv('env LANG=en_US.UTF-8 freeciv-gtk2')
    ['env', 'LANG=en_US.UTF-8', 'freeciv-gtk2']
    >>> parse_argv('emacsclient -a "" -c %f')
    ['emacsclient', '-a', '', '-c', '%f']

    == Below this we need quirks mode ==

    The following style is common but not supported in spec
    >>> parse_argv('env VAR="is broken" ./program')
    ['env', 'VAR=is broken', './program']

    The following is just completely broken
    >>> parse_argv('./program unquoted\\\\argument')
    ['./program', 'unquoted\\argument']

    The following is just completely broken
    >>> parse_argv('./program No\\ Space')
    ['./program', 'No Space']

    The following is just insanely broken
    >>> parse_argv("'/opt'/now/'This is broken/'")
    ['/opt/now/This is broken/']

    This is broken
    #>>> parse_argv('\\$')
    #['$']
    #>>> parse_argv('\\$ \\`  \\"')
    #['$', '`', '"']

    Unmatched quote, normal mode (just testing that it does not raise)
    >>> parse_argv('"hi there')
    ['"hi there']

    Unmatched quote, quirks mode (just testing that it does not raise)
    >>> parse_argv('A\\\\BC "hi there')
    ['A\\\\BC "hi there']

    """
    return _custom_shlex_split(instr)


def parse_unesc_argv(instr: str) -> list[str]:
    r"""Parse quoted @instr into an argv after unescaping it

    >>> parse_unesc_argv(r'stuff "C:\\\\suck\\\\start.exe"')
    ['stuff', 'C:\\suck\\start.exe']

    == Below this we need quirks mode ==

    >>> parse_unesc_argv(r'stuff C:\\\\suck\\\\start.exe')
    ['stuff', 'C:\\suck\\start.exe']

    >>> parse_unesc_argv("'/usr'/bin/gnome-terminal -x gvim 'Insanely Broken'Yes")
    ['/usr/bin/gnome-terminal', '-x', 'gvim', 'Insanely BrokenYes']
    """
    return _custom_shlex_split(_unescape(instr))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
