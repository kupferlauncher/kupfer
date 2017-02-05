import os
import sys

import dbus
import gio
import glib

from kupfer.objects import Source, FileLeaf, Leaf, Action
from kupfer.objects import OperationError
from kupfer.objects import AppLeaf, TextLeaf, TextSource
from kupfer.obj.objects import Launch
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import datatools
from kupfer import utils
from kupfer import kupferstring
from kupfer import pretty
from kupfer import plugin_support
from kupfer import utils

plugin_support.check_dbus_connection()

PLUGID='vim'

VIM = 'gvim'

def get_vim_files(filepath):
    """
    Read ~/.viminfo from @filepath

    Look for a line like this:
    *encoding=<encoding>

    Return an iterator of unicode string file paths
    """
    encoding = "UTF-8"
    recents = []
    with open(filepath, "r") as f:
        for line in f:
            if line.startswith("*encoding="):
                _, enc = line.split("=")
                encoding = enc.strip()
            us_line = line.decode(encoding, "replace")
            ## Now find the jumplist
            if us_line.startswith("-'  "):
                parts = us_line.split(None, 3)
                recentfile = os.path.expanduser(parts[-1].strip())
                if recentfile:
                    recents.append(recentfile)
    return datatools.UniqueIterator(recents)

class RecentsSource (AppLeafContentMixin, Source):
    appleaf_content_id = ("vim", "gvim")

    vim_viminfo_file = "~/.viminfo"
    def __init__(self, name=None):
        name = name or _("Vim Recent Documents")
        super(RecentsSource, self).__init__(name)

    def initialize(self):
        """Set up change monitor"""
        viminfofile = os.path.expanduser(self.vim_viminfo_file)
        gfile = gio.File(viminfofile)
        self.monitor = gfile.monitor_file(gio.FILE_MONITOR_NONE, None)
        if self.monitor:
            self.monitor.connect("changed", self._changed)

    def finalize(self):
        if self.monitor:
            self.monitor.cancel()
        self.monitor = None

    def _changed(self, monitor, file1, file2, evt_type):
        """Change callback; something changed"""
        if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
                gio.FILE_MONITOR_EVENT_DELETED,
                gio.FILE_MONITOR_EVENT_CHANGED):
            self.mark_for_update()

    def get_items(self):
        viminfofile = os.path.expanduser(self.vim_viminfo_file)
        if not os.path.exists(viminfofile):
            self.output_debug("Viminfo not found at", viminfofile)
            return

        try:
            filepaths = list(get_vim_files(viminfofile))
        except EnvironmentError:
            self.output_exc()
            return

        for filepath in filepaths:
            # The most confusing glib function
            # takes a unicode string and returns a
            # filesystem-encoded bytestring.
            yield FileLeaf(glib.filename_from_utf8(filepath))

    def get_icon_name(self):
        return "document-open-recent"

    def provides(self):
        yield FileLeaf

def get_plugin_iface_name(plugin_id):
    plugin_id = plugin_id.split(".")[-1]
    interface_name = "se.kaizer.kupfer.plugin.%s" % plugin_id
    return interface_name

def get_plugin_service_obj(plugin_id, activate=True):
    """Return the dbus proxy object for our plugin

    if @activate, we will --exec-helper= the service
    """
    plugin_id = plugin_id.split(".")[-1]

    service_name = "se.kaizer.kupfer.plugin.%s" % plugin_id
    interface_name = "se.kaizer.kupfer.plugin.%s" % plugin_id
    object_name = "/se/kaizer/kupfer/plugin/%s" % plugin_id
    try:
        bus = dbus.Bus()
    except dbus.DBusException:
        return None
    try:
        proxy_obj = bus.get_object(service_name, object_name)
    except dbus.DBusException as exc:
        if activate:
            service_id = "kupfer.plugin.%s.service" % plugin_id
            return utils.start_plugin_helper(service_id, True)
        return None
    proxy_iface = dbus.Interface(proxy_obj, interface_name)
    return proxy_iface

def stop_plugin_service(plugin_id):
    """
    Return True if it was running and was stopped
    """
    plug_iface = get_plugin_service_obj(plugin_id, activate=False)
    if plug_iface:
        plug_iface.Exit(reply_handler=_dummy_handler,
                        error_handler=_dummy_handler)


def _dummy_handler(*args):
    pass

