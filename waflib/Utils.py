#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Utilities and platform-specific fixes

The portability fixes try to provide a consistent behavior of the Waf API
through Python versions 2.3 to 3.X and across different platforms (win32, linux, etc)
"""

import os, sys, errno, traceback, inspect, re, shutil, datetime, gc
try:
	import subprocess
except:
	try:
		import waflib.extras.subprocess as subprocess
	except:
		print("The subprocess module is missing (python2.3?):\n try calling 'waf update --files=subprocess'\n or add a copy of subprocess.py to the python libraries")

try:
	from collections import deque
except ImportError:
	class deque(list):
		"""A deque for Python 2.3 which does not have one"""
		def popleft(self):
			return self.pop(0)
try:
	import _winreg as winreg
except:
	try:
		import winreg
	except:
		winreg = None

from waflib import Errors

try:
	from collections import UserDict
except:
	from UserDict import UserDict

try:
	from hashlib import md5
except:
	try:
		from md5 import md5
	except:
		# never fail to enable fixes from another module
		pass

try:
	import threading
except:
	class threading(object):
		"""
			A fake threading class for platforms lacking the threading module.
			Use ``waf -j1`` on those platforms
		"""
		pass
	class Lock(object):
		"""Fake Lock class"""
		def acquire(self):
			pass
		def release(self):
			pass
	threading.Lock = threading.Thread = Lock
else:
	run_old = threading.Thread.run
	def run(*args, **kwargs):
		try:
			run_old(*args, **kwargs)
		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			sys.excepthook(*sys.exc_info())
	threading.Thread.run = run

SIG_NIL = 'iluvcuteoverload'.encode()
"""Arbitrary null value for a md5 hash. This value must be changed when the hash value is replaced (size)"""

O644 = 420
"""Constant representing the permissions for regular files (0644 raises a syntax error on python 3)"""

O755 = 493
"""Constant representing the permissions for executable files (0755 raises a syntax error on python 3)"""

rot_chr = ['\\', '|', '/', '-']
"List of characters to use when displaying the throbber (progress bar)"

rot_idx = 0
"Index of the current throbber character (progress bar)"

try:
	from collections import defaultdict
except ImportError:
	class defaultdict(dict):
		"""
		defaultdict was introduced in python 2.5, so we leave it for python 2.4 and 2.3
		"""
		def __init__(self, default_factory):
			super(defaultdict, self).__init__()
			self.default_factory = default_factory
		def __getitem__(self, key):
			try:
				return super(defaultdict, self).__getitem__(key)
			except KeyError:
				value = self.default_factory()
				self[key] = value
				return value

is_win32 = sys.platform in ('win32', 'cli')

# we should have put this in the Logs.py file instead :-/
indicator = '\x1b[K%s%s%s\r'
if is_win32 and 'NOCOLOR' in os.environ:
	indicator = '%s%s%s\r'

def readf(fname, m='r'):
	"""
	Read an entire file into a string, in practice the wrapper
	node.read(..) should be used instead of this method::

		def build(ctx):
			from waflib import Utils
			txt = Utils.readf(self.path.find_node('wscript').abspath())
			txt = ctx.path.find_node('wscript').read()

	:type  fname: string
	:param fname: Path to file
	:type  m: string
	:param m: Open mode
	:rtype: string
	:return: Content of the file
	"""
	try:
		with open(fname, m) as f:
			return f.read()
	except UnicodeDecodeError:
		with open(fname, m, encoding='utf-8') as f:
			return f.read()

def h_file(filename):
	"""
	Compute a hash value for a file by using md5. This method may be replaced by
	a faster version if necessary. The following uses the file size and the timestamp value::

		import stat
		from waflib import Utils
		def h_file(filename):
			st = os.stat(filename)
			if stat.S_ISDIR(st[stat.ST_MODE]): raise IOError('not a file')
			m = Utils.md5()
			m.update(str(st.st_mtime))
			m.update(str(st.st_size))
			m.update(filename)
			return m.digest()
		Utils.h_file = h_file

	:type filename: string
	:param filename: path to the file to hash
	:return: hash of the file contents
	"""
	f = open(filename, 'rb')
	m = md5()
	try:
		while filename:
			filename = f.read(100000)
			m.update(filename)
	finally:
		f.close()
	return m.digest()

try:
	x = ''.encode('hex')
except:
	import binascii
	def to_hex(s):
		ret = binascii.hexlify(s)
		if not isinstance(ret, str):
			ret = ret.decode('utf-8')
		return ret
else:
	def to_hex(s):
		return s.encode('hex')

to_hex.__doc__ = """
Return the hexadecimal representation of a string

