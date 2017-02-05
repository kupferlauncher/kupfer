import fnmatch
import io
import pickle
import sys

class universalset (object):
    def __contains__(self, item):
        return True

class ConservativeUnpickler (pickle.Unpickler):
    """An Unpickler that refuses to import new modules

    >>> import pickle

    >>> import kupfer.objects
    >>> ConservativeUnpickler.loads(pickle.dumps(kupfer.objects.FileLeaf("A")))
    <builtin.FileLeaf A>

    >>> ConservativeUnpickler.loads(pickle.dumps(eval))
    Traceback (most recent call last):
        ...
    UnpicklingError: Refusing unsafe __builtin__.eval

    >>> import sys
    >>> import kupfer.obj.base
    >>> pdata = pickle.dumps(kupfer.obj.base.Leaf(1, "A"))
    >>> del sys.modules["kupfer.obj.base"]
    >>> ConservativeUnpickler.loads(pdata)
    Traceback (most recent call last):
        ...
    UnpicklingError: Refusing to load module kupfer.obj.base
    """
    safe_modules = {
        "builtins" : set(["set", "sum", "object"]),
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

class BasicUnpickler (ConservativeUnpickler):
    """An Unpickler that can only unpickle persistend ids and select builtins

    >>> import pickle

    >>> import kupfer.objects
    >>> BasicUnpickler.loads(pickle.dumps(kupfer.objects.FileLeaf("A")))
    Traceback (most recent call last):
        ...
    UnpicklingError: Refusing unsafe kupfer.obj.objects.FileLeaf
    """

    safe_modules = {
        "__builtin__" : set(["object"]),
        "copy_reg" : set(["_reconstructor"]),
        "kupfer.puid" : set(["SerializedObject"]),
    }

if __name__ == '__main__':
    import doctest
    doctest.testmod()
