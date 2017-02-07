"""
Debugging routines, can only be used when Kupfer is run from the Source
directory.
"""

import atexit

def mem_stats():
    import gc
    print("DEBUG: OBJ STATS")

    print("enabled:", gc.isenabled())
    print("objs", len(gc.get_objects()))
    print("collected (now)", gc.collect())

    # after collection
    hist = {}
    for obj in gc.get_objects():
        key = str(type(obj))
        if key not in hist:
            hist[key] =1
        else:
            hist[key] += 1
    
    best = list(hist.items())
    best.sort(key=lambda x:x[1], reverse=True)
    print("\n".join("%s: %d" % (k,v) for k,v in best[:10]))

    our = []
    gtk = []
    for item in best:
        if "objects." in item[0] or "kupfer." in item[0]:
            our.append(item)
        if "gtk" in item[0]:
            gtk.append(item)
    
    #print "---just gtk (top)"
    #print "\n".join("%s: %d" % (k,v) for k,v in gtk[:10])
    print("---Just our objects (all > 1)")
    print("\n".join("%s: %d" % (k,v) for k,v in our if v > 1))

def make_histogram(vect, nbins=7):
    """make a histogram out of @vect"""
    mi,ma = 0, max(vect)
    bins = [0]*nbins
    bin_size = ma/nbins + 1
    def brange(i):
        return range(i*bin_size, (i+1)*bin_size)
    for acc in vect:
        for i in range(nbins):
            if acc in brange(i):
                bins[i] += 1
                break
    # headers
    print(" ".join("%10s" % ("[%2d, %2d)" % (min(brange(i)), max(brange(i))),) for i in range(nbins)))
    print(" ".join("%10d" % bins[i] for i in range(nbins)))
    

def icon_stats():
    from kupfer.icons import icon_cache
    print("DEBUG: ICON STATS")

    c = 0
    tot_acc = 0
    tot_pix = 0
    acc_vect = []
    for size in icon_cache:
        for k in icon_cache[size]:
            rec = icon_cache[size][k]
            acc = rec["accesses"]
            acc_vect.append(acc)
            if not acc:
                c += 1
            tot_acc += acc
            icon = rec["icon"]
            tot_pix += icon.get_height() * icon.get_width()
        print("Cached icons:",  len(icon_cache[size]))
        print("Unused cache entries", c)
        print("Total accesses", tot_acc)
        print(make_histogram(acc_vect))
        print("Sum pixels", tot_pix)
        print("Cached icon keys:")
        for k in sorted(icon_cache[size],
                key=lambda k: icon_cache[size][k]["accesses"]):
            print(k, icon_cache[size][k]["accesses"])

def install():
    """Install atexit handlers for debug information"""
    atexit.register(mem_stats)
    #atexit.register(icon_stats)
