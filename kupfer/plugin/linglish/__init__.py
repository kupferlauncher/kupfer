# encoding: utf-8

try:
	# ast module only available in Python 2.6
	import ast
	ast_eval = ast.literal_eval
except ImportError:
	ast_eval = eval

import dbus

from kupfer.objects import Action, Source, Leaf, TextLeaf
from kupfer import icons, plugin_support
from kupfer import pretty

from kupfer.plugin.linglish import find

__kupfer_name__ = _("D-Bus Introspection")
__kupfer_sources__ = ("NameSource", )
__kupfer_actions__ = ()
__description__ = ""
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

plugin_support.check_dbus_connection()

def _get_dbus_interface(activate=False):
	"""Return the dbus proxy object for our Note Application.

	if @activate, we will activate it over d-bus (start if not running)
	"""
	bus = dbus.SessionBus()
	proxy_obj = bus.get_object('org.freedesktop.DBus',
			'/org/freedesktop/DBus')
	dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
	return dbus_iface

class BusName (Leaf):
	def has_content(self):
		return True
	def content_source(self, alternate=False):
		return ObjectsSource(self.object)

class NameSource (Source):
	_name_blacklist = [
		# if we introspect on self, we hang, since we make sync calls
		"se.kaizer.kupfer",
	]
	def __init__(self):
		Source.__init__(self, _("D-Bus names"))

	def get_items(self):
		dbus_object = _get_dbus_interface()
		names = dbus_object.ListNames()
		for name in names:
			if (any(character.isalpha() for character in name)
				and name not in self._name_blacklist):
				yield BusName(name, name)
	def provides(self):
		yield BusName


class Object (Leaf):
	def __init__(self, methods, object_path, bus_name):
		Leaf.__init__(self, (methods, object_path, bus_name), object_path)
	def has_content(self):
		return True
	def content_source(self, alternate=False):
		methods, object_path, bus_name = self.object
		return MethodsSource(bus_name, methods)

class ObjectsSource (Source):
	def __init__(self, name):
		Source.__init__(self, _("Objects for %s") % name)
		self.bus_name = name
	def get_items(self):
		bus = dbus.Bus()
		objects = find.get_objects(bus, self.bus_name)
		for obj in objects:
			yield Object(objects[obj], obj, self.bus_name)

class Signal (Leaf):
	def get_icon_name(self):
		return "dialog-question"

class Method (Leaf):
	"repr object is a name, args tuple"
	def __init__(self, bus_name, object_path, iface_name, method, name):
		Leaf.__init__(self, method, name)
		self.bus_name = bus_name
		self.object_path = object_path
		self.iface_name = iface_name

	def get_actions(self):
		name, arguments = self.object
		in_parameters = [A for A in arguments if A[1] == "in"]
		if not in_parameters:
			yield Call()
		else:
			yield CallWithArguments()

	def get_description(self):
		name, arguments = self.object
		# make a brief description
		in_parameters = [A for A in arguments if A[1] == "in"]
		out_parameters = [A for A in arguments if A[1] == "out"]
		if not in_parameters and not out_parameters:
			return None
		ilist = ", ".join("%s:%s" % (A[2], A[0]) for A in in_parameters)
		olist = ", ".join("%s:%s" % (A[2], A[0]) for A in out_parameters)
		return u"%s → %s" % (ilist, olist)

	def get_icon_name(self):
		return "emblem-system"

class MethodsSource (Source):
	def __init__(self, bus_name, infodict):
		Source.__init__(self, _("Methods for %s") % bus_name)
		self.bus_name = bus_name
		self.info = infodict
	def get_items(self):
		bus_name = self.bus_name
		obj_path = self.info["path"]
		for interface in self.info["interfaces"]:
			for method in self.info["interfaces"][interface]["methods"]:
				name, args = method
				yield Method(bus_name, obj_path, interface, method, name)
			for signal in self.info["interfaces"][interface]["signals"]:
				yield Signal(signal, signal)

	def provides(self):
		yield Method
		yield Signal

def parse_argument_tuple(ustr):
	""" Return a parsed tuple if successful, else None """
	try:
		parsed_arguments = ast_eval(ustr)
	except Exception, exc:
		return None
	if not hasattr(parsed_arguments, "__iter__"):
		parsed_arguments = (parsed_arguments, )
	return parsed_arguments

def text_from_result(result, out_parameters):
	if len(out_parameters) == 1 and out_parameters[0][-1] == "s":
		rettext = unicode(result)
	elif len(out_parameters) == 1 and out_parameters[0][-1] == "i":
		rettext = unicode(int(result))
	else:
		rettext = repr(result)
	return rettext


class Call (Action):
	def __init__(self):
		Action.__init__(self, _("Call Method"))
	def has_result(self):
		return True

	def activate(self, leaf):
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object(leaf.bus_name, leaf.object_path)
		dbus_iface = dbus.Interface(proxy_obj, leaf.iface_name)
		name, arguments = leaf.object
		method = dbus_iface.get_dbus_method(name)
		in_parameters = [A for A in arguments if A[1] == "in"]
		out_parameters = [A for A in arguments if A[1] == "out"]
		ret = method()
		if ret:
			return TextLeaf(text_from_result(ret, out_parameters))

class CallWithArguments (Action):
	def __init__(self):
		Action.__init__(self, _("Call with Arguments..."))
	def has_result(self):
		return True

	def activate(self, leaf, iobj):
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object(leaf.bus_name, leaf.object_path)
		dbus_iface = dbus.Interface(proxy_obj, leaf.iface_name)
		name, arguments = leaf.object
		method = dbus_iface.get_dbus_method(name)
		in_parameters = [A for A in arguments if A[1] == "in"]
		out_parameters = [A for A in arguments if A[1] == "out"]
		parsed_arguments = parse_argument_tuple(iobj.object)
		ret = method(*parsed_arguments)
		if ret:
			return TextLeaf(text_from_result(ret, out_parameters))
	
	def requires_object(self):
		return True
	def object_types(self):
		yield TextLeaf
	def valid_object(self, iobj, for_item):
		name, arguments = for_item.object
		in_parameters = [A for A in arguments if A[1] == "in"]
		parsed_arguments = parse_argument_tuple(iobj.object)
		if (not parsed_arguments or
			len(parsed_arguments) != len(in_parameters)):
			return False
		return True

	def get_description(self):
		return _("Arguments expected as a python tuple of literals")
