# Copyright (C) 2009  Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
#               2008  Christian Hergert <chris@dronelabs.com>
#               2007  Chris Halse Rogers, DR Colkitt
#                     David Siegel, James Walker
#                     Jason Smith, Miguel de Icaza
#                     Rick Harding, Thomsen Anders
#                     Volker Braun, Jonathon Anderson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module provides relevance matching and formatting of related strings
based on the relevance.  It originates in Gnome-Do.

 * Python port by Christian Hergert

 * Module updated by Ulrik Sverdrup to clean up and dramatically speed up
   the code, by using more pythonic constructs as well as doing less work.

Compatibility: Python 3
"""
from __future__ import annotations

import typing as ty

FormatCleanCB = ty.Callable[[str], str]
FormatMatchCB = ty.Callable[[str], str]


def _default_formatter(x: str) -> str:
    return x


def format_common_substrings(
    string: str,
    query: str,
    format_clean: FormatCleanCB | None = None,
    format_match: FormatMatchCB | None = None,
) -> str:
    """Creates a new string highlighting matching substrings.
    Returns: a formatted string

    >>> format_common_substrings('hi there dude', 'hidude',
    ...                        format_match=lambda m: "<b>%s</b>" % m)
    '<b>hi</b> there <b>dude</b>'

    >>> format_common_substrings('parallelism', 'lsm', format_match=str.upper)
    'paralleLiSM'
    """
    format_clean = format_clean or _default_formatter

    def _format(x: str) -> str:
        return x and format_clean(x)

    if not query:
        return _format(string)

    lowerstr = string.lower()

    # find overall range of match
    first, last = _find_best_match(lowerstr, query)

    if first == -1:
        return _format(string)

    # find longest perfect match, put in slc
    for slc in range(len(query), 0, -1):
        if query[:slc] == lowerstr[first : first + slc]:
            break

    nextkey = query[slc:]
    head = string[:first]
    match = string[first : first + slc]
    matchtail = string[first + slc : last]
    tail = string[last:]

    format_match = format_match or _default_formatter

    return "".join(
        (
            _format(head),
            format_match(match),
            format_common_substrings(
                matchtail, nextkey, format_clean, format_match
            ),
            _format(tail),
        )
    )


def score_single(string: str, query: str) -> float:
    """Find the shortest possible substring that matches the query
     and get the ration of their lengths for a base score.

    string: text body to score
    query: A single character

    This is a single character approximation to `score`.

    >>> round(score_single('terminal', 't'), 6)
    0.973125
    >>> round(score_single('terminal', 'e'), 6)
    0.903125
    >>> round(score_single('terminal', 'a'), 6)
    0.903125
    >>> round(score_single('t', 't'), 6)
    0.995
    """

    string = string.lower()

    first = string.find(query)
    if first == -1:
        return 0.0

    if first == 0:
        return 0.97 + 0.025 / len(string)

    return 0.9 + 0.025 / len(string)


def score(string: str, query: str) -> float:
    """A relevancy score for the string ranging from 0 to 1.

    @string: a string to be scored
    @query: a string query to score against

    `string' is treated case-insensitively while `query' is interpreted
    literally, including case and whitespace.

    Returns: a float between 0 and 1

    >>> round(score('terminal', 'trml'), 6)
    0.735099
    >>> round(score('terminal', 'term'), 6)
    0.992303
    >>> print(score('terminal', 'try'))
    0.0
    >>> print(score('terminal', ''))
    1.0
    >>> round(score('terminal', 't'), 6)
    0.98949
    >>> round(score('terminal', 'e'), 6)
    0.918438
    """
    if not query:
        return 1.0

    string = string.lower()

    # Find the shortest possible substring that matches the query
    # and get the ration of their lengths for a base score
    first, last = _find_best_match(string, query)
    if first == -1:
        return 0.0

    query_len = len(query)
    strscore: float = query_len / (last - first)

    # Now we weight by string length so shorter strings are better
    strscore *= 0.7 + query_len / len(string) * 0.3

    # Bonus points if the characters start words
    bad = 1
    first_count = 0
    for i in range(first, last - 1):
        if string[i] in " -.([_":
            if string[i + 1] in query:
                first_count += 1
            else:
                bad += 1

    # A first character match counts extra
    if query[0] == string[0]:
        first_count += 2

    # The longer the acronym, the better it scores
    good = first_count * first_count * 4

    # Better yet if the match itself started there
    if first == 0:
        good += 2

    # Super duper bonus if it is a perfect match
    if query == string:
        good += last * 2 + 4

    strscore = (strscore + 3 * good / (good + bad)) / 4

    # This fix makes sure that perfect matches always rank higher
    # than split matches.  Perfect matches get the .9 - 1.0 range
    # everything else lower

    if last - first == query_len:
        return 0.9 + 0.1 * strscore

    return 0.9 * strscore


def _find_best_match(string: str, query: str) -> tuple[int, int]:
    """Finds the shortest substring of @s that contains all characters of query
    in order.

    @string: a string to search
    @query: a string query to search for

    Returns: a two-item tuple containing the start and end indicies of
             the match.  No match returns (-1,-1).

    >>> _find_best_match('terminal', 'trml')
    (0, 8)
    >>> _find_best_match('total told', 'tl')
    (2, 5)
    >>> _find_best_match('terminal', 'yl')
    (-1, -1)
    """
    # Find the last instance of the last character of the query
    # since we never need to search beyond that
    last_char = string.rfind(query[-1])

    # No instance of the character?
    if last_char == -1:
        return -1, -1

    # Loop through each instance of the first character in query
    index = string.find(query[0])
    best_match_start = -1
    best_match_end = -1
    query_len = len(query)
    last_index = last_char - query_len + 1
    while 0 <= index <= last_index:
        # See if we can fit the whole query in the tail
        # We know the first char matches, so we dont check it.
        cur = index + 1
        qcur = 1
        while qcur < query_len:
            # find where in the string the next query character is
            # if not found, we are done
            cur = string.find(query[qcur], cur, last_char + 1)
            if cur == -1:
                return best_match_start, best_match_end

            cur += 1
            qcur += 1

        # take match if it is shorter
        # if perfect match, we are done
        if best_match_start == -1 or (cur - index) < (
            best_match_end - best_match_start
        ):
            best_match_start = index
            best_match_end = cur
            if cur - index == query_len:
                break

        index = string.find(query[0], index + 1)

    return best_match_start, best_match_end


if __name__ == "__main__":
    import doctest

    doctest.testmod()
