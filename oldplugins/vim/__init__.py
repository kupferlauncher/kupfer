__kupfer_name__ = _("Vim")
__kupfer_sources__ = ("RecentsSource", "ActiveVim", )
__kupfer_actions__ = ("InsertInVim", )
__description__ = _("Recently used documents in Vim")
__version__ = "2011-04"
__author__ = "Plugin: Ulrik Sverdrup, VimCom: Ali Afshar"


def initialize_plugin(name):
    global RecentsSource
    global ActiveVim
    global InsertInVim
    from kupfer.plugin.vim.plugin import RecentsSource, ActiveVim, InsertInVim
