"""
Debugging routines. To use this, simply import this module
"""

import atexit

def mem_stats():
	import gc
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
	for item in best:
		if "objects." in item[0] or "kupfer." in item[0]:
			our.append(item)
	
	print "---Just our objects"
	print "\n".join("%s: %d" % (k,v) for k,v in our)


atexit.register(mem_stats)