class VimApp (AppLeaf):
    """
    This is a re-implemented AppLeaf that represents a running Vim session

    with a fake vim self.object for safety (this should not be needed)
    """
    serializable = None
    def __init__(self, serverid, name):
        try:
            obj = gio.unix.DesktopAppInfo("gvim.desktop")
        except RuntimeError:
            obj = gio.AppInfo(VIM)
        Leaf.__init__(self, obj, name)
        self.serverid = serverid

    def get_id(self):
        # use an ostensibly fake id starting with @/
        return "@/%s/%s" % (__name__, self.serverid or "")

    def __setstate__(self, state):
        raise NotImplementedError

    def __getstate__(self):
        raise NotImplementedError

    def get_actions(self):
        if self.serverid is not None:
            yield Launch(_("Go To"), is_running=True)
            yield SendCommand()
            yield CloseSaveAll()
        else:
            yield Launch()

    def launch(self, files=(), paths=(), activate=False, ctx=None):
        """
        Launch the represented application

        @files: a seq of GFiles (gio.File)
        @paths: a seq of bytestring paths
        @activate: activate instead of start new
        """
        if self.serverid is not None:
            argv = [VIM, '--servername', self.serverid, '--remote']
        else:
            argv = [VIM]
        if files:
            paths = [f.get_path() or f.get_uri() for f in files]
        if paths:
            argv.extend(paths)
        if paths or self.serverid is None:
            try:
                utils.spawn_async_raise(argv)
            except utils.SpawnError as exc:
                raise OperationError(exc)
        if self.serverid:
            ## focus the window we opened
            def error_handler(exc):
                ctx.register_late_error(OperationError(exc))
            proxy_obj = get_plugin_service_obj(PLUGID)
            if proxy_obj:
                proxy_obj.Foreground(self.serverid,
                        reply_handler=_dummy_handler,
                        error_handler=error_handler)

    def get_icon_name(self):
        return 'vim'

    def get_description(self):
        return None

class CloseSaveAll (Action):
    """ Close a vim window without forcing """
    rank_adjust = -5
    def __init__(self):
        Action.__init__(self, _("Close (Save All)"))

    def wants_context(self):
        return True
    def activate(self, obj, ctx):
        def error_handler(exc):
            ctx.register_late_error(OperationError(exc))
        proxy_obj = get_plugin_service_obj(PLUGID)
        if proxy_obj:
            proxy_obj.SendEx(obj.serverid, 'wqa',
                    reply_handler=_dummy_handler,
                    error_handler=error_handler)

    def get_icon_name(self):
        return "window-close"

class SendCommand (Action):
    def __init__(self):
        Action.__init__(self, _("Send..."))

    def wants_context(self):
        return True
    def activate(self, obj, iobj, ctx):
        ## accept with or without starting :
        lcmd = kupferstring.tolocale(iobj.object)
        if lcmd.startswith(":"):
            lcmd = lcmd[1:]

        def error_handler(exc):
            ctx.register_late_error(OperationError(exc))
        proxy_obj = get_plugin_service_obj(PLUGID)
        if proxy_obj:
            proxy_obj.SendEx(obj.serverid, lcmd,
                    reply_handler=_dummy_handler,
                    error_handler=error_handler)


    def requires_object(self):
        return True
    def object_types(self):
        yield TextLeaf
    def object_source(self, for_item=None):
        return TextSource()

    def get_description(self):
        return _("Send ex command")

class InsertInVim (Action):
    """
    Insert a given text into the currently open buffer in a vim
    session
    """
    def __init__(self):
        Action.__init__(self, _("Insert in Vim..."))

    def wants_context(self):
        return True
    def activate(self, obj, iobj, ctx):
        tmpf, tmpname = utils.get_safe_tempfile()
        tmpf.write(kupferstring.tolocale(obj.object))
        tmpf.close()
        vim_cmd = "r %s" % tmpname
        glib.timeout_add_seconds(10, os.unlink, tmpname)

        def error_handler(exc):
            ctx.register_late_error(OperationError(exc))

        proxy_obj = get_plugin_service_obj(PLUGID)
        if proxy_obj:
            proxy_obj.SendEx(iobj.serverid, vim_cmd,
                    reply_handler=_dummy_handler,
                    error_handler=error_handler)

    def item_types(self):
        yield TextLeaf

    def requires_object(self):
        return True

    def object_types(self):
        yield VimApp

    def get_icon_name(self):
        return "insert-text"


class ActiveVim (AppLeafContentMixin, Source):
    appleaf_content_id = ("vim", "gvim")

    def __init__(self):
        Source.__init__(self, _("Active Vim Sessions"))

    def initialize(self):
        ActiveVim.instance = self
        self.serverids = []
        self.signal_match = None
        glib.timeout_add_seconds(1, self.start_helper)

    def start_helper(self):
        bus = dbus.Bus()
        self.signal_match = bus.add_signal_receiver(self.on_new_serverlist,
                                signal_name="NewServerlist",
                                dbus_interface=get_plugin_iface_name(PLUGID),
                                byte_arrays=True)
        get_plugin_service_obj(PLUGID, activate=True)

    def finalize(self):
        ActiveVim.instance = None
        if self.signal_match is not None:
            bus = dbus.Bus()
            bus.remove_signal_receiver(self.signal_match,
                                signal_name="NewServerlist",
                                dbus_interface=get_plugin_iface_name(PLUGID))
            self.signal_match = None
        self.mark_for_update()
        stop_plugin_service(PLUGID)

    def get_items(self):
        for x in self.serverids:
            yield VimApp(x, _("Vim Session %s") % kupferstring.fromlocale(x))

    def on_new_serverlist(self, new_list):
        self.output_debug("New list:", list(new_list))
        if set(new_list) != set(self.serverids):
            self.serverids = list(map(str, new_list))
            self.mark_for_update()

    def provides(self):
        yield VimApp

    @classmethod
    def decorate_item(cls, leaf):
        if cls.instance and not cls.instance.serverids:
            return None
        return super(ActiveVim, cls).decorate_item(leaf)
