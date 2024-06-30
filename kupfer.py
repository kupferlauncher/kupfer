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

    stackprinter.set_excepthook(
        style="color",
        suppressed_paths=[r"*/site-packages/typeguard/"],
    )
except ImportError:
    try:
        from rich.traceback import install

        suppress_modules = []

        try:
            import typeguard

            suppress_modules.append(typeguard)
        except ImportError:
            pass

        install(show_locals=True, suppress=suppress_modules)
        print("rich.traceback installed")
    except ImportError:
        pass

try:
    import icecream

    icecream.install()
    icecream.ic.configureOutput(includeContext=True)

    import traceback

    def ic_stack(*args, **kwargs):
        stack = "".join(tbs.rstrip() for tbs in traceback.format_stack()[:-2])
        ic(stack, *args, **kwargs)

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
        from typeguard import install_import_hook

        install_import_hook("kupfer")
        print("WARN! typeguard hook installed")

        import typing
        typing.TYPE_CHECKING = True

        import typeguard._checkers as checkers
        checkers.check_protocol = None  # agronholm/typeguard#465
except ImportError as err:
    print(err)

try:
    from pympler import tracker
except ImportError:
    tracker = None


if __name__ == "__main__":
    from kupfer import main

    if tracker:
        tr = tracker.SummaryTracker()

    print("!!!!!!!!!!!!!! WARN !!!!!!!!!!!!!!")
    print("Launching Kupfer by kupfer.py is dedicated only for development. "
          "This may totally broke some plugins, and some parts may not not "
          "work as expected.")
    print("Also Kupfer may run much slower.")
    print("Please install and run Kupfer as described in documentation.")
    print("!!!!!!!!!!!!!! WARN !!!!!!!!!!!!!!")


    main.main()

    if tracker:
        print("--- TRACKER start ---")
        tr.print_diff()
        print("--- TRACKER end ---")
