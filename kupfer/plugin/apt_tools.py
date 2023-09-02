from __future__ import annotations

__kupfer_name__ = _("APT")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
    "ShowPackageInfo",
    "SearchPackageName",
    "InstallPackage",
    "OpenPackageWebsite",
    "SearchForFile",
)
__description__ = _("Interface with the package manager APT")
__version__ = ""
__author__ = (
    "Martin Koelewijn <martinkoelewijn@gmail.com>, "
    "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"
)

import subprocess
import typing as ty
import urllib.parse

from kupfer import icons, launch, plugin_support, support
from kupfer.obj import Action, Leaf, Source, TextLeaf
from kupfer.support import kupferstring, task
from kupfer.ui import uiutils

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "installation_method",
        "label": _("Installation method"),
        "type": str,
        "value": "gksu -- apt-get install --yes",
    },
)

plugin_support.check_command_available("apt", "apt-cache")

if ty.TYPE_CHECKING:
    _ = str


# pylint: disable=too-few-public-methods
class InfoTask(task.Task):
    def __init__(self, text: str):
        super().__init__()
        self.text = text
        self.aptitude: bytes | None = None
        self.apt_cache: bytes | None = None
        self._finish_callback = None

    def start(self, finish_callback):
        self._finish_callback = finish_callback
        timeout = 60
        launch.AsyncCommand(
            ["apt", "show", self.text], self._aptitude_finished, timeout
        )
        launch.AsyncCommand(
            ["apt-cache", "policy", self.text],
            self._aptcache_finished,
            timeout,
        )

    def _aptitude_finished(
        self, acommand: launch.AsyncCommand, stdout: bytes, stderr: bytes
    ) -> None:
        self.aptitude = stderr + stdout
        self._check_end()

    def _aptcache_finished(
        self, acommand: launch.AsyncCommand, stdout: bytes, stderr: bytes
    ) -> None:
        self.apt_cache = stderr + stdout
        self._check_end()

    def _check_end(self):
        if self.aptitude is None or self.apt_cache is None:
            return

        assert self._finish_callback
        text = kupferstring.fromlocale(self.aptitude) + kupferstring.fromlocale(
            self.apt_cache
        )
        uiutils.show_text_result(text, title=_("Show Package Information"))
        self._finish_callback(self)


class ShowPackageInfo(Action):
    def __init__(self):
        Action.__init__(self, _("Show Package Information"))
        self.kupfer_add_alias("apt show")

    def is_async(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        return InfoTask(leaf.object.strip())

    def item_types(self):
        yield TextLeaf
        yield Package

    def valid_for_item(self, leaf):
        # check if it is a single word
        text = leaf.object
        return len(text.split(None, 1)) == 1

    def get_gicon(self):
        return icons.ComposedIcon("dialog-information", "package-x-generic")


class OpenPackageWebsite(Action):
    def __init__(self):
        Action.__init__(self, _("Browse packages.debian.org"))

    def activate(self, leaf, iobj=None, ctx=None):
        name = leaf.object.strip()
        url = f"https://packages.debian.org/{name}"
        launch.show_url(url)

    def get_description(self):
        return _("Open packages.debian.org page for package")

    def item_types(self):
        yield TextLeaf
        yield Package

    def valid_for_item(self, leaf):
        # check if it is a single word
        text = leaf.object
        return len(text.split(None, 1)) == 1

    def get_gicon(self):
        return icons.ComposedIcon("edit-find", "package-x-generic")


class InstallPackage(Action):
    def __init__(self):
        Action.__init__(self, _("Install"))
        self.kupfer_add_alias("apt install")

    def activate(self, leaf, iobj=None, ctx=None):
        self.activate_multiple((leaf,))

    def activate_multiple(self, objs):
        program = __kupfer_settings__["installation_method"]
        pkgs = [o.object.strip() for o in objs]
        prog_argv = support.argv_for_commandline(program)
        launch.spawn_in_terminal(prog_argv + pkgs)

    def item_types(self):
        yield Package
        yield TextLeaf

    def get_description(self):
        return _("Install package using the configured method")

    def get_icon_name(self):
        return "document-save"


class Package(Leaf):
    def __init__(self, package: str, desc: str):
        Leaf.__init__(self, package, package)
        self.desc = desc

    def get_text_representation(self):
        return self.object

    def get_description(self):
        return self.desc

    def get_icon_name(self):
        return "package-x-generic"


class PackageSearchSource(Source):
    def __init__(self, query):
        self.query = query
        Source.__init__(self, _('Packages matching "%s"') % query)

    def repr_key(self):
        return self.query

    def get_items(self):
        proc = subprocess.run(
            ["apt-cache", "search", "--names-only", self.query],
            capture_output=True,
            check=True,
        )
        for line in kupferstring.fromlocale(proc.stdout).splitlines():
            line = line.strip()
            if not line:
                continue

            package, sep, desc = line.partition(" - ")
            if not sep:
                self.output_error("apt-cache: ", line)
                continue

            yield Package(package, desc)

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield TextLeaf

    def get_icon_name(self):
        return "system-software-install"


class SearchPackageName(Action):
    def __init__(self):
        Action.__init__(self, _("Search Package Name..."))
        self.kupfer_add_alias("apt search")

    def is_factory(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        package = leaf.object.strip()
        return PackageSearchSource(package)

    def item_types(self):
        yield TextLeaf

    def valid_for_item(self, leaf):
        # check if it is a single word
        text = leaf.object
        return len(text.split(None, 1)) == 1

    def get_icon_name(self):
        return "system-software-install"


class SearchForFile(Action):
    def __init__(self):
        Action.__init__(self, _("Search for file in packages..."))
        self.kupfer_add_alias("apt file")

    def activate(self, leaf, iobj=None, ctx=None):
        name = urllib.parse.quote(leaf.object.strip())
        url = f"https://packages.debian.org/file:{name}"
        launch.show_url(url)

    def get_description(self):
        return _(
            "Search the contents of Debian distributions for any files (online)"
        )

    def item_types(self):
        yield TextLeaf

    def valid_for_item(self, leaf):
        text = leaf.object
        return len(text) > 2

    def get_gicon(self):
        return icons.ComposedIcon("edit-find", "package-x-generic")
