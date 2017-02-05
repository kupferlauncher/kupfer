__kupfer_name__ = _("APT")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
        "ShowPackageInfo",
        "SearchPackageName",
        "InstallPackage",
    )
__description__ = _("Interface with the package manager APT")
__version__ = ""
__author__ = ("Martin Koelewijn <martinkoelewijn@gmail.com>, "
              "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>")

import os

from kupfer.objects import Action, Source, Leaf
from kupfer.objects import TextLeaf
from kupfer import icons, kupferstring, task, uiutils, utils
from kupfer import plugin_support


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "installation_method",
        "label": _("Installation method"),
        "type": str,
        "value": "gksu -- apt-get install --yes",
    },
)

class InfoTask(task.Task):
    def __init__(self, text):
        super(InfoTask, self).__init__()
        self.text = text
        self.aptitude = None
        self.apt_cache = None

    def start(self, finish_callback):
        self._finish_callback = finish_callback
        timeout = 60
        AC = utils.AsyncCommand
        AC(["aptitude", "show", self.text], self.aptitude_finished, timeout)
        AC(["apt-cache", "policy", self.text], self.aptcache_finished, timeout)

    def aptitude_finished(self, acommand, stdout, stderr):
        self.aptitude = stderr
        self.aptitude += stdout
        self._check_end()

    def aptcache_finished(self, acommand, stdout, stderr):
        self.apt_cache = stderr
        self.apt_cache += stdout
        self._check_end()

    def _check_end(self):
        if self.aptitude is not None and self.apt_cache is not None:
            self.finish("".join(kupferstring.fromlocale(s)
                        for s in (self.aptitude, self.apt_cache)))

    def finish(self, text):
        uiutils.show_text_result(text, title=_("Show Package Information"))
        self._finish_callback(self)

class ShowPackageInfo (Action):
    def __init__(self):
        Action.__init__(self, _("Show Package Information"))

    def is_async(self):
        return True
    def activate(self, leaf):
        return InfoTask(leaf.object.strip())

    def item_types(self):
        yield TextLeaf
        yield Package

    def valid_for_item(self, item):
        # check if it is a single word
        text = item.object
        return len(text.split(None, 1)) == 1

    def get_gicon(self):
        return icons.ComposedIcon("dialog-information", "package-x-generic")

class InstallPackage (Action):
    def __init__(self):
        Action.__init__(self, _("Install"))

    def activate(self, leaf):
        self.activate_multiple((leaf, ))

    def activate_multiple(self, objs):
        program = (__kupfer_settings__["installation_method"])
        pkgs = [o.object.strip() for o in objs]
        prog_argv = utils.argv_for_commandline(program)
        utils.spawn_in_terminal(prog_argv + pkgs)

    def item_types(self):
        yield Package
        yield TextLeaf

    def get_description(self):
        return _("Install package using the configured method")
    def get_icon_name(self):
        return "document-save"

class Package (Leaf):
    def __init__(self, package, desc):
        Leaf.__init__(self, package, package)
        self.desc = desc

    def get_text_representation(self):
        return self.object
    def get_description(self):
        return self.desc
    def get_icon_name(self):
        return "package-x-generic"

class PackageSearchSource (Source):
    def __init__(self, query):
        self.query = query
        Source.__init__(self, _('Packages matching "%s"') % query)

    def repr_key(self):
        return self.query

    def get_items(self):
        package = kupferstring.tolocale(self.query)
        c_in, c_out_err = os.popen4(['apt-cache', 'search', '--names-only', package])
        try:
            c_in.close()
            acp_out = c_out_err.read()
            for line in kupferstring.fromlocale(acp_out).splitlines():
                if not line.strip():
                    continue
                if not " - " in line:
                    self.output_error("apt-cache: ", line)
                    continue
                package, desc = line.split(" - ", 1)
                yield Package(package, desc)
        finally:
            c_out_err.close()

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield TextLeaf
    def get_icon_name(self):
        return "system-software-install"

class SearchPackageName (Action):
    def __init__(self):
        Action.__init__(self, _("Search Package Name..."))

    def is_factory(self):
        return True

    def activate(self, leaf):
        package = leaf.object.strip()
        return PackageSearchSource(package)

    def item_types(self):
        yield TextLeaf
    def valid_for_item(self, item):
        # check if it is a single word
        text = item.object
        return len(text.split(None, 1)) == 1

    def get_icon_name(self):
        return "system-software-install"

