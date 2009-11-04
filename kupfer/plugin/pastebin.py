from kupfer.objects import Source, Action, TextLeaf , Leaf
from kupfer import utils, icons
import urllib, os, sys, re

__kupfer_name__ = "Pastebin"
__kupfer_actions__ = ("PasteIt", )
__description__ = ("Paste text in pastebin")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

website="http://pastebin.com"

_LANGUAGES = {
		'None': 		'Simple Text',
		'bash':			'Bash',
		'c':			'C',
		'cpp': 			'C++',
		'html4strict':		'HTML',
		'java':			'Java',
		'javascript':		'Javascript',
		'lua':			'Lua',
		'perl':			'Perl',
		'php':			'PHP',	
		'python':		'Python',
		'ruby':			'Ruby'	
}

class PasteIt (Action):
	def __init__(self):
		Action.__init__(self, "Paste It")
	def activate(self, leaf, iobj):
		text = leaf.object
		#user="user"
		params=self.getParameters(website,text,iobj.object,user="") #Get the parameters array
		params=urllib.urlencode(params) #Convert to a format usable with the HTML POST
		print params

		page=urllib.urlopen(website+'/',params) #Send the informations and be redirected to the final page
		#print page.url
		return TextLeaf(page.url)
		
	def item_types(self):
		yield TextLeaf
	def valid_for_item(self, leaf):
		text = leaf.object
		return text
	def get_description(self):
		return "Paste text in pastebin.com"

	def get_gicon(self):
		return icons.ComposedIcon(self.get_icon_name(), "gtk-paste")
	
	def has_result(self):
		return True



	def getParameters(self,website,content,code,user):
		params={
			#'poster':user
			'code2':content,
			'parent_pid':"",
			'format':code, #The format, for syntax hilighting
			'paste':"Send",
			'remember':"1", #Do you want a cookie ?
			'expiry':"d",	 #The expiration, f = forever
		}
	
		return params

	def requires_object(self):
		return True

	def object_types(self):
		yield LanguageLeaf

	def object_source(self, for_item=None):
		return LanguageSource()
	    
	    #params['code2']=content
	    #params['parent_pid']="" 
	    #params['format']="text" #The format, for syntax hilighting
	    #params['paste']="Send" 
	    #params['remember']="1" #Do you want a cookie ?
	    #params['expiry']="d" #The expiration, f = forever

    	    #return params

class LanguageLeaf(Leaf):
	pass

class LanguageSource (Source):
	def __init__(self):
		Source.__init__(self, "Syntax")

	def get_items(self):
		for code, name in _LANGUAGES.iteritems():
			yield LanguageLeaf(code,name)

	def provides(self):
		yield LanguageLeaf

	def should_sort_lexically(self): 
		return True
