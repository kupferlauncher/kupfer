import sys
from gi.repository import Gtk as gtk
#import gtk

def tohex(c):
   #Convert to hex string
   #little hack to fix bug
   s = ['#',hex(int(c[0]*256))[2:].zfill(2),hex(int(c[1]*256))[2:].zfill(2),hex(int(c[2]*256))[2:].zfill(2)]
   for item in enumerate(s):
      if item[1]=='100':
         s[item[0]]='ff'
   #print s
   return ''.join(s)

def getColor():
	csd = gtk.ColorSelectionDialog('Select Colour')
	response = csd.run()
	if response == gtk.ResponseType.CANCEL:
		print("Cancel hit")
		csd.destroy()
		return None
	else:
		print("Selected new color")
	csd.hide()
	cs = csd.get_color_selection()
	c = cs.get_current_color()
	csd.destroy()		
	hexColor = tohex((c.red/65536.0, c.green/65536.0, c.blue/65536.0))
	return (round(c.red/65536*255), round(c.green/65536*255), round(c.blue/65536*255))