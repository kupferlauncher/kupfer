# encoding: UTF-8

VERSION = "development version"
PACKAGE_NAME = "kupfer"

try:
	from kupfer import version_subst
except ImportError:
	pass
else:
	VERSION = version_subst.VERSION
	PACKAGE_NAME = version_subst.PACKAGE_NAME

ICON_NAME = "kupfer"
PROGRAM_NAME = _("Kupfer")

AUTHORS = u"""Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
Karol Będkowski
Francesco Marella
Chmouel Boudjnah
Horia V. Corcalciuc
Grigory Javadyan
Chris Parsons
Fabian Carlström
Jakh Daven
Thomas Renard
""".splitlines()

PACKAGERS=u"""
Luca Falavigna (Debian, Ubuntu)
Francesco Marella (Ubuntu PPA)
""".splitlines()

TRANSLATORS=u"""
Marek Černocký (cs)
Petr Kovar (cs)
Joe Hansen (da)
Thibaud Roth (de)
Mario Blättermann (de)
Leandro Leites (es)
Jesús Barbero Rodríguez (es)
Jorge González (es)
Daniel Mustieles (es)
Oier Mees (eu)
Iñaki Larrañaga Murgoitio (eu)
Christophe Benz (fr)
Marcos Lans (gl)
Fran Diéguez (gl)
Andrea Zagli (it)
Francesco Marella (it)
Martin Koelewijn (nl)
Kjartan Maraas (no)
Maciej Kwiatkowski (pl)
Karol Będkowski (pl)
Carlos Pais (pt)
Andrej Žnidaršič (sl)
Matej Urbančič (sl)
M. Deran Delice (tr)
lh (zh_CN)
Aron Xu (zh_CN)
Yinghua Wang (zh_CN)
""".splitlines()

ARTISTS=u"""Nasser Alshammari <designernasser@gmail.com>
""".splitlines()

AUTHORS += ARTISTS + PACKAGERS + TRANSLATORS

DOCUMENTERS = []

# TRANS: Don't translate literally!
# TRANS: This should be a list of all translators of this language
TRANSLATOR_CREDITS = _("translator-credits")

WEBSITE = u"http://kaizer.se/wiki/kupfer/"
HELP_WEBSITE = u"http://kaizer.se/wiki/kupfer/help/"

SHORT_DESCRIPTION = _("A free software (GPLv3+) launcher")
COPYRIGHT = u"""Copyright © 2007--2012 Ulrik Sverdrup with others"""

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

# follows strings used elsewhere

_("Could not find running Kupfer")
