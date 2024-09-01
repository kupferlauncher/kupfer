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
        self._accels: dict[str, str] = {}
        # is configuration loaded
        self._loaded: bool = False
        # is configuration changed and not saved
        self._changed: bool = False

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
        if self._loaded:
            return True

        self._loaded = True
        data_file = self._filename()
        if data_file is None:
            return False

        self._accels.clear()

        try:
            with open(data_file, encoding="UTF-8") as dfp:
                accels = json.load(dfp)

            self.output_debug("Read", data_file)
        except FileNotFoundError:
            return False
        except Exception:
            self.output_error("Failed to read:", data_file)
            self.output_exc()
            return False

        try:
            self._valid_accel(accels, validate_func)
        except Exception:
            self.output_exc()

        self.output_debug("Loaded", self._accels)
        return True

    def _valid_accel(
        self, accels: dict[ty.Any, ty.Any], validate_func: AcceleratorValidator
    ) -> None:
        """Validate loaded data."""
        if not isinstance(self._accels, dict):
            raise TypeError("Accelerators must be a dictionary")

        for obj, key in accels.items():
            # make sure object and key are strings
            key = str(key)  # noqa:PLW2901
            if validate_func(key):
                self._accels[str(obj)] = key
            else:
                self.output_error("Ignoring invalid accel", key, "for", obj)

    def get(self, obj: ty.Any) -> str | None:
        """Return accel key for @obj or None"""
        return self._accels.get(_repr_key(obj))

    def set(self, obj: ty.Any, key: str) -> None:
        """Set accelerator `key` for `obj`."""
        self.output_debug("Set", key, "for", _repr_key(obj))
        assert hasattr(obj, "activate")
        assert isinstance(key, str)
        self._accels[_repr_key(obj)] = key
        self._changed = True

    def store(self) -> None:
        """Write all accelerator into configuration file."""
        if not self._changed:
            return

        data_file = self._filename()
        if data_file is None:
            return

        self.output_debug("Writing to", data_file)
        try:
            with open(data_file, "w", encoding="UTF-8") as dfp:
                json.dump(self._accels, dfp, indent=4, sort_keys=True)

        except Exception:
            self.output_error("Failed to write:", data_file)
            self.output_exc()

        self._changed = False
