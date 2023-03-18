"""
Accelerators configuration.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import json
import typing as ty

from kupfer import config
from kupfer.support import pretty

_repr_key = repr


__all__ = ("AccelConfig",)

# AcceleratorValidator check is given accelerator is valid
AcceleratorValidator = ty.Callable[[str], bool]


class AccelConfig(pretty.OutputMixin):
    """Action Accelerator configuration"""

    def __init__(self):
        self.accels: ty.Dict[str, str] = {}
        self.loaded: bool = False
        self.changed: bool = False

    def _filename(self) -> str | None:
        if ret := config.save_config_file("action_accels.json"):
            return ret

        self.output_error("Can't find XDG_CONFIG_HOME")
        return None

    def load(self, validate_func: AcceleratorValidator) -> bool:
        """Load accelerators configuration.

        If configuration is already loaded - do nothing.

        After loading `validate_func` is used for each accelerator; if function
        return false - accelerator is ignored.

        Return True on success.
        """
        if self.loaded:
            return True

        self.loaded = True
        data_file = self._filename()
        if data_file is None:
            return False

        try:
            with open(data_file, encoding="UTF-8") as dfp:
                self.accels = json.load(dfp)

            self.output_debug("Read", data_file)
        except FileNotFoundError:
            return False
        except Exception:
            self.output_error("Failed to read:", data_file)
            self.output_exc()
            return False

        try:
            self._valid_accel(validate_func)
        except Exception:
            self.output_exc()
            self.accels = {}

        self.output_debug("Loaded", self.accels)
        return True

    def _valid_accel(self, validate_func: AcceleratorValidator) -> None:
        if not isinstance(self.accels, dict):
            raise TypeError("Accelerators must be a dictionary")

        self.accels.clear()
        for obj, k in self.accels.items():
            if validate_func(k):
                self.accels[obj] = k
            else:
                self.output_error("Ignoring invalid accel", k, "for", obj)

    def get(self, obj: ty.Any) -> str | None:
        """Return accel key for @obj or None"""
        return self.accels.get(_repr_key(obj))

    def set(self, obj: ty.Any, key: str) -> None:
        """Set accelerator `key` for `obj`."""
        self.output_debug("Set", key, "for", _repr_key(obj))
        assert hasattr(obj, "activate")
        assert isinstance(key, str)
        self.accels[_repr_key(obj)] = key
        self.changed = True

    def store(self) -> None:
        """Write all accelerator into configuration file."""
        if not self.changed:
            return

        data_file = self._filename()
        if data_file is None:
            return

        self.output_debug("Writing to", data_file)
        try:
            with open(data_file, "w", encoding="UTF-8") as dfp:
                json.dump(self.accels, dfp, indent=4, sort_keys=True)

        except Exception:
            self.output_error("Failed to write:", data_file)
            self.output_exc()

        self.changed = False
