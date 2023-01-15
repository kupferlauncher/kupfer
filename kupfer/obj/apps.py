from __future__ import annotations

import typing as ty
from contextlib import suppress

from .base import Leaf, Source
from .exceptions import InvalidDataError
from .files import AppLeaf
from .helplib import FilesystemWatchMixin, PicklingHelperMixin


class AppLeafContentMixin:
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
    def get_leaf_repr(cls) -> AppLeaf | None:
        if not hasattr(cls, "_cached_leaf_repr"):
            cls._cached_leaf_repr = cls.__get_leaf_repr()  # type: ignore

        return cls._cached_leaf_repr  # type: ignore

    @classmethod
    def __get_appleaf_id_iter(cls) -> ty.Tuple[str, ...]:
        if isinstance(cls.appleaf_content_id, str):  # type: ignore
            ids = (cls.appleaf_content_id,)  # type: ignore
        else:
            ids = tuple(cls.appleaf_content_id)  # type: ignore

        return ids

    @classmethod
    def __get_leaf_repr(cls) -> ty.Optional[AppLeaf]:
        for appleaf_id in cls.__get_appleaf_id_iter():
            with suppress(InvalidDataError):
                return AppLeaf(app_id=appleaf_id)

        return None

    @classmethod
    def decorates_type(cls) -> ty.Type[Leaf]:
        return AppLeaf

    @classmethod
    def decorate_item(cls, leaf: Leaf) -> ty.Optional[AppLeafContentMixin]:
        if leaf == cls.get_leaf_repr():
            return cls()

        return None


class ApplicationSource(
    AppLeafContentMixin, Source, PicklingHelperMixin, FilesystemWatchMixin
):
    pass
