# -*- coding: UTF-8 -*-

def split_at(s, seps):
	"""
	Split at string at any char in seps
	"""
	parts = []
	last = 0
	for i, c in enumerate(s):
		if c in seps:
			parts.append(s[last:i])
			last = i+1
	if last == 0:
		parts.append(s)
	else:
		parts.append(s[last:])
	return parts

def upper_str(s):
	return "".join([c for c in s if c.isupper()])

def remove_chars(s, clist):
	"""
	remove any char in string clist from s and return the result
	"""
	return "".join([c for c in s if c not in clist])

class Search (object):
	"""
	Loads a list of strings and performs a smart search,
	returning a ranked list
	"""
	
	def __init__(self, search_base, wordsep=" .-_"):
		self.wordsep = wordsep
		self.search_base = search_base

	def rank_string(self, s, key):
		# match values
		exact_v = 20
		start_v = 10
		wordm_v = 8
		substr_v = 5

		s = s.lower()
		key = key.lower()
		rank = 0
		if s == key:
			rank += exact_v
		elif s.startswith(key):
			rank += start_v
		elif key in s:
			rank += substr_v
		else:
			rank += self.common_prefix(s, key)

		words = split_at(s, self.wordsep)
		if key in words:
			# exact subword match
			rank += wordm_v
		else:
			# score prefixes of subwords
			# example:
			# key: contdesk
			# matches configure-the-thing.desktop as 3-1-0-4 for a score of 7
			# key: conddesk matches only 3-0-0-1
			idx = 0
			word_pfx = 0
			for w in words:
				pfx = self.common_prefix(w, key[idx:])
				idx += pfx
				word_pfx += pfx
			if word_pfx > 5: print s, "hat", word_pfx, "for", key
			rank += word_pfx

		return rank

	def common_letters(self, s, key, case_insensitive=True):
		"""
		count number of common letters
		(in order)
		"""
		if case_insensitive:
			s = s.lower()
			key = key.lower()
		idx = 0
		for c in s:
			if c == key[idx]:
				idx += 1
				if idx == len(key):
					break
		return idx

	def common_prefix(self, s, key):
		"""
		count nbr of common letters in common prefix
		"""
		common =0
		for c1, c2 in zip(s, key):
			if c1 == c2:
				common += 1
			else:
				break
		return common

	def abbrev_str(self, s):
		words = split_at(s, self.wordsep)
		first_chars = "".join([w[0] for w in words if len(w)])
		return first_chars

	def rank_objects(self, objects, key):
		"""
		objects --
		key -- 
		"""
		normal_w = 10
		abbrev_w = 7 
		common_letter_w = 3
		part_w = 1
		rank_list = []

		def rank_key(obj, key):
			rank = 0
			rank += normal_w * self.rank_string(i, key)
			abbrev = self.abbrev_str(i)
			rank += abbrev_w * self.rank_string(abbrev, key)
			rank += common_letter_w * self.common_letters(i, key)
			rank += common_letter_w * self.common_letters(abbrev, key)

			return rank

		for i in objects:
			rank = 0
			rank += normal_w * rank_key(i, key)
			# do parts
			keyparts = key.split()
			for part in keyparts:
				rank += part_w * rank_key(i, part)
			
			rank_list.append((rank,i))
		rank_list.sort(key= lambda item: item[0], reverse=True)
		return rank_list

	def search_objects(self, key):
		"""
		key -- string key
		"""
		ranked_str = self.rank_objects(self.search_base, key)
		return ranked_str
	
