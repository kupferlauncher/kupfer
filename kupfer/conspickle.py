import fnmatch
import io
import pickle
import sys

class universalset (object):
	def __contains__(self, item):
		return True

class ConservativeUnpickler (pickle.Unpickler):
	"An Unpickler that refuses to import new modules"
	safe_modules = {
		"__builtin__" : set(["set", "sum", "object"]),
		"copy_reg" : set(["_reconstructor"]),
		"kupfer.*" : universalset(),
	}
	@classmethod
	def is_safe_symbol(cls, module, name):
		for pattern in cls.safe_modules:
			if fnmatch.fnmatchcase(module, pattern):
				return name in cls.safe_modules[pattern]
		return False

	def find_class(self, module, name):
		if module not in sys.modules:
			raise pickle.UnpicklingError("Refusing to load module %s" % module)
		if not self.is_safe_symbol(module, name):
			raise pickle.UnpicklingError("Refusing unsafe %s.%s" % (module, name))
		return pickle.Unpickler.find_class(self, module, name)

	@classmethod
	def loads(cls, pickledata):
		unpickler = cls(io.BytesIO(pickledata))
		return unpickler.load()