:param s: string to convert
:type s: string
"""

listdir = os.listdir
if is_win32:
	def listdir_win32(s):
		"""
		List the contents of a folder in a portable manner.

		:type s: string
		:param s: a string, which can be empty on Windows for listing the drive letters
		"""
		if not s:
			try:
				import ctypes
			except:
				# there is nothing much we can do
				return [x + ':\\' for x in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')]
			else:
				dlen = 4 # length of "?:\\x00"
				maxdrives = 26
				buf = ctypes.create_string_buffer(maxdrives * dlen)
				ndrives = ctypes.windll.kernel32.GetLogicalDriveStringsA(maxdrives, ctypes.byref(buf))
				return [ buf.raw[4*i:4*i+3].decode('ascii') for i in range(int(ndrives/dlen)) ]

		if len(s) == 2 and s[1] == ":":
			s += os.sep

		if not os.path.isdir(s):
			e = OSError()
			e.errno = errno.ENOENT
			raise e
		return os.listdir(s)
	listdir = listdir_win32

def num2ver(ver):
	"""
	Convert a string, tuple or version number into an integer. The number is supposed to have at most 4 digits::

		from waflib.Utils import num2ver
		num2ver('1.3.2') == num2ver((1,3,2)) == num2ver((1,3,2,0))

	:type ver: string or tuple of numbers
	:param ver: a version number
	"""
	if isinstance(ver, str):
		ver = tuple(ver.split('.'))
	if isinstance(ver, tuple):
		ret = 0
		for i in range(4):
			if i < len(ver):
				ret += 256**(3 - i) * int(ver[i])
		return ret
	return ver

def ex_stack():
	"""
	Extract the stack to display exceptions

	:return: a string represening the last exception
	"""
	exc_type, exc_value, tb = sys.exc_info()
	exc_lines = traceback.format_exception(exc_type, exc_value, tb)
	return ''.join(exc_lines)

def to_list(sth):
	"""
	Convert a string argument to a list by splitting on spaces, and pass
	through a list argument unchanged::

		from waflib.Utils import to_list
		lst = to_list("a b c d")

	:param sth: List or a string of items separated by spaces
	:rtype: list
	:return: Argument converted to list

	"""
	if isinstance(sth, str):
		return sth.split()
	else:
		return sth

re_nl = re.compile('\r*\n', re.M)
def str_to_dict(txt):
	"""
	Parse a string with key = value pairs into a dictionary::

		from waflib import Utils
		x = Utils.str_to_dict('''
			a = 1
			b = test
		''')

	:type  s: string
	:param s: String to parse
	:rtype: dict
	:return: Dictionary containing parsed key-value pairs
	"""
	tbl = {}

	lines = re_nl.split(txt)
	for x in lines:
		x = x.strip()
		if not x or x.startswith('#') or x.find('=') < 0:
			continue
		tmp = x.split('=')
		tbl[tmp[0].strip()] = '='.join(tmp[1:]).strip()
	return tbl

def split_path(path):
	return path.split('/')

def split_path_cygwin(path):
	if path.startswith('//'):
		ret = path.split('/')[2:]
		ret[0] = '/' + ret[0]
		return ret
	return path.split('/')

re_sp = re.compile('[/\\\\]')
def split_path_win32(path):
	if path.startswith('\\\\'):
		ret = re.split(re_sp, path)[2:]
		ret[0] = '\\' + ret[0]
		return ret
	return re.split(re_sp, path)

if sys.platform == 'cygwin':
	split_path = split_path_cygwin
elif is_win32:
	split_path = split_path_win32

split_path.__doc__ = """
Split a path by / or \\. This function is not like os.path.split

