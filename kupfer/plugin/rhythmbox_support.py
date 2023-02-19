import typing as ty
from collections import defaultdict

Song = dict[str, ty.Any]


def _sort_album(album: list[Song]) -> None:
    """Sort album in track order"""

    def get_track_number(rec):
        try:
            tnr = int(rec["track-number"])
        except (KeyError, ValueError):
            tnr = 0
        return tnr

    album.sort(key=get_track_number)


def _sort_album_order(songs: list[Song]) -> None:
    """Sort songs in order by album then by track number

    >>> songs = [
    ... {"title": "a", "album": "B", "track-number": 2},
    ... {"title": "b", "album": "A", "track-number": 1},
    ... {"title": "c", "album": "B", "track-number": 1},
    ... ]
    >>> _sort_album_order(songs)
    >>> [s["title"] for s in songs]
    ['b', 'c', 'a']
    """

    def get_album_order(rec):
        return (rec["date"], rec["album"], rec["track-number"])

    songs.sort(key=get_album_order)


def parse_rhythmbox_albums(songs: ty.Iterable[Song]) -> dict[str, list[Song]]:
    albums: dict[str, list[Song]] = defaultdict(list)
    for song in songs:
        if not song["artist"]:
            continue

        if song_album := song["album"]:
            albums[song_album].append(song)

    # sort album in track order
    for album in albums.values():
        _sort_album(album)

    return albums


def parse_rhythmbox_artists(songs: ty.Iterable[Song]) -> dict[str, list[Song]]:
    artists: dict[str, list[Song]] = defaultdict(list)
    for song in songs:
        if song_artist := song["artist"]:
            artists[song_artist].append(song)

    # sort in album + track order
    for artist in artists.values():
        _sort_album_order(artist)

    return artists


if __name__ == "__main__":
    import doctest

    doctest.testmod()
