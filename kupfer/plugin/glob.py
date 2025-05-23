# TRANS: "Glob" is the matching files like a shell with "*.py" etc.
__kupfer_name__ = _("Glob")
__kupfer_actions__ = ("Glob",)
__description__ = _("Select objects using '*' and '?' as wildcards.")
__version__ = ""
__author__ = ""

import fnmatch
import re
import typing as ty

from kupfer.obj import Action, Leaf, OperationError, TextLeaf, TextSource
from kupfer.obj.compose import MultipleLeaf

if ty.TYPE_CHECKING:
    from gettext import gettext as _


class Glob(Action):
    def __init__(self):
        Action.__init__(self, _("Glob"))

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        return self.activate_multiple((leaf,), (iobj,))

    def activate_multiple(self, objects, iobjects):
        ## Do case-insensitive matching
        ## As a special case, understand '**/' prefix as recursive

        def get_subcatalog_matches(subcatalog, pat, recursive, paths):
            if len(paths) > 1000:  # noqa:PLR2004
                raise OperationError("Globbing way too many objects")

            for content in subcatalog.content_source().get_leaves():
                if recursive and content.has_content():
                    get_subcatalog_matches(content, pat, recursive, paths)
                elif re.match(pat, str(content), flags=re.IGNORECASE):
                    paths.append(content)

        paths: list[str] = []
        for iobj in iobjects:
            glob = iobj.object
            if glob.startswith("**/"):
                glob = glob[3:]
                recursive = True
            else:
                recursive = False

            pat = fnmatch.translate(glob)
            for obj in objects:
                get_subcatalog_matches(obj, pat, recursive, paths)

        if paths:
            return MultipleLeaf(paths)

        return None

    def has_result(self):
        return True

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        return leaf.has_content()

    def requires_object(self):
        return True

    def object_types(self):
        yield TextLeaf

    def object_source(self, for_item=None):
        return TextSource()

    def valid_object(self, iobj, for_item):
        return ("*" in iobj.object) or ("?" in iobj.object)

    def get_description(self):
        return __description__
