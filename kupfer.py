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

import sys

try:
    import stackprinter

    stackprinter.set_excepthook(style="color")
except ImportError:
    try:
        from rich.traceback import install

        install()
    except ImportError:
        pass

try:
    import icecream

    icecream.install()
    icecream.ic.configureOutput(includeContext=True)

    import traceback

    def ic_stack():
        ic("\n".join(traceback.format_stack()[:-2]))

    try:
        builtins = __import__("__builtin__")
    except ImportError:
        builtins = __import__("builtins")

    setattr(builtins, "ic_stack", ic_stack)
except ImportError:  # Graceful fallback if IceCream isn't installed.
    pass


try:
    if "--debug" in sys.argv:
        from typeguard.importhook import install_import_hook

        install_import_hook("kupfer")
        print("WARN! typeguard hook installed")
except ImportError:
    pass


if __name__ == "__main__":
    from kupfer import main

    main.main()
