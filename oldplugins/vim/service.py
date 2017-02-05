
import os
import sys
import traceback

import pygtk
pygtk.require('2.0')

import glib
import gobject

from kupfer.plugin.vim import vimcom

try:
    import dbus
    import dbus.service
    #import dbus.glib
    from dbus.mainloop.glib import DBusGMainLoop

except (ImportError, dbus.exceptions.DBusException) as exc:
    print(exc)
    raise SystemExit(1)

PLUGID='vim'

server_name = "se.kaizer.kupfer.plugin.%s" % PLUGID
interface_name = "se.kaizer.kupfer.plugin.%s" % PLUGID
object_name = "/se/kaizer/kupfer/plugin/%s" % PLUGID

class Service (dbus.service.Object):
    def __init__(self, mainloop, bus):
        bus_name = dbus.service.BusName(server_name, bus=bus,
                allow_replacement=True, replace_existing=True)
        super(Service, self).__init__(conn=bus, object_path=object_name,
                bus_name=bus_name)
        self.mainloop = mainloop
        self.initialize()

    def unregister(self):
        self.connection.release_name(server_name)

    def initialize(self):
        self.vimcom = vimcom.VimCom(self)
        self.vimcom.vim_hidden = vimcom.poller(name_token="KUPFER")
        self.vimcom.stop_fetching_serverlist()
        self.serverids = []
        glib.timeout_add_seconds(1, self.update_serverlist)

    def finalize(self):
        pid = self.vimcom.vim_hidden.pid
        if pid:
            self.vimcom.send_ex(self.vimcom.vim_hidden.name, 'qa!')
            os.close(self.vimcom.vim_hidden.childfd)
            #os.kill(pid, 15)
            os.waitpid(pid, 0)
        self.vimcom.destroy()
        self.vimcom = None

    def mark_for_update(self):
        self.NewServerlist(self.serverids)

    def vim_new_serverlist(self, serverlist):
        """this is the inaccurate serverlist"""
        ## useless callback from vimcom.VimCom
        pass

    def on_new_serverlist(self, new_list):
        if set(new_list) != set(self.serverids):
            self.serverids = new_list
            self.mark_for_update()

    def update_serverlist(self):
        if self.vimcom:
            self.vimcom.get_hidden_serverlist(self.on_new_serverlist)
            return True

    @dbus.service.method(interface_name, in_signature="ay", out_signature="b",
                         byte_arrays=True)
    def Foreground(self, server):
        if self.vimcom and server in self.serverids:
            self.vimcom.foreground(server)
            return True
        return False

    @dbus.service.method(interface_name, in_signature="ayay", out_signature="b",
                         byte_arrays=True)
    def SendEx(self, server, excommand):
        if self.vimcom and server in self.serverids:
            self.vimcom.send_ex(server, excommand)
            return True
        return False

    @dbus.service.signal(interface_name, signature="aay")
    def NewServerlist(self, serverlist):
        pass

    @dbus.service.method(interface_name)
    def Exit(self):
        self.unregister()
        self.finalize()
        self.mainloop.quit()

def start(ml):
    try:
        bus = dbus.Bus()
        service = Service(ml, bus)
    except:
        traceback.print_exc()
        raise SystemExit(1)

def main():
    ml_wrap = DBusGMainLoop(set_as_default=True)
    glib.set_prgname(__name__)
    ml = glib.MainLoop()
    glib.idle_add(start, ml)
    ml.run()

if __name__ == '__main__':
    main()
