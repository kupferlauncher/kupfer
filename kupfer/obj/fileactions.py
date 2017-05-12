import os

from gi.repository import Gio 

from kupfer import utils
from kupfer import launch

from kupfer.obj.base import Action, OperationError

class NoDefaultApplicationError (OperationError):
    pass

def is_good_executable(fileleaf):
    if not fileleaf._is_executable():
        return False
    ctype, uncertain = Gio.content_type_guess(fileleaf.object, None)
    return uncertain or Gio.content_type_can_be_executable(ctype)

def get_actions_for_file(fileleaf):
    acts = [GetParent(), ]
    if fileleaf.is_dir():
        acts.append(OpenTerminal())
    elif fileleaf.is_valid():
        if is_good_executable(fileleaf):
            acts.extend((Execute(), Execute(in_terminal=True)))
    return [Open()] + acts

class Open (Action):
    """ Open with default application """
    action_accelerator = "o"
    rank_adjust = 5
    def __init__(self, name=_("Open")):
        Action.__init__(self, name)

    @classmethod
    def default_application_for_leaf(cls, leaf):
        content_attr = Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE
        gfile = leaf.get_gfile()
        info = gfile.query_info(content_attr, Gio.FileQueryInfoFlags.NONE, None)
        content_type = info.get_attribute_string(content_attr)
        def_app = Gio.app_info_get_default_for_type(content_type, False)
        if not def_app:
            raise NoDefaultApplicationError(
                    (_("No default application for %(file)s (%(type)s)") % 
                     {"file": str(leaf), "type": content_type}) + "\n" +
                    _('Please use "%s"') % _("Set Default Application...")
                )
        return def_app

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        self.activate_multiple((leaf, ), ctx)

    def activate_multiple(self, objects, ctx):
        appmap = {}
        leafmap = {}
        for obj in objects:
            app = self.default_application_for_leaf(obj)
            id_ = app.get_id()
            appmap[id_] = app
            leafmap.setdefault(id_, []).append(obj)

        for id_, leaves in leafmap.items():
            app = appmap[id_]
            launch.launch_application(app, paths=[L.object for L in leaves],
                                      activate=False,
                                      screen=ctx and ctx.environment.get_screen())

    def get_description(self):
        return _("Open with default application")

class GetParent (Action):
    action_accelerator = "p"
    rank_adjust = -5
    def __init__(self, name=_("Get Parent Folder")):
        super().__init__(name)
    
    def has_result(self):
        return True

    def activate(self, leaf):
        # Avoid cyclical dep on module level
        from kupfer.objects import FileLeaf
        fileloc = leaf.object
        parent = os.path.normpath(os.path.join(fileloc, os.path.pardir))
        return FileLeaf(parent)

    def get_description(self):
        return None

    def get_icon_name(self):
        return "folder-open"

class OpenTerminal (Action):
    action_accelerator = "t"
    def __init__(self, name=_("Open Terminal Here")):
        super(OpenTerminal, self).__init__(name)

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        try:
            utils.spawn_terminal(leaf.object, ctx.environment.get_screen())
        except utils.SpawnError as exc:
            raise OperationError(exc)

    def get_description(self):
        return _("Open this location in a terminal")
    def get_icon_name(self):
        return "utilities-terminal"

class Execute (Action):
    """ Execute executable file (FileLeaf) """
    rank_adjust = 10
    def __init__(self, in_terminal=False, quoted=True):
        name = _("Run in Terminal") if in_terminal else _("Run (Execute)")
        super(Execute, self).__init__(name)
        self.in_terminal = in_terminal
        self.quoted = quoted

    def repr_key(self):
        return (self.in_terminal, self.quoted)
    
    def activate(self, leaf):
        if self.quoted:
            argv = [leaf.object]
        else:
            argv = utils.argv_for_commandline(leaf.object)
        if self.in_terminal:
            utils.spawn_in_terminal(argv)
        else:
            utils.spawn_async(argv)

    def get_description(self):
        if self.in_terminal:
            return _("Run this program in a Terminal")
        else:
            return _("Run this program")

