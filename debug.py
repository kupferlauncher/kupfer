"""
ouuu
Debugging routines, can only be used when Kupfer is run from the Source
directory.
"""
import atexit
import gc


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
    mi, ma = 0, max(vect)
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
            "%10s" % ("[%2d, %2d)" % (min(brange(i)), max(brange(i))),)
            for i in range(nbins)
        )
    )
    print(" ".join("%10d" % bins[i] for i in range(nbins)))
    print("---------------------\n")


def icon_stats():
    from kupfer.icons import _ICON_CACHE, _MISSING_ICON_FILES

    print("DEBUG: ICON STATS")
    for size, data in _ICON_CACHE.items():
        print("size:", size)
        print("Cached icons:", len(data))
        print("Cached icon keys:")
        for key in data.keys():
            print("  ", key)

    print("missing icon files: ", _MISSING_ICON_FILES)
    print("---------------------\n")


def learn_stats():
    from kupfer.core.learn import _REGISTER

    print("Learn _REGISTER:")
    for k, v in _REGISTER.items():
        print(f"  {k}: {v}")
    print("---------------------\n")


def cache_stats():
    import gc
    import functools

    from kupfer.support.datatools import LruCache, simple_cache

    print("Cache")
    for obj in gc.get_objects():
        if isinstance(obj, (LruCache, simple_cache)):
            print(str(obj))

    print("\nfunctools.*cache")
    for obj in gc.get_objects():
        if isinstance(obj, functools._lru_cache_wrapper):
            print(
                obj.__wrapped__.__module__,
                obj.__wrapped__.__name__,
                obj.cache_info(),
            )

    print("---------------------\n")


def install():
    """Install atexit handlers for debug information"""
    atexit.register(mem_stats)
    atexit.register(icon_stats)
    atexit.register(learn_stats)
    atexit.register(cache_stats)
