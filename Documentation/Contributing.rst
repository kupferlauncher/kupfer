

Guidelines and Policy
=====================

Contributing
------------

You can structure your changes into a series of commits in git. A series
of well disposed changes is easy to review. Write a sufficient commit
log message for each change. Do not fear writing down details about
why the change is implemented as it is, if there are multiple
alternatives. Also, if you forsee any future possibilites or problems,
please describe them in the commit log.

You can find kupfer's `git repository at github`__ and fork it there,
for easy publication of your changes.

If you suggest your changes for inclusion into Kupfer, make sure you
have read the whole *Guidelines and Policy* chapter of this manual. And
take care to structure your changes, do not fear asking for advice. Good
Luck!

__ https://github.com/kupferlauncher/kupfer


Icon Guidelines
---------------

Consider the following:

* A Leaf is an object, a metaphor for a physical thing. It can have as
  detailed icon as is possible.

* An Action is a verb, a command that can be carried out. Choose its
  name with care. The icon should be simple, maybe assign the action
  to a category, rather than trying to illustrate the action itself.
  For example, all text display actions use the "bold style" icon, in
  some icon themes simply a bold "A".

.. important::

    Actions should have stylized, simple icons. Leaves and Sources
    should have detailed, specific icons.


Coding style
------------

Kupfer python code is indented with four spaces.  If you contribute to
kupfer keep in mind that

* Python code should be clear
* Kupfer is a simple project. Do simple first.

Python's general style guideline is called `PEP 8`_, and you should
programmers should read it. The advice given there is very useful when
coding for Kupfer.

.. _`PEP 8`: https://www.python.org/dev/peps/pep-0008/

Specific Points
---------------

Using ``rank_adjust``
.....................

A declaration like this can modify the ranking of an object::

    class MyAction (Action):
        rank_adjust = -5
        ...

1. Often, this is useless. Don't use it, let Kupfer learn which actions
   are important.

2. If the action is destructive, the adjust should be negative. Never
   positive. For example *Move to Trash* has a negative 10
   ``rank_adjust``.

3. If the action is very general, and applies to almost everything but
   still should never be the default for anything, the adjust should be
   negative.


Using ``super(..)``
...................

You should use the Python 3 ``super()`` without arguments.

Old code was using the following style which worked best in older
Python, but the style is obsolete::

    Source.__init__(self, _("Recent items"))

Text and Encodings
..................

Care must be taken with all input and output text and its encoding!
Internally, kupfer must use ``str`` for all internal text.
The module ``kupfer.kupferstring`` has functions for the most important
text conversions.

A resource for unicode in Python:

| http://farmdev.com/talks/unicode/

**Always** find out what encoding you must expect for externally read
text (from files or command output). If you must guess, use the locale
encoding.
Text received from GTK is always ``str``, which means encoding is not
a problem.

Note that the gettext function ``_()`` always returns a unicode string
(``str``).

.. vim: ft=rst tw=72 et sts=4
.. this document best viewed with rst2html
