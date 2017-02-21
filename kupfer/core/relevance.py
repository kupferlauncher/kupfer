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
from __future__ import division

"""
This module provides relevance matching and formatting of related strings
based on the relevance.  It originates in Gnome-Do.

 * Python port by Christian Hergert

 * Module updated by Ulrik Sverdrup to clean up and dramatically speed up
   the code, by using more pythonic constructs as well as doing less work.

Compatibility: Python 2.4 and later, including Python 3
"""



# This module is compatible with both Python 2 and Python 3;
# we need the iterator form of range for either version, stored in range()
try:
    range = xrange
except NameError:
    pass

def formatCommonSubstrings(s, query, format_clean=None, format_match=None):
    """
    Creates a new string highlighting matching substrings.

    Returns: a formatted string

    >>> formatCommonSubstrings('hi there dude', 'hidude',
    ...                        format_match=lambda m: "<b>%s</b>" % m)
    '<b>hi</b> there <b>dude</b>'

    >>> formatCommonSubstrings('parallelism', 'lsm', format_match=str.upper)
    'paralleLiSM'
    """
    format_clean = format_clean or (lambda x: x)
    format_match = format_match or (lambda x: x)
    format = lambda x: x and format_clean(x)

    if not query:
        return format(s)

    ls = s.lower()

    # find overall range of match
    first, last = _findBestMatch(ls, query)

    if first == -1:
        return format(s)

    # find longest perfect match, put in slc
    for slc in range(len(query), 0, -1):
        if query[:slc] == ls[first:first+slc]:
            break
    nextkey = query[slc:]

    head = s[:first]
    match = s[first: first+slc]
    matchtail = s[first+slc: last]
    tail = s[last:]

    # we use s[0:0], which is "" or u""
    return s[0:0].join((
            format(head),
            format_match(match),
            formatCommonSubstrings(matchtail, nextkey,
                                   format_clean, format_match),
            format(tail),
            ))

def score_single(s, query):
    """
    s: text body to score
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

    ls = s.lower()

    # Find the shortest possible substring that matches the query
    # and get the ration of their lengths for a base score
    first = ls.find(query)
    if first == -1:
        return .0
    score = 0.9 + .025 / len(s)

    if first == 0:
        score += 0.07
    return score

def score(s, query):
    """
    A relevancy score for the string ranging from 0 to 1

    @s: a string to be scored
    @query: a string query to score against

    `s' is treated case-insensitively while `query' is interpreted literally,
    including case and whitespace.

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

    ls = s.lower()

    # Find the shortest possible substring that matches the query
    # and get the ration of their lengths for a base score
    first, last = _findBestMatch(ls, query)
    if first == -1:
        return .0

    score = len(query) / (last - first)

    # Now we weight by string length so shorter strings are better
    score *= .7 + len(query) / len(s) * .3

    # Bonus points if the characters start words
    good = 0
    bad = 1
    firstCount = 0
    for i in range(first, last-1):
        if ls[i] in " -.([_":
            if ls[i + 1] in query:
                firstCount += 1
            else:
                bad += 1
    
    # A first character match counts extra
    if query[0] == ls[0]:
        firstCount += 2
        
    # The longer the acronym, the better it scores
    good += firstCount * firstCount * 4
    
    # Better yet if the match itself started there
    if first == 0:
        good += 2

    # Super duper bonus if it is a perfect match
    if query == ls:
        good += last * 2 + 4

    score = (score + 3 * good / (good + bad)) / 4

    # This fix makes sure that perfect matches always rank higher
    # than split matches.  Perfect matches get the .9 - 1.0 range
    # everything else lower
    
    if last - first == len(query):
        score = .9 + .1 * score
    else:
        score = .9 * score
    
    return score

def _findBestMatch(s, query):
    """
    Finds the shortest substring of @s that contains all characters of query
    in order.

    @s: a string to search
    @query: a string query to search for

    Returns: a two-item tuple containing the start and end indicies of
             the match.  No match returns (-1,-1).

    >>> _findBestMatch('terminal', 'trml')
    (0, 8)
    >>> _findBestMatch('total told', 'tl')
    (2, 5)
    >>> _findBestMatch('terminal', 'yl')
    (-1, -1)
    """
    bestMatch = -1, -1
    
    # Find the last instance of the last character of the query
    # since we never need to search beyond that
    lastChar = s.rfind(query[-1])
    
    # No instance of the character?
    if lastChar == -1:
        return bestMatch

    # Loop through each instance of the first character in query
    index = s.find(query[0])

    queryLength = len(query)
    lastIndex = lastChar - len(query) + 1
    while 0 <= index <= lastIndex:
        # See if we can fit the whole query in the tail
        # We know the first char matches, so we dont check it.
        cur = index + 1
        qcur = 1
        while qcur < queryLength:
            # find where in the string the next query character is
            # if not found, we are done
            cur = s.find(query[qcur], cur, lastChar + 1)
            if cur == -1:
                return bestMatch
            cur += 1
            qcur += 1

        # take match if it is shorter
        # if perfect match, we are done
        if bestMatch[0] == -1 or (cur - index) < (bestMatch[1] - bestMatch[0]):
            bestMatch = (index, cur)
            if cur - index == queryLength:
                break

        index = s.find(query[0], index + 1)

    return bestMatch

if __name__ == '__main__':
    import doctest
    doctest.testmod()
