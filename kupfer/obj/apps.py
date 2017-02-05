from kupfer.obj.base import InvalidDataError, Source
from kupfer.obj.helplib import PicklingHelperMixin, FilesystemWatchMixin
from kupfer.obj.objects import AppLeaf

class AppLeafContentMixin (object):
    """
    Mixin for Source that correspond one-to-one with a AppLeaf

    This Mixin sees to that the Source is set as content for the application
    with id 'cls.appleaf_content_id', which may also be a sequence of ids.

    Source has to define the attribute appleaf_content_id and must
    inherit this mixin BEFORE the Source

    This Mixin defines:
    get_leaf_repr
    decorates_type,
    decorates_item
    """
    @classmethod
    def get_leaf_repr(cls):
        if not hasattr(cls, "_cached_leaf_repr"):
            cls._cached_leaf_repr = cls.__get_leaf_repr()
        return cls._cached_leaf_repr
    @classmethod
    def __get_appleaf_id_iter(cls):
        if isinstance(cls.appleaf_content_id, str):
            ids = (cls.appleaf_content_id, )
        else:
            ids = list(cls.appleaf_content_id)
        return ids
    @classmethod
    def __get_leaf_repr(cls):
        for appleaf_id in cls.__get_appleaf_id_iter():
            try:
                return AppLeaf(app_id=appleaf_id)
            except InvalidDataError:
                pass
    @classmethod
    def decorates_type(cls):
        return AppLeaf
    @classmethod
    def decorate_item(cls, leaf):
        if leaf == cls.get_leaf_repr():
            return cls()

class ApplicationSource(AppLeafContentMixin, Source, PicklingHelperMixin,
        FilesystemWatchMixin):
    pass

