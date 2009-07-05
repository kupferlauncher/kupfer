# encoding: UTF-8

VERSION = "version undefined"
PACKAGE_NAME = "kupfer"

try:
	import version_subst
except ImportError:
	pass
else:
	VERSION = version_subst.VERSION
	PACKAGE_NAME = version_subst.PACKAGE_NAME

ICON_NAME = "search"
PROGRAM_NAME = _("Kupfer")

AUTHORS = """Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
""".splitlines()

DOCUMENTERS = []

TRANSLATOR_CREDITS = _("translator-credits")

WEBSITE = "http://kaizer.se/wiki/kupfer/"

SHORT_DESCRIPTION = _("A free software (GPLv3+) launcher")
COPYRIGHT = """Copyright © 2007--2009 Ulrik Sverdrup"""

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
