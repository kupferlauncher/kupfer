"""
Debugging routines. To use this, simply import this module
"""

import atexit

def mem_stats():
	import gc
	print "DEBUG: OBJ STATS"

	print "enabled:", gc.isenabled()
	print "objs", len(gc.get_objects())
	print "collected (now)", gc.collect()

	# after collection
	hist = {}
	for obj in gc.get_objects():
		key = str(type(obj))
		if key not in hist:
			hist[key] =1
		else:
			hist[key] += 1
	
	best = hist.items()
	best.sort(key=lambda x:x[1], reverse=True)
	print "\n".join("%s: %d" % (k,v) for k,v in best[:10])

	our = []
	gtk = []
	for item in best:
		if "objects." in item[0] or "kupfer." in item[0]:
			our.append(item)
		if "gtk" in item[0]:
			gtk.append(item)
	
	print "---just gtk (top)"
	print "\n".join("%s: %d" % (k,v) for k,v in gtk[:10])
	print "---Just our objects (all)"
	print "\n".join("%s: %d" % (k,v) for k,v in our)

def icon_stats():
	from kupfer.icons import icon_cache
	print "DEBUG: ICON STATS"

	c = 0
	tot_acc = 0
	tot_pix = 0
	for k in icon_cache:
		rec = icon_cache[k]
		acc = rec["accesses"]
		if not acc:
			c += 1
		tot_acc += acc
		icon = rec["icon"]
		tot_pix += icon.get_height() * icon.get_width()
	print "Cached icons:",  len(icon_cache)
	print "Unused cache entries", len(icon_cache) -c
	print "Total accesses", tot_acc
	print "Sum pixels", tot_pix

atexit.register(mem_stats)
atexit.register(icon_stats)
