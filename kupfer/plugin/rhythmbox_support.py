
def sort_album(album):
    """Sort album in track order"""
    def get_track_number(rec):
        try:
            tnr = int(rec["track-number"])
        except (KeyError, ValueError):
            tnr = 0
        return tnr
    album.sort(key=get_track_number)

def sort_album_order(songs):
    """Sort songs in order by album then by track number

    >>> songs = [
    ... {"title": "a", "album": "B", "track-number": 2},
    ... {"title": "b", "album": "A", "track-number": 1},
    ... {"title": "c", "album": "B", "track-number": 1},
    ... ]
    >>> sort_album_order(songs)
    >>> [s["title"] for s in songs]
    ['b', 'c', 'a']
    """
    def get_album_order(rec):
        return (rec['date'], rec["album"], rec['track-number'])
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
