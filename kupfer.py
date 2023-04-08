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

    def ic_stack(*args, **kwargs):
        ic("\n".join(traceback.format_stack()[:-2]), *args, **kwargs)

    import inspect

    class ShiftedIceCreamDebugger(icecream.IceCreamDebugger):
        def format(self, *args):
            # one more frame back
            callFrame = inspect.currentframe().f_back.f_back
            out = self._format(callFrame, *args)
            return out

    sic = ShiftedIceCreamDebugger()

    def ic_trace(func):
        def wrapper(*args, **kwargs):
            sic(func, args, kwargs)
            res = func(*args, **kwargs)
            sic(func, res)
            return res

        return wrapper

    import builtins

    setattr(builtins, "ic_stack", ic_stack)
    setattr(builtins, "ic_trace", ic_trace)
except ImportError:  # Graceful fallback if IceCream isn't installed.
    pass


try:
    if "--debug" in sys.argv:
        from typeguard.importhook import install_import_hook

        install_import_hook("kupfer")
        print("WARN! typeguard hook installed")
except ImportError:
    pass

try:
    from pympler import tracker
except ImportError:
    tracker = None


if __name__ == "__main__":
    from kupfer import main

    if tracker:
        tr = tracker.SummaryTracker()

    main.main()

    if tracker:
        print("--- TRACKER start ---")
        tr.print_diff()
        print("--- TRACKER end ---")
