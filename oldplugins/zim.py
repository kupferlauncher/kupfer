# -*- coding: UTF-8 -*-


__kupfer_name__ = _("Zim")
__kupfer_sources__ = ("ZimPagesSource", )
__kupfer_actions__ = (
        "CreateZimPage",
        "CreateZimPageInNotebook",
        "CreateZimQuickNote",
    )
__description__ = _("Access to Pages stored in Zim - "
                    "A Desktop Wiki and Outliner")
__version__ = "2011-12-03"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
import time

import gio
import glib

from kupfer.objects import Leaf, Action, Source, TextLeaf, TextSource
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import config, utils, pretty, icons, plugin_support


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "page_name_starts_colon",
        "label": _("Page names start with :colon"),
        "type": bool,
        "value": False,
    },
    {
        "key": "quicknote_basename",
        "label": _("Default page name for quick notes"),
        "type": str,
        "value": _("Note %x %X"),
        "tooltip": _("Strftime tags can be used: %H - hour, %M - minutes, etc\n"
                "Please check python documentation for details.\n"
                "NOTE: comma will be replaced by _"),
    },
    {
        "key": "quicknote_namespace",
        "label": _("Default namespace for quick notes"),
        "type": str,
        "value": "",
    },
)

'''
Changes:
    2011-12-02 Karol Będkowski
        fix loading notebook list from zim 0.53
    2011-12-03 Karol Będkowski
        add CreateZimQuickNote action
TODO:
    use FilesystemWatchMixin (?)
'''


def _start_zim(notebook, page):
    ''' Start zim and open given notebook and page. '''
    utils.spawn_async(("zim", notebook, page.replace("'", "_")))


class ZimPage(Leaf):
    """ Represent single Zim page """
    def __init__(self, page_id, page_name, notebook_path, notebook_name):
        Leaf.__init__(self, page_id, page_name)
        self.page = page_name
        self.notebook = notebook_path
        self.notebook_name = notebook_name

    def get_actions(self):
        yield OpenZimPage()
        yield CreateZimSubPage()

    def get_description(self):
        return _('Zim Page from Notebook "%s"') % self.notebook_name

    def get_icon_name(self):
        return "text-x-generic"


class CreateZimPage(Action):
    """ Create new page in default notebook """
    def __init__(self):
        Action.__init__(self, _('Create Zim Page'))

    def activate(self, leaf):
        notebook = _get_default_notebook()
        _start_zim(notebook, ":" + leaf.object.strip(':'))

    def get_description(self):
        return _("Create page in default notebook")

    def get_icon_name(self):
        return 'document-new'

    def item_types(self):
        yield TextLeaf


class CreateZimPageInNotebook(Action):
    """ Create new page in default notebook """
    def __init__(self):
        Action.__init__(self, _('Create Zim Page In...'))

    def activate(self, leaf, iobj):
        _start_zim(iobj.object, ":" + leaf.object.strip(':'))

    def get_icon_name(self):
        return 'document-new'

    def item_types(self):
        yield TextLeaf

    def requires_object(self):
        return True

    def object_types(self):
        yield ZimNotebook

    def object_source(self, for_item=None):
        return ZimNotebooksSource()


class CreateZimQuickNote(Action):
    """ Create new page using quicknote plugin """
    def __init__(self):
        Action.__init__(self, _('Insert QuickNote into Zim'))

    def activate(self, leaf):
        self._create_note(leaf.object)

    def activate_multiple(self, objects):
        text = '\n'.join(str(leaf.object) for leaf in objects)
        self._create_note(text)

    def get_description(self):
        return _("Quick note selected text into Zim notebook")

    def get_icon_name(self):
        return 'document-new'

    def item_types(self):
        yield TextLeaf

    def _create_note(self, text):
        argv = ['zim', '--plugin', 'quicknote', 'input=stdin']
        basename = __kupfer_settings__['quicknote_basename']
        if basename:
            try:
                basename = time.strftime(basename, time.localtime())
                basename = basename.replace(':', '_')
            except:
                pass
            argv.append("basename=" + basename)
        namespace = __kupfer_settings__['quicknote_namespace']
        if namespace:
            argv.append("namespace=" + namespace)

        def finish_callback(acommand, stdout, stderr):
            pretty.print_debug(__name__, "CreateZimQuickNote.finish_callback", acommand,
                    stdout, stderr)

        utils.AsyncCommand(argv, finish_callback, None, stdin=text)


