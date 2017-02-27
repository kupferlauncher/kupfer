from time import time
import os
import pickle as pickle

from gi.repository import GLib, Gio

from kupfer import pretty, config
from kupfer import scheduler
from kupfer import desktop_launch
from kupfer.ui import uievents
from kupfer import terminal

from kupfer.desktop_launch import SpawnError

## NOTE: SpawnError  *should* be imported from this module

try:
    import gi
    gi.require_version("Wnck", "3.0")
    from gi.repository import Wnck
    Wnck.set_client_type(Wnck.ClientType.PAGER)
except ValueError as e:
    pretty.print_info(__name__, "Disabling window tracking:", e)
    Wnck = None


default_associations = {
    "evince" : "Document Viewer",
    "file-roller" : "File Roller",
    #"gedit" : "Text Editor",
    "gnome-keyring-manager" : "Keyring Manager",
    "nautilus-browser" : "File Manager",
    "rhythmbox" : "Rhythmbox Music Player",
}


def application_id(app_info, desktop_file=None):
    """Return an application id (string) for GAppInfo @app_info"""
    app_id = app_info.get_id()
    if not app_id:
        app_id = desktop_file or ""
    if app_id.endswith(".desktop"):
        app_id = app_id[:-len(".desktop")]
    return app_id

def launch_application(app_info, files=(), uris=(), paths=(), track=True,
                       activate=True, desktop_file=None, screen=None):
    """
    Launch @app_rec correctly, using a startup notification

    you may pass in either a list of Gio.Files in @files, or 
    a list of @uris or @paths

    if @track, it is a user-level application
    if @activate, activate rather than start a new version

    @app_rec is either an GAppInfo or (GAppInfo, desktop_file_path) tuple

    Raises SpawnError on failed program start.
    """
    assert app_info

    if paths:
        files = [Gio.File.new_for_path(p) for p in paths]
    if uris:
        files = [Gio.File.new_for_uri(p) for p in uris]

    svc = GetApplicationsMatcherService()
    app_id = application_id(app_info, desktop_file)

    if activate and svc.application_is_running(app_id):
        svc.application_to_front(app_id)
        return True

    # An launch callback closure for the @app_id
    def application_launch_callback(argv, pid, notify_id, files, timestamp):
        is_terminal = terminal.is_known_terminal_executable(argv[0])
        if not is_terminal:
            svc.launched_application(app_id, pid)

    if track:
        launch_callback = application_launch_callback
    else:
        launch_callback = None

    try:
        desktop_launch.launch_app_info(app_info, files,
               timestamp=uievents.current_event_time(),
               desktop_file=desktop_file,
               launch_cb=launch_callback,
               screen=screen)
    except SpawnError:
        raise
    return True

def application_is_running(app_id):
    svc = GetApplicationsMatcherService()
    return svc.application_is_running(app_id)

def application_close_all(app_id):
    svc = GetApplicationsMatcherService()
    return svc.application_close_all(app_id)

