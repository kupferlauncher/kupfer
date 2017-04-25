__kupfer_name__ = _("Spotify")
__kupfer_sources__ = ("SpotifySource", )
__description__ = _("Control spofity media player.")
__version__ = "0.2"
__author__ = "Stephen Johnson <steve@thatbytes.co.uk>; Emanuel Regnath <emanuel.regnath@tum.de>"

import dbus

from kupfer.objects import RunnableLeaf, Source
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import utils, icons, pretty


class PlayPause (RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_('Play/Pause Spotify'))
    def run(self):
        session = dbus.SessionBus.get_session()
        spotify = session.get_object("org.mpris.MediaPlayer2.spotify","/org/mpris/MediaPlayer2")
        player = dbus.Interface(spotify, "org.mpris.MediaPlayer2.Player")
        player.PlayPause() 
    def get_description(self):
        return _("Resume/Pause playback in Spotify")
    def get_icon_name(self):
        return "media-playback-start"

class Next (RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_('Next in Spotify'))
    def run(self):
        session = dbus.SessionBus.get_session()
        spotify = session.get_object("org.mpris.MediaPlayer2.spotify","/org/mpris/MediaPlayer2")
        player = dbus.Interface(spotify, "org.mpris.MediaPlayer2.Player")
        player.Next()
        
    def get_description(self):
        return _("Jump to next track in Spotify")
    def get_icon_name(self):
        return "media-skip-forward"

class Previous (RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_('Previous in Spotify'))
    def run(self):
        session = dbus.SessionBus.get_session() 
        spotify = session.get_object("org.mpris.MediaPlayer2.spotify","/org/mpris/MediaPlayer2")
        player = dbus.Interface(spotify, "org.mpris.MediaPlayer2.Player")
        player.Previous()
        player.Previous()  # most likely we are in the middle of a track and need two 
    def get_description(self):
        return _("Jump to previous track in Spotify")
    def get_icon_name(self):
        return "media-skip-backward"

class SpotifySource (AppLeafContentMixin, Source):
    appleaf_content_id = 'spotify'
    def __init__(self):
        Source.__init__(self, _("Spotify"))
    def get_items(self):
        yield PlayPause()
        yield Next()
        yield Previous()
    def provides(self):
        yield RunnableLeaf
    def get_description(self):
        return __description__
    def get_icon_name(self):
        return "spotify"