class OpenZimPage(Action):
    """ Open Zim page  """
    rank_adjust = 10

    def __init__(self):
        Action.__init__(self, _('Open'))

    def activate(self, leaf):
        _start_zim(leaf.notebook, leaf.page)

    def get_icon_name(self):
        return 'document-open'

    def item_types(self):
        yield ZimPage


class CreateZimSubPage(Action):
    """ Open Zim page  """
    def __init__(self):
        Action.__init__(self, _('Create Subpage...'))

    def activate(self, leaf, iobj):
        _start_zim(leaf.notebook, leaf.page + ":" + iobj.object.strip(':'))

    def get_icon_name(self):
        return 'document-new'

    def item_types(self):
        yield ZimPage

    def requires_object(self):
        return True

    def object_types(self):
        yield TextLeaf

    def object_source(self, for_item=None):
        return TextSource()


def _read_zim_notebooks_old(zim_notebooks_file):
    ''' Yield (notebook name, notebook path) from zim config

    @notebook_name: Unicode name
    @notebook_path: Filesystem byte string
    '''
    # We assume the notebook description is UTF-8 encoded
    with open(zim_notebooks_file, 'r') as notebooks_file:
        for line in notebooks_file.readlines():
            if not line.startswith('_default_'):
                notebook_name, notebook_path = line.strip().split('\t', 2)
                notebook_name = notebook_name.decode("UTF-8", "replace")
                notebook_path = os.path.expanduser(notebook_path)
                yield (notebook_name, notebook_path)


def _get_default_notebook():
    ''' Find default notebook '''
    zim_notebooks_file = config.get_config_file("notebooks.list", package="zim")
    if not zim_notebooks_file:
        pretty.print_error(__name__, "Zim notebooks.list not found")
        return None
    lines = None
    with open(zim_notebooks_file, 'r') as notebooks_file:
        lines = notebooks_file.readlines()
    if not lines:
        return ''
    if lines[0].strip() == '[NotebookList]':
        # new version
        # first section looks like:
        # [NotebookList]
        # Default=~/doc/zim
        # ~/doc/zim
        # ~/tmp/test
        for line in lines[1:]:
            if line.startswith('Default='):
                _dummy, name = line.split('=', 1)
                name = name.strip()
                if name:
                    pretty.print_debug(__name__, '_get_default_notebook:', name)
                    return name
            return line
        return ''
    # old version
    # format '<notebook name | _default_>\t<path>'
    name = ''
    for line in lines:
        if '\t' in line:
            notebook_name, notebook_path = line.strip().split('\t', 1)
            if notebook_name == '_default_':
                # _default_ is pointing at name of the default notebook
                name = notebook_path.decode("UTF-8", "replace")
            else:
                # assume first notebook as default
                name = notebook_name.decode("UTF-8", "replace")
            break
    pretty.print_debug(__name__, '_get_default_notebook (old):', name)
    return name


def _read_zim_notebook_name(notebook_path):
    npath = os.path.join(notebook_path, "notebook.zim")
    with open(npath, "r") as notebook_file:
        for line in notebook_file:
            if line.startswith("name="):
                _ignored, b_name = line.strip().split("=", 1)
                us_name = b_name.decode("unicode_escape")
                return us_name
    return os.path.basename(notebook_path)