:type  path: string
:param path: path to split
:return:     list of strings
"""

def check_dir(path):
	"""
	Ensure that a directory exists (similar to ``mkdir -p``).

	:type  dir: string
	:param dir: Path to directory
	"""
	if not os.path.isdir(path):
		try:
			os.makedirs(path)
		except OSError as e:
			if not os.path.isdir(path):
				raise Errors.WafError('Cannot create the folder %r' % path, ex=e)

def def_attrs(cls, **kw):
	"""
	Set default attributes on a class instance

	:type cls: class
	:param cls: the class to update the given attributes in.
	:type kw: dict
	:param kw: dictionary of attributes names and values.
	"""
	for k, v in kw.items():
		if not hasattr(cls, k):
			setattr(cls, k, v)

def quote_define_name(s):
	"""
	Convert a string to an identifier suitable for C defines.

	:type  s: string
	:param s: String to convert
	:rtype: string
	:return: Identifier suitable for C defines
	"""
	fu = re.compile("[^a-zA-Z0-9]").sub("_", s)
	fu = fu.upper()
	return fu

def h_list(lst):
	"""
	Hash lists. For tuples, using hash(tup) is much more efficient

	:param lst: list to hash
	:type lst: list of strings
	:return: hash of the list
	"""
	m = md5()
	m.update(str(lst).encode())
	return m.digest()

def h_fun(fun):
	"""
	Hash functions

	:param fun: function to hash
	:type  fun: function
	:return: hash of the function
	"""
	try:
		return fun.code
	except AttributeError:
		try:
			h = inspect.getsource(fun)
		except IOError:
			h = "nocode"
		try:
			fun.code = h
		except AttributeError:
			pass
		return h

reg_subst = re.compile(r"(\\\\)|(\$\$)|\$\{([^}]+)\}")
def subst_vars(expr, params):
	"""
	Replace ${VAR} with the value of VAR taken from a dict or a config set::

		from waflib import Utils
		s = Utils.subst_vars('${PREFIX}/bin', env)

	:type  expr: string
	:param expr: String to perform substitution on
	:param params: Dictionary or config set to look up variable values.
	"""
	def repl_var(m):
		if m.group(1):
			return '\\'
		if m.group(2):
			return '$'
		try:
			# ConfigSet instances may contain lists
			return params.get_flat(m.group(3))
		except AttributeError:
			return params[m.group(3)]
	return reg_subst.sub(repl_var, expr)

def destos_to_binfmt(key):
	"""
	Return the binary format based on the unversioned platform name.

	:param key: platform name
	:type  key: string
	:return: string representing the binary format
	"""
	if key == 'darwin':
		return 'mac-o'
	elif key in ('win32', 'cygwin', 'uwin', 'msys'):
		return 'pe'
	return 'elf'

def unversioned_sys_platform():
	"""
	Return the unversioned platform name.
	Some Python platform names contain versions, that depend on
	the build environment, e.g. linux2, freebsd6, etc.
	This returns the name without the version number. Exceptions are
	os2 and win32, which are returned verbatim.

	:rtype: string
	:return: Unversioned platform name
	"""
	s = sys.platform
	if s == 'java':
		# The real OS is hidden under the JVM.
		from java.lang import System
		s = System.getProperty('os.name')
		# see http://lopica.sourceforge.net/os.html for a list of possible values
		if s == 'Mac OS X':
			return 'darwin'
		elif s.startswith('Windows '):
			return 'win32'
		elif s == 'OS/2':
			return 'os2'
		elif s == 'HP-UX':
			return 'hpux'
		elif s in ('SunOS', 'Solaris'):
			return 'sunos'
		else: s = s.lower()
	
	# powerpc == darwin for our purposes
	if s == 'powerpc':
		return 'darwin'
	if s == 'win32' or s.endswith('os2') and s != 'sunos2': return s
	return re.split('\d+$', s)[0]

def nada(*k, **kw):
	"""
	A function that does nothing

	:return: None
	"""
	pass

class Timer(object):
	"""
	Simple object for timing the execution of commands.
	Its string representation is the current time::

		from waflib.Utils import Timer
		timer = Timer()
		a_few_operations()
		s = str(timer)
	"""
	def __init__(self):
		self.start_time = datetime.datetime.utcnow()

	def __str__(self):
		delta = datetime.datetime.utcnow() - self.start_time
		days = int(delta.days)
		hours = delta.seconds // 3600
		minutes = (delta.seconds - hours * 3600) // 60
		seconds = delta.seconds - hours * 3600 - minutes * 60 + float(delta.microseconds) / 1000 / 1000
		result = ''
		if days:
			result += '%dd' % days
		if days or hours:
			result += '%dh' % hours
		if days or hours or minutes:
			result += '%dm' % minutes
		return '%s%.3fs' % (result, seconds)

if is_win32:
	old = shutil.copy2
	def copy2(src, dst):
		"""
		shutil.copy2 does not copy the file attributes on windows, so we
		hack into the shutil module to fix the problem
		"""
		old(src, dst)
		shutil.copystat(src, dst)
	setattr(shutil, 'copy2', copy2)

if os.name == 'java':
	# Jython cannot disable the gc but they can enable it ... wtf?
	try:
		gc.disable()
		gc.enable()
	except NotImplementedError:
		gc.disable = gc.enable

def read_la_file(path):
	"""
	Read property files, used by msvc.py

	:param path: file to read
	:type path: string
	"""
	sp = re.compile(r'^([^=]+)=\'(.*)\'$')
	dc = {}
	for line in readf(path).splitlines():
		try:
			_, left, right, _ = sp.split(line.strip())
			dc[left] = right
		except ValueError:
			pass
	return dc

def nogc(fun):
	"""
	Decorator: let a function disable the garbage collector during its execution.
	It is used in the build context when storing/loading the build cache file (pickle)

	:param fun: function to execute
	:type fun: function
	:return: the return value of the function executed
	"""
	def f(*k, **kw):
		try:
			gc.disable()
			ret = fun(*k, **kw)
		finally:
			gc.enable()
		return ret
	f.__doc__ = fun.__doc__
	return f

def run_once(fun):
	"""
	Decorator: let a function cache its results, use like this::

		@run_once
		def foo(k):
			return 345*2343

	:param fun: function to execute
	:type fun: function
	:return: the return value of the function executed
	"""
	cache = {}
	def wrap(k):
		try:
			return cache[k]
		except KeyError:
			ret = fun(k)
			cache[k] = ret
			return ret
	wrap.__cache__ = cache
	return wrap

def get_registry_app_path(key, filename):
	if not winreg:
		return None
	try:
		result = winreg.QueryValue(key, "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\%s.exe" % filename[0])
	except WindowsError:
		pass
	else:
		if os.path.isfile(result):
			return result

