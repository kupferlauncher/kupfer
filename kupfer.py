#!/usr/bin/python3
"""
kupfer      A convenient command and access tool

Copyright 2007--2017 Ulrik Sverdrup

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

if __name__ == '__main__':
    from kupfer import main
#    from os import chdir
#    chdir("/home/chaitanya/Documents/PROJECTS/kupfer/")
#    chdir is required if kupfer script added in OS starup (start on boot). Otherwise all the applications are not indexed.
    main.main()
