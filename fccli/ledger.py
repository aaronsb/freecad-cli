# SPDX-License-Identifier: LGPL-2.1-or-later

"""What a verification sweep found, joined to a command at read time.

``tools/verify.py`` drives each authored `example` and stamps
``fccli/verified.json`` with the date, the FreeCAD version, the mode and
the result (ADR-501). The record is machine output, so it lives beside
the command tree rather than inside it, and the tools that need both --
`man`, the reports -- join them here by command id.

The join matters because an example on its own says nothing about
whether it runs. Seventeen of the stamped examples are recorded
`broken`, and a page that printed one of those as an invocation would be
making a claim the sweep already refuted.
"""

import json
import os

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "verified.json")

_CACHE = {}


def _read(path):
    """The ledger's command table, or an empty one.

    A file that will not parse is treated as absent, the way
    ``factory.load_dictionary`` treats a broken dictionary: a bad ledger
    costs the stamps, never the pages.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("commands") or {}
    except (OSError, ValueError, AttributeError):
        return {}


def load(path=None):
    path = path or LEDGER
    if path not in _CACHE:
        _CACHE[path] = _read(path)
    return _CACHE[path]


def forget():
    """Drop the cache. For a test that writes a ledger of its own."""
    _CACHE.clear()


def stamp(command, example, path=None):
    """This command's record, when it is a record of *this* invocation.

    A ledger entry names the example it drove. An authored example edited
    after the sweep leaves the stamp attached to text nobody typed, so an
    entry whose `example` has moved on is no evidence about the one the
    page is showing and is withheld.
    """
    if not command:
        return None
    entry = load(path).get(command)
    if not entry:
        return None
    if example and entry.get("example") != example:
        return None
    return entry
