"""
Module provide function to read Thunderbird's address book.

Concept for mork parser from:
    - demork.py by Kumaran Santhanam
    - mork.cs from GnomeDo by Pierre Östlund

2021-01-01 Add support sqlite address book file format
2022-06-14 Support new (?) sqlite address book file format; load also
           history.sqlite
"""

import os
import re
import sqlite3
import time
import typing as ty
from configparser import RawConfigParser
from contextlib import closing

from kupfer.support import pretty

__version__ = "2021-01-01"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

_THUNDERBIRD_HOME = [
    os.path.expanduser(name)
    for name in ("~/.mozilla-thunderbird/", "~/.thunderbird", "~/.icedove/")
]

_THUNDERBIRD_PROFILES = [
    (thome, os.path.join(thome, "profiles.ini")) for thome in _THUNDERBIRD_HOME
]


_RE_COLS = re.compile(r"<\s*<\(a=c\)>\s*(\/\/)?\s*(\(.+?\))\s*>")
_RE_CELL = re.compile(r"\((.+?)\)")
_RE_ATOM = re.compile(r"<\s*(\(.+?\))\s*>")
_RE_TABLE = re.compile(
    r"\{-?(\d+):\^(..)\s*\{\(k\^(..):c\)\(s=9u?\)\s*(.*?)\}\s*(.+?)\}"
)
_RE_ROW = re.compile(r"(-?)\s*\[(.+?)((\(.+?\)\s*)*)\]")
_RE_CELL_TEXT = re.compile(r"\^(.+?)=(.*)")
_RE_CELL_OID = re.compile(r"\^(.+?)\^(.+)")
_RE_TRAN_BEGIN = re.compile(r"@\$\$\{.+?\{\@")
_RE_TRAN_END = re.compile(r"@\$\$\}.+?\}\@")


_COLS_TO_KEEP = (
    "DisplayName",
    "FirstName",
    "LastName",
    "PrimaryEmail",
    "SecondEmail",
)

SPECIAL_CHARS = (
    ("\\\\", "\\"),
    ("\\$", "$"),
    ("\\t", chr(9)),
    ("\\n", chr(10)),
)

RE_ESCAPED = re.compile(r"(\$[a-f0-9]{2})", re.IGNORECASE)
RE_ESCAPEDB = re.compile(rb"(\$[a-f0-9]{2})", re.IGNORECASE)
RE_HEADER = re.compile(r'// <!-- <mdb:mork:z v="(.*)"/> -->')


class _Table:
    def __init__(self, tableid):
        self.tableid = tableid
        self.rows = {}

    def __repr__(self):
        return f"Table {self.tableid!r}: {self.rows!r}"

    def add_cell(self, rowid: str, col: str, atom: str) -> None:
        if ":" in rowid:
            rowid = rowid.split(":")[0]

        row = self.rows.get(rowid)
        if not row:
            row = self.rows[rowid] = {}

        row[col] = _unescape_data(atom)

    def del_row(self, rowid: str) -> None:
        if ":" in rowid:
            rowid = rowid.split(":")[0]

        if rowid in self.rows:
            del self.rows[rowid]


def _unescape_byte(match: re.Match[bytes]) -> bytes:
    value = match.group()
    return bytes([int(value[1:], 16)])


def _unescape_data(instr: str) -> str:
    for src, dst in SPECIAL_CHARS:
        instr = instr.replace(src, dst)

    if RE_ESCAPED.search(instr) is not None:
        inbytes = instr.encode("utf-8")
        instr = RE_ESCAPEDB.sub(_unescape_byte, inbytes).decode(
            "utf-8", "replace"
        )

    return instr


def _read_mork_filecontent(filename: str) -> ty.Iterable[str]:
    with open(filename, encoding="UTF-8") as mfile:
        header = mfile.readline().strip()
        # check header
        if not RE_HEADER.match(header):
            pretty.print_debug(__name__, "_read_mork: header error", header)
            return

        for line in mfile:
            # remove blank lines and comments
            line = line.strip()  # noqa: PLW2901
            if not line:
                continue

            # remove comments
            if (comments := line.find("// ")) > -1:
                line = line[:comments].strip()  # noqa: PLW2901

            if line:
                yield line.replace("\\)", "$29")


