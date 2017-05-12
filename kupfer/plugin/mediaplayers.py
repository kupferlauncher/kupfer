__kupfer_name__ = _("Media Player Control")
__kupfer_sources__ = ("Players", )
__description__ = _("Playback control for media players")
__version__ = "2017.1"
__author__ = "US"

import dbus

from kupfer.objects import Source, RunnableLeaf, OperationError
from kupfer import plugin_support
from kupfer.weaklib import dbus_signal_connect_weakly

plugin_support.check_dbus_connection()

MPRIS_PREFIX = 'org.mpris.MediaPlayer2.'
MPRIS_PLAYER = 'org.mpris.MediaPlayer2.Player'
MPRIS_OBJ = '/org/mpris/MediaPlayer2'

class Players(Source):
    source_use_cache = False
    def __init__(self):
        super().__init__(_("Media Player Control"))

    def initialize(self):
        bus = dbus.SessionBus()
        dbus_signal_connect_weakly(bus, "NameOwnerChanged", self._name_owner_changed,
                                   dbus_interface="org.freedesktop.DBus")

    def finalize(self):
        pass

    def _name_owner_changed(self, name, old, new):
        if name.startswith(MPRIS_PREFIX):
            self.mark_for_update()

    def get_items(self):
        bus_names = []
        for bus_name in dbus.SessionBus().list_names():
            if bus_name.startswith(MPRIS_PREFIX):
                name = bus_name[len(MPRIS_PREFIX):]
                yield PlayPause(bus_name, name)
                yield Next(bus_name, name)
                yield Previous(bus_name, name)
                yield Stop(bus_name, name)
                bus_names.append(bus_name)
        if bus_names:
            yield PauseAll(bus_names)

    def provides(self):
        yield RunnableLeaf
    def description(self):
        return __description__
    def get_icon_name(self):
        return "applications-multimedia"


def mpris_connection(bus_name, activate=False, operation_error=True):
    try:
        obj = dbus.SessionBus().get_object(bus_name, MPRIS_OBJ)
        if obj:
            return dbus.Interface(obj, MPRIS_PLAYER)
    except dbus.exceptions.DBusException as err:
        raise OperationError(str(err))

class MprisAction(RunnableLeaf):
    def __init__(self, bus_name, name):
        super().__init__(str(bus_name), name=name)

    @property
    def bus_name(self):
        return self.object

    def repr_key(self):
        return self.bus_name

class PlayPause(MprisAction):
    def __init__(self, bus_name, name):
        # TRANS: %s is a media player name
        super().__init__(bus_name, name=_("Play/Pause (%s)") % name)

    def run(self):
        mpris_connection(self.bus_name).PlayPause()

    def get_description(self):
        return _("Resume playback")
    def get_icon_name(self):
        return "media-playback-start"

def _reply_nop(*args):
    pass

class PauseAll(RunnableLeaf):
    def __init__(self, bus_names):
        super().__init__(name=_("Pause All"))
        self.bus_names = bus_names

    def run(self):
        for name in self.bus_names:
            mpris_connection(name).Pause(
                reply_handler=_reply_nop,
                error_handler=_reply_nop)

    def get_icon_name(self):
        return "media-playback-pause"

class Next (MprisAction):
    def __init__(self, bus_name, name):
        # TRANS: %s is a media player name
        super().__init__(bus_name, name=_("Next (%s)") % name)

    def run(self):
        mpris_connection(self.bus_name).Next()

    def get_description(self):
        return _("Skip to next track")

    def get_icon_name(self):
        return "media-skip-forward"

class Previous (MprisAction):
    def __init__(self, bus_name, name):
        # TRANS: %s is a media player name
        super().__init__(bus_name, name=_("Previous (%s)") % name)

    def run(self):
        mpris_connection(self.bus_name).Previous()

    def get_description(self):
        return _("Skip to previous track")

    def get_icon_name(self):
        return "media-skip-backward"

class Stop(MprisAction):
    def __init__(self, bus_name, name):
        # TRANS: %s is a media player name
        super().__init__(bus_name, name=_("Stop (%s)") % name)

    def run(self):
        mpris_connection(self.bus_name).Stop()

    def get_description(self):
        return _("Stop playback")

    def get_icon_name(self):
        return "media-playback-stop"
