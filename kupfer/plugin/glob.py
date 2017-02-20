
# TRANS: "Glob" is the matching files like a shell with "*.py" etc.
__kupfer_name__ = _("Glob")
__kupfer_actions__ = ("Glob",)
__description__ = _("Select objects using '*' and '?' as wildcards.")
__version__ = ""
__author__ = ""

import fnmatch
import re

from kupfer.objects import Action, TextLeaf, TextSource, Leaf, OperationError
from kupfer.obj.compose import MultipleLeaf

class Glob (Action):
    def __init__(self):
        Action.__init__(self, _("Glob"))

    def activate(self, obj, iobj):
        return self.activate_multiple((obj,), (iobj, ))

    def activate_multiple(self, objects, iobjects):
        ## Do case-insentive matching
        ## As a special case, understand '**/' prefix as recurive

        def get_subcatalog_matches(subcatalog, pat, recursive, paths):
            if len(paths) > 1000:
                raise OperationError("Globbing wayy too many objects")
            for content in subcatalog.content_source().get_leaves():
                if recursive and content.has_content():
                    get_subcatalog_matches(content, pat, recursive, paths)
                else:
                    if re.match(pat, str(content), flags=re.I):
                        paths.append(content)
        paths = []
        for iobj in iobjects:
            glob = iobj.object
            if glob.startswith('**/'):
                glob = glob[3:]
                recursive = True
            else:
                recursive = False
            pat = fnmatch.translate(glob)
            for obj in objects:
                get_subcatalog_matches(obj, pat, recursive, paths)
        if paths:
            return MultipleLeaf(paths)

    def has_result(self):
        return True
    def item_types(self):
        yield Leaf
    def valid_for_item(self, item):
        return item.has_content()
    def requires_object(self):
        return True
    def object_types(self):
        yield TextLeaf
    def object_source(self, for_item=None):
        return TextSource()
    def valid_object(self, iobj, for_item):
        return ('*' in iobj.object) or ('?' in iobj.object)

    def get_description(self):
        return __description__