# pylint: disable=too-many-locals,too-many-nested-blocks,too-many-branches
# pylint: disable=too-many-statements
def _read_mork(filename: str) -> dict[str, _Table]:  # noqa:PLR0915,PLR0912
    """Read mork file, return tables from file"""

    data = "".join(_read_mork_filecontent(filename))
    if not data:
        return {}

    # decode data
    cells = {}
    atoms = {}
    tables: dict[str, _Table] = {}
    pos = 0
    active_trans = False
    while data:
        data = data[pos:].lstrip()
        if not data:
            break

        # cols
        if match := _RE_COLS.match(data):
            for cell in _RE_CELL.findall(match.group()):
                key, val = cell.split("=", 1)
                if val in _COLS_TO_KEEP:  # skip necessary columns
                    cells[key] = val

            pos = match.span()[1]
            continue

        # atoms
        if match := _RE_ATOM.match(data):
            for cell in _RE_CELL.findall(match.group()):
                if "=" in cell:
                    key, val = cell.split("=", 1)
                    atoms[key] = val

            pos = match.span()[1]
            continue

        # tables
        if match := _RE_TABLE.match(data):
            tableid = ":".join(match.groups()[0:2])
            table = tables.get(tableid)
            if not table:
                table = tables[tableid] = _Table(tableid)

            for row in _RE_ROW.findall(match.group()):
                tran, rowid = row[:2]
                if active_trans and rowid[0] == "-":
                    rowid = rowid[1:]
                    table.del_row(rowid)

                if not active_trans or tran != "-":
                    rowdata = row[2:]
                    rowcell: str
                    for rowcell in filter(None, rowdata):
                        for cell in _RE_CELL.findall(rowcell):
                            atom, col = None, None
                            if cmatch := _RE_CELL_TEXT.match(cell):
                                col = cells.get(cmatch.group(1))
                                atom = cmatch.group(2)
                            elif cmatch := _RE_CELL_OID.match(cell):
                                col = cells.get(cmatch.group(1))
                                atom = atoms.get(cmatch.group(2))

                            if col and atom:
                                table.add_cell(rowid, col, atom)

            pos = match.span()[1]
            continue

        # transaction
        if _RE_TRAN_BEGIN.match(data):
            active_trans = True
            continue

        if _RE_TRAN_END.match(data):
            tran = True
            continue

        # dangling rows
        if match := _RE_ROW.match(data):
            row = match.groups()
            tran, rowid = row[:2]
            table = tables.get("1:80")  # bind to default table
            if rowid[0] == "-":
                rowid = rowid[1:]
                if table:
                    table.del_row(rowid)

            if tran != "-" and (rowdata := row[2:]):
                if not table:
                    table = tables["1:80"] = _Table("1:80")

                for rowcell in filter(None, rowdata):
                    for cell in _RE_CELL.findall(rowcell):
                        atom, col = None, None
                        if cmatch := _RE_CELL_TEXT.match(cell):
                            col = cells.get(cmatch.group(1))
                            atom = cmatch.group(2)
                        elif cmatch := _RE_CELL_OID.match(cell):
                            col = cells.get(cmatch.group(1))
                            atom = atoms.get(cmatch.group(2))

                        if col and atom:
                            table.add_cell(rowid, col, atom)

            pos = match.span()[1]
            continue

        pos = 1

    return tables


def _mork2contacts(tables: dict[str, _Table]) -> ty.Iterator[tuple[str, str]]:
    """Get contacts from mork table prepared by _read_mork"""
    if not tables:
        return
    # get only default table
    if table := tables.get("1:80"):
        for row in table.rows.values():
            display_name = row.get("DisplayName")
            if not display_name:
                first_name = row.get("FirstName", "")
                last_name = row.get("LastName", "")
                display_name = " ".join((first_name, last_name))

            if display_name:
                display_name = display_name.strip()

            for key in ("PrimaryEmail", "SecondEmail"):
                if email := row.get(key):
                    yield (display_name or email[: email.find("@")], email)


_ABOOK_CONTACTS_SQL = """
select
    (select value from properties
     where card = c.uid and name = 'FirstName'
    ) as FirstName,
    (select value from properties
     where card = c.uid and name = 'LastName'
    ) as LastName,
    (select value from properties
     where card = c.uid and name = 'DisplayName'
    ) as DisplayName,
    (select value from properties
     where card = c.uid and name = 'PrimaryEmail'
    ) as PrimaryEmail,
    (select value from properties
     where card = c.uid and name = 'SecondEmail'
    ) as SecondEmail
from cards c
"""

