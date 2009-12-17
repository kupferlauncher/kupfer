# encoding: UTF-8

VERSION = "version undefined"
PACKAGE_NAME = "kupfer"

try:
	from kupfer import version_subst
except ImportError:
	pass
else:
	VERSION = version_subst.VERSION
	PACKAGE_NAME = version_subst.PACKAGE_NAME

ICON_NAME = "search"
PROGRAM_NAME = _("Kupfer")

AUTHORS = u"""Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
Karol Będkowski
Francesco Marella
Chmouel Boudjnah
""".splitlines()

PACKAGERS=u"""
Luca Falavigna (Debian, Ubuntu)
Francesco Marella (Ubuntu PPA)
""".splitlines()

TRANSLATORS=u"""
Thibaud Roth (de)
Leandro Leites (es)
Jesús Barbero Rodríguez (es)
Andrea Zagli (it)
Martin Koelewijn (nl)
Maciej Kwiatkowski (pl)
Karol Będkowski (pl)
Carlos Pais (pt)
lh (zh_CN)
""".splitlines()

AUTHORS += PACKAGERS + TRANSLATORS

DOCUMENTERS = []

# TRANS: Don't translate literally!
# TRANS: This should be a list of all translators of this language
TRANSLATOR_CREDITS = _("translator-credits")

WEBSITE = u"http://kaizer.se/wiki/kupfer/"

SHORT_DESCRIPTION = _("A free software (GPLv3+) launcher")
COPYRIGHT = u"""Copyright © 2007--2009 Ulrik Sverdrup"""

LICENSE = _("""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
""")
