"""
A test project to see if we can make a plugin that allows us to
drill down into compressed archives.

So far we only support .zip and .tar, .tar.gz, .tar.bz2, using Python's
standard library.
"""
from __future__ import annotations

__kupfer_name__ = _("Deep Archives")
__kupfer_contents__ = ("ArchiveContent",)
__description__ = _("Allow browsing inside compressed archive files")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import hashlib
import os
import shutil
import tarfile
import typing as ty
import zipfile
from pathlib import Path

from kupfer.obj import FileLeaf, Leaf, Source
from kupfer.obj.filesrc import DirectorySource
from kupfer.support import pretty, scheduler

if ty.TYPE_CHECKING:
    _ = str

# Limit this to archives of a couple of megabytes
MAX_ARCHIVE_BYTE_SIZE = 15 * 1024**2

# Wait a year, or until program shutdown for cleaning up
# archive files
VERY_LONG_TIME_S = 3600 * 24 * 365


class UnsafeArchiveError(Exception):
    def __init__(self, path: str):
        Exception.__init__(self, f"Refusing to extract unsafe path: {path}")


def _is_safe_to_unarchive(path: str) -> bool:
    "return whether @path is likely a safe path to unarchive"
    npth = os.path.normpath(path)
    return not os.path.isabs(npth) and not npth.startswith(os.path.pardir)


# pylint: disable=too-few-public-methods
class _Extractor:
    def __init__(self):
        self.extensions: list[str] = []
        self.predicate: ty.Callable[[str], bool] = None  # type: ignore

    def __call__(self, src: str, dst: str) -> None:
        pass


class ArchiveContent(Source):
    extractors: list[_Extractor] = []
    unarchived_files: list[str] = []
    end_timer = scheduler.Timer(True)

    def __init__(self, fileleaf, unarchive_func):
        Source.__init__(self, _("Content of %s") % fileleaf)
        self.path = fileleaf.object
        self.unarchiver = unarchive_func

    def repr_key(self):
        return self.path

    def get_items(self) -> ty.Iterable[Leaf]:
        # always use the same destination for the same file and mtime
        basename = os.path.basename(os.path.normpath(self.path))
        root, _ext = os.path.splitext(basename)
        mtime = os.stat(self.path).st_mtime
        fileid = hashlib.sha1((f"{self.path}{mtime}").encode()).hexdigest()
        pth = os.path.join("/tmp", f"kupfer-{root}-{fileid}")
        if not Path(pth).exists():
            self.output_debug(f"Extracting with {self.unarchiver}")
            self.unarchiver(self.path, pth)
            self.unarchived_files.append(pth)
            self.end_timer.set(VERY_LONG_TIME_S, self.clean_up_unarchived_files)

        files = list(DirectorySource(pth, show_hidden=True).get_leaves())
        if len(files) == 1 and files[0].has_content():
            csrc = files[0].content_source()
            return (csrc.get_leaves() or []) if csrc else []

        return files

    def get_description(self):
        return None

    @classmethod
    def decorates_type(cls):
        return FileLeaf

    @classmethod
    def decorate_item(cls, leaf):
        basename = os.path.basename(leaf.object).lower()
        for extractor in cls.extractors:
            if any(basename.endswith(ext) for ext in extractor.extensions):
                if Path(leaf.object).is_file() and extractor.predicate(
                    leaf.object
                ):
                    return cls._source_for_path(leaf, extractor)

        return None

    @classmethod
    def _source_for_path(cls, leaf, extractor):
        byte_size = os.stat(leaf.object).st_size
        if byte_size < MAX_ARCHIVE_BYTE_SIZE:
            return cls(leaf, extractor)

        return None

    @classmethod
    def clean_up_unarchived_files(cls):
        if not cls.unarchived_files:
            return

        pretty.print_info(__name__, "Removing extracted archives..")
        for filetree in set(cls.unarchived_files):
            pretty.print_debug(__name__, "Removing", os.path.basename(filetree))
            shutil.rmtree(filetree, onerror=cls._clean_up_error_handler)

        cls.unarchived_files = []

    @classmethod
    def _clean_up_error_handler(cls, func, path, exc_info):
        pretty.print_error(__name__, f"Error in {func} deleting {path}:")
        pretty.print_error(__name__, exc_info)

    @classmethod
    def extractor(cls, extensions, predicate):
        def decorator(func):
            func.extensions = extensions
            func.predicate = predicate
            cls.extractors.append(func)
            return func

        return decorator


@ArchiveContent.extractor(
    (".tar", ".tar.gz", ".tgz", ".tar.bz2"), tarfile.is_tarfile
)
def extract_tarfile(filepath, destpath):
    with tarfile.TarFile.open(filepath, "r") as zfile:
        try:
            for member in zfile.getnames():
                if not _is_safe_to_unarchive(member):
                    raise UnsafeArchiveError(member)

            zfile.extractall(path=destpath)
        finally:
            pass


# ZipFile only supports extractall since Python 2.6
@ArchiveContent.extractor((".zip",), zipfile.is_zipfile)
def extract_zipfile(filepath, destpath):
    with zipfile.ZipFile(filepath, "r") as zfile:
        try:
            for member in zfile.namelist():
                if not _is_safe_to_unarchive(member):
                    raise UnsafeArchiveError(member)

            zfile.extractall(path=destpath)
        finally:
            pass
