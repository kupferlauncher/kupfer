#!/usr/bin/python3
"""
kupfer      A convenient command and access tool

Copyright 2007-–2023 Ulrik Sverdrup and other Kupfer authors

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

if __name__ == "__main__":
    from pathlib import Path

    from kupfer import main

    # if kupfer is installed in this same dir should be defaults.cfg
    if not Path(__file__).with_name("defaults.cfg").is_file():
        print("!!!!!!!!!!!!!! WARN !!!!!!!!!!!!!!")
        print(
            "Launching Kupfer by kupfer.py is dedicated only for development. "
            "This may totally broke some plugins, and some parts may not not "
            "work as expected."
        )
        print("Also Kupfer may run much slower.")
        print("Please install and run Kupfer as described in documentation.")
        print("!!!!!!!!!!!!!! WARN !!!!!!!!!!!!!!")

    main.main()
