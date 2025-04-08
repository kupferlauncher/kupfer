"""
ouuu
Debugging routines, can only be used when Kupfer is run from the Source
directory.
"""

import atexit
import gc
import inspect
import logging
import sys

logger = logging.getLogger(__name__)


def get_size(obj, seen=None):
    """Recursively finds size of objects in bytes

    from/based on: https://github.com/bosswissam/pysize/
    """
    try:
        size = sys.getsizeof(obj)
    except RecursionError:
        return 0

    if seen is None:
        seen = set()

    obj_id = id(obj)
    if obj_id in seen:
        return 0

    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if hasattr(obj, "__dict__"):
        for cls in obj.__class__.__mro__:
            if "__dict__" in cls.__dict__:
                d = cls.__dict__["__dict__"]
                if inspect.isgetsetdescriptor(d) or inspect.ismemberdescriptor(
                    d
                ):
                    size += get_size(obj.__dict__, seen)

                break

    if isinstance(obj, dict):
        size += sum((get_size(v, seen) for v in obj.values()))
        size += sum((get_size(k, seen) for k in obj))

    elif hasattr(obj, "__iter__") and not isinstance(
        obj, (str, bytes, bytearray)
    ):
        try:
            size += sum((get_size(i, seen) for i in obj))
        except TypeError:
            logger.exception("Unable to get size of %r.", obj)

    if hasattr(obj, "__slots__"):  # can have __slots__ with __dict__
        size += sum(
            get_size(getattr(obj, s), seen)
            for s in obj.__slots__
            if hasattr(obj, s)
        )

    return size


def mem_stats():
    print("DEBUG: OBJ STATS")

    print("enabled:", gc.isenabled())
    print("objs", len(gc.get_objects()))
    print("collected (now)", gc.collect())

    # after collection
    hist = {}
    for obj in gc.get_objects():
        key = str(type(obj))
        if key not in hist:
            hist[key] = 1
        else:
            hist[key] += 1

    best = list(hist.items())
    best.sort(key=lambda x: x[1], reverse=True)
    print("\n".join(f"{k}: {v}" for k, v in best[:10]))

    our = []
    gtk = []
    for item in best:
        if "objects." in item[0] or "kupfer." in item[0]:
            our.append(item)

        if "gtk" in item[0]:
            gtk.append(item)

    # print "---just gtk (top)"
    # print "\n".join("%s: %d" % (k,v) for k,v in gtk[:10])
    print("---Just our objects (all > 1)")
    print("\n".join(f"{k}: {v}" for k, v in our if v > 1))
    print("---------------------\n")


def make_histogram(vect, nbins=7):
    """make a histogram out of @vect"""
    _mi, ma = 0, max(vect)
    bins = [0] * nbins
    bin_size = ma / nbins + 1

    def brange(i):
        return range(i * bin_size, (i + 1) * bin_size)

    for acc in vect:
        for i in range(nbins):
            if acc in brange(i):
                bins[i] += 1
                break
    # headers
    print(
        " ".join(
            "%10s" % f"[{min(brange(i)):2d}, {max(brange(i)):2d}]"
            for i in range(nbins)
        )
    )
    print(" ".join(f"{bins[i]:10d}" for i in range(nbins)))
    print("---------------------\n")


def icon_stats():
    from kupfer import icons

    print("DEBUG: ICON STATS")
    print("size:", len(icons._ICON_CACHE))  # noqa:SLF001
    for size, key in icons._ICON_CACHE:  # noqa:SLF001,
        print("  ", size, key)

    print("---------------------\n")


def learn_stats():
    from kupfer.core.learn import _ACTIVATIONS_KEY, _CORRELATION_KEY, _REGISTER

    print("Learn _REGISTER:")
    for k, v in _REGISTER.items():
        if k not in (_CORRELATION_KEY, _ACTIVATIONS_KEY):
            print(f"  {k}: {v}")

    if _CORRELATION_KEY in _REGISTER:
        print("------")
        print("Correlations:")
        for k, v in _REGISTER[_CORRELATION_KEY].items():  # type: ignore
            print(f"  {k}: {v}")

    if _ACTIVATIONS_KEY in _REGISTER:
        print("------")
        print("Activations:")
        for k, v in _REGISTER[_ACTIVATIONS_KEY].items():  # type: ignore
            print(f"  {k}: {v}")

    print("---------------------\n")


def cache_stats():
    import functools
    import gc

    from kupfer.support.datatools import LruCache, simple_cache

    print("Cache")
    for obj in gc.get_objects():
        if isinstance(obj, (LruCache, simple_cache)):
            print(str(obj), get_size(obj))

    print("\nfunctools.*cache")
    for obj in gc.get_objects():
        if isinstance(obj, functools._lru_cache_wrapper):  # noqa:SLF001
            print(
                obj.__wrapped__.__module__,
                obj.__wrapped__.__name__,
                obj.cache_info(),
                get_size(obj),
            )

    print("---------------------\n")


def opened_files():
    try:
        import psutil
    except ImportError:
        return

    print("Opened files")
    for file in psutil.Process().open_files():
        print(str(file))

    print("---------------------\n")


def install():
    """Install atexit handlers for debug information"""
    atexit.register(opened_files)
    atexit.register(mem_stats)
    atexit.register(icon_stats)
    atexit.register(learn_stats)
    atexit.register(cache_stats)
