# -*- coding: UTF-8 -*-

from __future__ import with_statement

import os
import re
from ConfigParser import RawConfigParser

from kupfer import pretty

__version__ = "2009-12-11"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

'''
Module provide function to read Thunderbird's address book.

Concept for mork parser from:
	- demork.py by Kumaran Santhanam
	- mork.cs from GnomeDo by Pierre Östlund
'''

RE_COLS = re.compile(r'<\s*<\(a=c\)>\s*(\/\/)?\s*(\(.+?\))\s*>')
RE_CELL = re.compile(r'\((.+?)\)')
RE_ATOM = re.compile(r'<\s*(\(.+?\))\s*>')
RE_TABLE = re.compile(
		r'\{-?(\d+):\^(..)\s*\{\(k\^(..):c\)\(s=9u?\)\s*(.*?)\}\s*(.+?)\}')
RE_ROW = re.compile(r'(-?)\s*\[(.+?)((\(.+?\)\s*)*)\]')
RE_CELL_TEXT = re.compile(r'\^(.+?)[=^](.*)')
RE_ESCAPED = re.compile(r'((\\[\$\0abtnvfr])|(\$..))')

COLS_TO_KEEP = (
		'DisplayName',
		'FirstName',
		'LastName',
		'PrimaryEmail',
		'SecondEmail'
)

class _Table(object):
	def __init__(self, tableid):
		self.tableid = tableid
		self.rows = {}

	def __repr__(self):
		return 'Table %r: %r' % (self.tableid, self.rows)

	def add_cell(self, rowid, col, atom):
		row = self.rows.get(rowid)
		if not row:
			row = self.rows[rowid] = dict()
		row[col] = _unescape_data(atom)

SPECIAL_CHARS = (
		('\\\\', '\\'),
		('\\$', '$'),
		('\\0', chr(0)),
		('\\a', chr(7)),
		('\\b', chr(8)),
		('\\t', chr(9)),
		('\\n', chr(10)),
		('\\v', chr(11)),
		('\\f', chr(12)),
		('\\r', chr(13)),
)

def _unescape_data(instr):
	for src, dst in SPECIAL_CHARS:
		instr = instr.replace(src, dst)
	return RE_ESCAPED.sub(lambda x:chr(int(x.group()[1:], 16)), instr)


def _read_mork(filename):
	''' Read mork file, return tables from file '''
	data = []
	with open(filename, 'rt') as mfile:
		header = mfile.readline().strip()
		# check header
		if not re.match(r'// <!-- <mdb:mork:z v="(.*)"/> -->', header):
			pretty.print_debug(__name__, '_read_mork: header error', header)
			return {}

		for line in mfile.readlines():
			# remove blank lines and comments
			line = line.strip()
			if not line:
				continue

			# remove comments
			comments = line.find('//')
			if comments > -1:
				line = line[:comments].strip()
			
			if line:
				data.append(line)

		data = ''.join(data)

	if not data:
		return {}

	# decode data
	cells = {}
	atoms = {}
	tables = {}
	pos = 0
	while data:
		data = data[pos:].lstrip()
		if not data:
			break

		# cols
		match = RE_COLS.match(data)
		if match:
			for cell in RE_CELL.findall(match.group()):
				key, val = cell.split('=', 1)
				if val in COLS_TO_KEEP: # skip necessary columns
					cells[key] = val

			pos = match.span()[1]
			continue

		# atoms
		match = RE_ATOM.match(data)
		if match:
			for cell in RE_CELL.findall(match.group()):
				key, val = cell.split('=', 1)
				atoms[key] = val

			pos = match.span()[1]
			continue

		# tables
		match = RE_TABLE.match(data)
		if match:
			tableid = ':'.join(match.group()[1:2])
			table = tables.get(tableid)
			if not table:
				table = tables[tableid] = _Table(match.group(1))

			for row in RE_ROW.findall(match.group()):
				tran, rowid = row[:2]
				if tran != '-':
					rowdata = row[2:]
					for rowcell in rowdata:
						for cell in RE_CELL.findall(rowcell):
							match = RE_CELL_TEXT.match(cell)
							if match:
								col = cells.get(match.group(1))
								atom = atoms.get(match.group(2))
								if col and atom:
									table.add_cell(rowid, col, atom)
								continue

			pos = match.span()[1]
			continue

		# rows
		match = RE_ROW.match(data)
		if match:
			row = match.group()
			tran, rowid = row[:2]
			if tran != '-':
				rowdata = row[2:]
				table = tables.get('1:80')
				for rowcell in rowdata:
					for cell in RE_CELL.findall(rowcell):
						match = RE_CELL_TEXT.match(cell)
						if match:
							col = cells.get(match.group(1))
							atom = atoms.get(match.group(2))
							if col and atom:
								table.add_cell(rowid, col, atom)
							continue
			pos = match.span()[1]
			continue

		pos = 1
	return tables


def _mork2contacts(tables):
	''' Get contacts from mork table prepared by _read_mork '''
	if not tables:
		return 

	for table in tables.itervalues():
		for row in table.rows.itervalues():
			display_name = row.get('DisplayName')
			if not display_name:
				first_name = row.get('FirstName', '')
				last_name = row.get('LastName', '')
				display_name = ' '.join((first_name, last_name))

			display_name = display_name.strip()
			if not display_name:
				continue

			for key in ('PrimaryEmail', 'SecondEmail'):
				email = row.get(key)
				if email:
					yield (display_name, email)


def get_addressbook_dir_file():
	''' Get path to addressbook file from default profile. '''
	profile_file = os.path.expanduser('~/.thunderbird/profiles.ini')
	if not os.path.isfile(profile_file):
		return None, None

	config = RawConfigParser()
	config.read(profile_file)
	path = None
	for section in config.sections():
		if config.has_option(section, "Default") and \
				config.get(section, "Default") == "1":
			path = config.get(section, "Path")
			break
		elif config.has_option(section, "Path"):
			path = config.get(section, "Path")

	if path:
		path = os.path.join(os.path.expanduser('~/.thunderbird'), path)

	return path, 'abook.mab'


def get_addressbook_file():
	''' Get full path to the Thunderbird address book file.
		Return None if it don't exists '''
	path, filename = get_addressbook_dir_file()
	if not path:
		return None

	fullpath = os.path.join(path, filename)
	if os.path.isfile(fullpath):
		return fullpath

	return None


def get_contacts():
	''' Get all contacts from Thunderbird address book as
		[(contact name, contact email)] '''
	abook = get_addressbook_file()
	if abook:
		try:
			tables = _read_mork(abook)
		except IOError, err:
			pretty.print_error(__name__, 'get_contacts error', err)
		else:
			return list(_mork2contacts(tables))
	
	return []


if __name__ == '__main__':
	print '\n'.join(map(str, sorted(get_contacts())))
