"""
This is a plugin that should do everything wrong, for debugging Purposes
"""
__kupfer_name__ = u"Evil Plugin"
__kupfer_sources__ = (
    "EvilSource",
    "EvilInstantiationSource",
)
__description__ = u"Evil for debugging purposes (necessary evil)"
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


from kupfer.objects import Leaf, Action, Source

class EvilError (Exception):
    pass

class EvilInstantiationSource (Source):
    def __init__(self):
        raise EvilError

class EvilSource (Source):
    def __init__(self):
        Source.__init__(self, u"Evil Source")

    def initialize(self):
        raise EvilError

    def get_items(self):
        raise EvilError

    def get_icon_name(self):
        raise EvilError

    def provides(self):
        pass