class ApplicationsMatcherService (pretty.OutputMixin):
    """Handle launching applications and see if they still run.
    This is a learning service, since we have no first-class application
    object on the Linux desktop
    """
    def __init__(self):
        self.register = {}
        self._get_wnck_screen_windows_stacked()
        scheduler.GetScheduler().connect("finish", self._finish)
        self._load()

    @classmethod
    def _get_wnck_screen_windows_stacked(cls):
        if not Wnck:
            return ()
        screen = Wnck.Screen.get_default()
        if screen is None:
            return ()
        return screen.get_windows_stacked()

    def _get_filename(self):
        # Version 1: Up to incl v203
        # Version 2: Do not track terminals
        version = 2
        return os.path.join(config.get_cache_home(),
                "application_identification_v%d.pickle" % version)
    def _load(self):
        reg = self._unpickle_register(self._get_filename())
        self.register = reg if reg else default_associations
        # pretty-print register to debug
        if self.register:
            self.output_debug("Learned the following applications")
            self.output_debug("\n{\n%s\n}" % "\n".join(
                ("  %-30s : %s" % (k,v)
                    for k,v in self.register.items())
                ))
    def _finish(self, sched):
        self._pickle_register(self.register, self._get_filename())
    def _unpickle_register(self, pickle_file):
        try:
            pfile = open(pickle_file, "rb")
        except IOError as e:
            return None
        try:
            source = pickle.loads(pfile.read())
            assert isinstance(source, dict), "Stored object not a dict"
            self.output_debug("Reading from %s" % (pickle_file, ))
        except (pickle.PickleError, Exception) as e:
            source = None
            self.output_info("Error loading %s: %s" % (pickle_file, e))
        finally:
            pfile.close()
        return source

    def _pickle_register(self, reg, pickle_file):
        output = open(pickle_file, "wb")
        self.output_debug("Saving to %s" % (pickle_file, ))
        output.write(pickle.dumps(reg, pickle.HIGHEST_PROTOCOL))
        output.close()
        return True

    def _store(self, app_id, window):
        # FIXME: Store the 'res_class' name?
        application = window.get_application()
        store_name = application.get_name()
        self.register[app_id] = store_name
        self.output_debug("storing application", app_id, "as", store_name)

    def _has_match(self, app_id):
        return app_id in self.register

    def _is_match(self, app_id, window):
        application = window.get_application()
        res_class = window.get_class_group().get_res_class()
        reg_name = self.register.get(app_id)
        if reg_name and reg_name in (application.get_name(), res_class):
            return True
        if app_id in (application.get_name().lower(), res_class.lower()):
            return True
        return False

    def launched_application(self, app_id, pid):
        if self._has_match(app_id):
            return
        timeout = time() + 15
        GLib.timeout_add_seconds(2, self._find_application, app_id, pid, timeout)
        # and once later
        GLib.timeout_add_seconds(30, self._find_application, app_id, pid, timeout)

    def _find_application(self, app_id, pid, timeout):
        if self._has_match(app_id):
            return False
        #self.output_debug("Looking for window for application", app_id)
        for w in self._get_wnck_screen_windows_stacked():
            app = w.get_application()
            app_pid = app.get_pid()
            if not app_pid:
                app_pid = w.get_pid()
            if app_pid == pid:
                self._store(app_id, w)
                return False
        if time() > timeout:
            return False
        return True

    def application_name(self, app_id):
        if not self._has_match(app_id):
            return None
        return self.register[app_id]

    def application_is_running(self, app_id):
        for w in self._get_wnck_screen_windows_stacked():
            if (w.get_application() and self._is_match(app_id, w) and 
                w.get_window_type() == Wnck.WindowType.NORMAL):
                return True
        return False

    def get_application_windows(self, app_id):
        application_windows = []
        for w in self._get_wnck_screen_windows_stacked():
            if (w.get_application() and self._is_match(app_id, w) and 
                w.get_window_type() == Wnck.WindowType.NORMAL):
                application_windows.append(w)
        return application_windows

    def application_to_front(self, app_id):
        application_windows = self.get_application_windows(app_id)
        if not application_windows:
            return False
        etime = uievents.current_event_time()
        # if True, focus app's all windows on the same workspace
        # if False, focus only one window (in cyclical manner)
        focus_all = True
        if focus_all:
            return self._to_front_application_style(application_windows, etime)
        else:
            return self._to_front_single(application_windows, etime)

    def _to_front_application_style(self, application_windows, evttime):
        workspaces = {}
        cur_screen = application_windows[0].get_screen()
        cur_workspace = cur_screen.get_active_workspace()

        def visible_window(window):
            return (window.get_window_type() == Wnck.WindowType.NORMAL and
                    window.is_visible_on_workspace(cur_workspace))

        def normal_window(window):
            return window.get_window_type() == Wnck.WindowType.NORMAL

        ## get all visible windows in stacking order
        vis_windows = list(filter(visible_window,
                             self._get_wnck_screen_windows_stacked()))

        ## sort windows into "bins" by workspace
        for w in filter(normal_window, application_windows):
            wspc = w.get_workspace() or cur_workspace
            workspaces.setdefault(wspc, []).append(w)

        cur_wspc_windows = workspaces.get(cur_workspace, [])
        # make a rotated workspace list, with current workspace first
        idx = cur_workspace.get_number()
        all_workspaces = cur_screen.get_workspaces()
        all_workspaces[:] = all_workspaces[idx:] + all_workspaces[:idx]
        # check if the application's window on current workspace
        # are the topmost
        focus_windows = []
        if (cur_wspc_windows and 
            set(vis_windows[-len(cur_wspc_windows):]) != set(cur_wspc_windows)):
            focus_windows = cur_wspc_windows
            ## if the topmost window is already active, take another
            if focus_windows[-1:] == vis_windows[-1:]:
                focus_windows[:] = focus_windows[:-1]
        else:
            # all windows are focused, find on next workspace
            for wspc in all_workspaces[1:]:
                focus_windows = workspaces.get(wspc, [])
                if focus_windows:
                    break
            else:
                # no windows on other workspaces, so we rotate among
                # the local ones
                focus_windows = cur_wspc_windows[:1]
        self._focus_windows(focus_windows, evttime)

    def _to_front_single(self, application_windows, evttime):
        # bring the first window to front
        for window in application_windows:
            self._focus_windows([window], evttime)
            return

    def _focus_windows(self, windows, evttime):
        for window in windows:
            # we special-case the desktop
            # only show desktop if it's the only window
            if window.get_name() == "x-nautilus-desktop":
                if len(windows) == 1:
                    screen = Wnck.Screen.get_default()
                    if screen is not None:
                        screen.toggle_showing_desktop(True)
                else:
                    continue
            wspc = window.get_workspace()
            if wspc:
                wspc.activate(evttime)
            window.activate_transient(evttime)

    def application_close_all(self, app_id):
        application_windows = self.get_application_windows(app_id)
        evttime = uievents.current_event_time()
        for w in application_windows:
            if not w.is_skip_tasklist():
                w.close(evttime)


_appl_match_service = None
def GetApplicationsMatcherService():
    """Get the (singleton) ApplicationsMatcherService"""
    global _appl_match_service
    if not _appl_match_service:
        _appl_match_service = ApplicationsMatcherService()
    return _appl_match_service

