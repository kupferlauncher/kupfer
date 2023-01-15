import fnmatch
import io
import pickle
import sys
import typing as ty


# pylint: disable=too-few-public-methods
class UniversalSet:
    def __contains__(self, item: ty.Any) -> bool:
        return True


class ConservativeUnpickler(pickle.Unpickler):
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

    safe_modules: ty.Dict[str, ty.Any] = {
        "builtins": {"set", "sum", "object"},
        "copy_reg": {"_reconstructor"},
        "kupfer.*": UniversalSet(),
    }

    @classmethod
    def is_safe_symbol(cls, module: str, name: str) -> bool:
        for pattern, modules in cls.safe_modules.items():
            if fnmatch.fnmatchcase(module, pattern):
                return name in modules

        return False

    def find_class(self, module: str, name: str) -> ty.Any:
        if module not in sys.modules:
            raise pickle.UnpicklingError(f"Refusing to load module {module}")

        if not self.is_safe_symbol(module, name):
            raise pickle.UnpicklingError(f"Refusing unsafe {module}.{name}")

        return pickle.Unpickler.find_class(self, module, name)

    @classmethod
    def loads(cls, pickledata: bytes) -> ty.Any:
        unpickler = cls(io.BytesIO(pickledata))
        return unpickler.load()


class BasicUnpickler(ConservativeUnpickler):
    """An Unpickler that can only unpickle persistend ids and select builtins

    >>> import pickle

    >>> import kupfer.objects
    >>> BasicUnpickler.loads(pickle.dumps(kupfer.objects.FileLeaf("A")))
    Traceback (most recent call last):
        ...
    UnpicklingError: Refusing unsafe kupfer.obj.objects.FileLeaf
    """

    safe_modules: ty.Dict[str, ty.Set[str]] = {
        "__builtin__": {"object"},
        "copy_reg": {"_reconstructor"},
        "kupfer.puid": {"SerializedObject"},
    }


if __name__ == "__main__":
    import doctest

    doctest.testmod()