# new version of abook.sqlite file
_ABOOK_CONTACTS_SQL2 = """
select
    (select value from properties
     where card = c.card and name = 'FirstName'
    ) as FirstName,
    (select value from properties
     where card = c.card and name = 'LastName'
    ) as LastName,
    (select value from properties
     where card = c.card and name = 'DisplayName'
    ) as DisplayName,
    (select value from properties
     where card = c.card and name = 'PrimaryEmail'
    ) as PrimaryEmail,
    (select value from properties
     where card = c.card and name = 'SecondEmail'
    ) as SecondEmail
from (select distinct card from properties) c
"""


def _load_abook_sqlite(filename: str) -> ty.Iterator[tuple[str, str]]:
    """Load contacts from abook.sqlite filename.

    Thunderbird (like firefox) lock database, so it mus be opened as immutable
    and read-only. Also changes may be not visible immediate - require close
    sqlite file by thunderbird.
    """

    dbfpath = filename.replace("?", "%3f").replace("#", "%23")
    dbfpath = "file:" + dbfpath + "?immutable=1&mode=ro"

    for _ in range(2):
        try:
            pretty.print_debug(__name__, "_load_abook_sqlite load:", dbfpath)
            with closing(
                sqlite3.connect(dbfpath, uri=True, timeout=1)
            ) as conn:
                cur = conn.cursor()

                # check db version
                cur.execute(
                    "select count(*) from sqlite_schema "
                    "where name = 'list_cards'"
                )
                ver = cur.fetchone()[0]
                abook_query = (
                    _ABOOK_CONTACTS_SQL2 if ver else _ABOOK_CONTACTS_SQL
                )
                cur.execute(abook_query)

                for (
                    first_name,
                    last_name,
                    display_name,
                    primary_email,
                    second_email,
                ) in cur:
                    display_name = display_name or " ".join(  # noqa: PLW2901
                        filter(None, (first_name, last_name))
                    )
                    for email in (primary_email, second_email):
                        if email:
                            yield (
                                display_name or email.partition("@")[0],
                                email,
                            )
            return
        except sqlite3.Error as err:  # noqa: PERF203
            # Something is wrong with the database
            # wait short time and try again
            pretty.print_debug(__name__, "_load_abook_sqlite error:", str(err))
            time.sleep(1)


def get_addressbook_dirs() -> ty.Iterator[str]:
    """Get path to addressbook file from default profile."""
    for thome, tprofile in _THUNDERBIRD_PROFILES:
        if os.path.isfile(tprofile):
            config = RawConfigParser()
            config.read(tprofile)
            for section in config.sections():
                if config.has_option(section, "Path"):
                    path = config.get(section, "Path")
                    if not os.path.isabs(path):
                        path = os.path.join(thome, path)

                    if os.path.isdir(path):
                        yield path


def get_addressbook_files() -> ty.Iterator[str]:
    """Get full path to all Thunderbird address book files."""
    for path in get_addressbook_dirs():
        pretty.print_debug(__name__, "get_addressbook_files dir:", path)
        with os.scandir(path) as entries:
            for entry in entries:
                if not entry.is_file():
                    continue

                if (
                    entry.name.endswith(".mab")
                    or (
                        entry.name.endswith(".sqlite")
                        and entry.name.startswith("abook")
                    )
                    or entry.name == "history.sqlite"
                ):
                    yield entry.path


def get_contacts() -> ty.Iterator[tuple[str, str]]:
    """Get all contacts from all Thunderbird address books as
    ((contact name, contact email))"""
    for abook in get_addressbook_files():
        pretty.print_debug(__name__, "get_contacts:", abook)
        if abook.endswith(".sqlite"):
            try:
                yield from _load_abook_sqlite(abook)
            except Exception as err:
                pretty.print_error(__name__, "get_contacts error", abook, err)
        else:
            try:
                tables = _read_mork(abook)
            except OSError as err:
                pretty.print_error(__name__, "get_contacts error", abook, err)
            else:
                yield from _mork2contacts(tables)


if __name__ == "__main__":
    print("\n".join(map(str, sorted(get_contacts()))))
