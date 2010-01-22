
import os
import xml.etree.cElementTree as ElementTree

NEEDED_KEYS= set(("title", "artist", "album", "track-number", "location", ))
UNICODE_KEYS = set(("title", "artist", "album"))

def _tounicode(bstr):
	# the XML parser returns `str' only when it's ascii, but we want
	# unicode objects all the time
	if isinstance(bstr, unicode):
		return bstr
	return bstr.decode("ascii")

def _lookup_string(string, strmap):
	"""Look up @string in the string map,
	and return the copy in the map.

	If not found, update the map with the string.
	"""
	string = string or ""
	try:
		return strmap[string]
	except KeyError:
		strmap[string] = string
		return string

def get_rhythmbox_songs(dbfile, typ="song", keys=NEEDED_KEYS):
	"""Return a list of info dictionaries for all songs
	in a Rhythmbox library database file, with dictionary
	keys as given in @keys.
	"""
	rhythmbox_dbfile = os.path.expanduser(dbfile)

	lSongs = []
	strmap = {}

	# Parse with iterparse; we get the elements when
	# they are finished, and can remove them directly after use.

	for event, entry in ElementTree.iterparse(rhythmbox_dbfile):
		if not (entry.tag == ("entry") and entry.get("type") == typ):
			continue
		info = {}
		for child in entry.getchildren():
			if child.tag in keys:
				if child.tag in UNICODE_KEYS:
					childtext = _tounicode(child.text)
				else:
					childtext = child.text
				tag = _lookup_string(child.tag, strmap)
				text = _lookup_string(childtext, strmap)
				info[tag] = text
		lSongs.append(info)
		entry.clear()
	return lSongs

def sort_album(album):
	"""Sort album in track order"""
	def get_track_number(rec):
		tnr = rec.get("track-number")
		if not tnr: return None
		try:
			tnr = int(tnr)
		except ValueError:
			pass
		return tnr
	album.sort(key=get_track_number)

def sort_album_order(songs):
	"""Sort songs in order by album then by track number

	>>> songs = [
	... {"title": "a", "album": "B", "track-number": "2"},
	... {"title": "b", "album": "A", "track-number": "1"},
	... {"title": "c", "album": "B", "track-number": "1"},
	... ]
	>>> sort_album_order(songs)
	>>> [s["title"] for s in songs]
	['b', 'c', 'a']
	"""
	def get_album_order(rec):
		tnr = rec.get("track-number")
		if not tnr: return None
		try:
			tnr = int(tnr)
		except ValueError:
			pass
		return (rec["album"], tnr)
	songs.sort(key=get_album_order)

def parse_rhythmbox_albums(songs):
	albums = {}
	for song in songs:
		song_artist = song["artist"]
		if not song_artist:
			continue
		song_album = song["album"]
		if not song_album:
			continue
		album = albums.get(song_album, [])
		album.append(song)
		albums[song_album] = album
	# sort album in track order
	for album in albums:
		sort_album(albums[album])
	return albums

def parse_rhythmbox_artists(songs):
	artists = {}
	for song in songs:
		song_artist = song["artist"]
		if not song_artist:
			continue
		artist = artists.get(song_artist, [])
		artist.append(song)
		artists[song_artist] = artist
	# sort in album + track order
	for artist in artists:
		sort_album_order(artists[artist])
	return artists

if __name__ == '__main__':
	import doctest
	doctest.testmod()
