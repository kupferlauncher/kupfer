
import json

# Action Accelerator configuration
from kupfer import config
from kupfer import pretty

_repr_key = repr

class AccelConfig(pretty.OutputMixin):
    def __init__(self):
        self.accels = {}
        self.loaded = False
        self.changed = False

    def _filename(self):
        ret = config.save_config_file("action_accels.json")
        if ret is None:
            self.output_error("Can't find XDG_CONFIG_HOME")
        return ret

    def load(self, validate_func):
        if self.loaded:
            return True
        self.loaded = True
        data_file = self._filename()
        if data_file is None:
            return False

        try:
            with open(data_file, "r") as fp:
                self.accels = json.load(fp)
            self.output_debug("Read", data_file)
        except FileNotFoundError:
            return
        except Exception as exc:
            self.output_error("Failed to read:", data_file)
            self.output_exc()
            return

        try:
            self._valid_accel(validate_func)
        except:
            self.output_exc()
            self.accels = {}
        self.output_debug("Loaded", self.accels)

    def _valid_accel(self, validate_func):
        if not isinstance(self.accels, dict):
            raise TypeError("Accelerators must be a dictionary")
        self.accels = {str(k): str(v) for k, v in self.accels.items()}
        delete = set()
        for obj, k in self.accels.items():
            if not validate_func(k):
                delete.add(obj)
                self.output_error("Ignoring invalid accel", k, "for", obj)
        for obj in delete:
            self.accels.pop(obj, None)

    def get(self, obj):
        """
        Return accel key for @obj or None
        """
        return self.accels.get(_repr_key(obj))

    def set(self, obj, key):
        self.output_debug("Set", key, "for", _repr_key(obj))
        assert hasattr(obj, "activate")
        assert isinstance(key, str)
        self.accels[_repr_key(obj)] = key
        self.changed = True

    def store(self):
        if not self.changed:
            return
        data_file = self._filename()
        if data_file is None:
            return False
        self.output_debug("Writing to", data_file)
        try:
            with open(data_file, "w") as fp:
                json.dump(self.accels, fp, indent=4, sort_keys=True)
        except Exception as exc:
            self.output_error("Failed to write:", data_file)
            self.output_exc()
        self.changed = False