def _read_zim_notebooks_new(zim_notebooks_file):
    ''' Yield (notebook name, notebook path) from zim config

    NOTE: we can't use ConfigParser - zim config file is not parsable

    Sample file:
        [NotebookList]
        Default=~/doc/zim
        ~/doc/zim
        ~/tmp/test

        [Notebook]
        uri=~/doc/zim
        name=doc
        interwiki=None
        icon=

        [Notebook]
        ....

    @notebook_name: Unicode name
    @notebook_path: Filesystem byte string
    '''
    notebooks = []
    last_section = None
    with open(zim_notebooks_file, 'r') as notebooks_file:
        for line in notebooks_file:
            line = line.strip()
            if line.startswith("["):
                if line == '[Notebook]':
                    notebooks.append(dict())
                last_section = line
                continue
            if not line:
                last_section = None
                continue
            if last_section == '[Notebook]':
                if '=' in line:
                    key, val = line.split('=', 1)
                    notebooks[-1][key] = val
    for notebook in notebooks:
        uri = notebook.get('uri')
        if not uri:
            continue
        notebook_path = gio.File(os.path.expanduser(uri)).get_path()
        notebook_name = notebook.get('name')
        if not notebook_name:
            # old version: name don't present in config
            try:
                notebook_name = _read_zim_notebook_name(notebook_path)
            except IOError:
                pass
        if not notebook_name:
            notebook_name = notebook_path.split('/')[-1]
        yield (notebook_name, notebook_path)


def _get_zim_notebooks():
    ''' Yield (notebook name, notebook path) from zim config

    @notebook_name: Unicode name
    @notebook_path: Filesystem byte string
    '''
    # We assume the notebook description is UTF-8 encoded
    zim_notebooks_file = config.get_config_file("notebooks.list", package="zim")
    if not zim_notebooks_file:
        pretty.print_error(__name__, "Zim notebooks.list not found")
        return []
    try:
        config_first_line = None
        with open(zim_notebooks_file, 'r') as notebooks_file:
            config_first_line = notebooks_file.readline().strip()
        if config_first_line == "[NotebookList]":
            return _read_zim_notebooks_new(zim_notebooks_file)
        else:
            return _read_zim_notebooks_old(zim_notebooks_file)
    except IOError as err:
        pretty.print_error(__name__, err)


class ZimNotebook (Leaf):
    def get_gicon(self):
        return icons.get_gicon_for_file(self.object)


class ZimNotebooksSource (Source):
    def __init__(self):
        Source.__init__(self, _("Zim Notebooks"))

    def get_items(self):
        for name, path in _get_zim_notebooks():
            yield ZimNotebook(path, name)

    def get_icon_name(self):
        return "zim"

    def provides(self):
        yield ZimNotebook


class ZimPagesSource(AppLeafContentMixin, Source):
    ''' Index pages in all Zim notebooks '''
    appleaf_content_id = "zim"

    def __init__(self, name=_("Zim Pages")):
        Source.__init__(self, name)
        # path to file with list notebooks
        self._version = 2

    def get_items(self):
        strip_name_first_colon = not __kupfer_settings__["page_name_starts_colon"]
        for notebook_name, notebook_path in _get_zim_notebooks():
            for root, dirs, files in os.walk(notebook_path):
                # find pages in notebook
                for filename in files:
                    file_path = os.path.join(root, filename)
                    page_name, ext = os.path.splitext(file_path)
                    if not ext.lower() == ".txt":
                        continue
                    page_name = page_name.replace(notebook_path, "", 1)
                    # Ask GLib for the correct unicode representation
                    # of the page's filename
                    page_name = glib.filename_display_name(page_name)
                    if strip_name_first_colon:
                        page_name = page_name.lstrip(os.path.sep)
                    page_name = (page_name
                            .replace(os.path.sep, ":")
                            .replace("_", " "))
                    yield ZimPage(file_path, page_name, notebook_path,
                            notebook_name)

    def get_description(self):
        return _("Pages stored in Zim Notebooks")

    def get_icon_name(self):
        return "zim"

    def provides(self):
        yield ZimPage
