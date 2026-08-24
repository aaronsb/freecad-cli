# SPDX-License-Identifier: LGPL-2.1-or-later

"""Where files go.

Three paths were spelled out by hand in three modules, all of them
`~/.local/share/FreeCAD/fccli/...`, none of them reading the environment.
That is wrong twice over: it ignores `XDG_DATA_HOME`, and it puts a history
file in the data directory when the spec has a place for exactly this.

    XDG_STATE_HOME   state that should persist between restarts but is not
                     important or portable enough for the data directory --
                     the spec names history files as the example.
    XDG_DATA_HOME    what the user authored and would miss: aliases, their
                     own patches.

Reads fall back to the old location so an existing history is not lost.
Writes only ever go to the new one, and nothing is moved or deleted -- a
file left behind costs a few kilobytes, and guessing wrong about somebody's
data costs more than that.
"""

import os

APP = "fccli"

# Where these files lived before this module existed.
LEGACY = os.path.join(os.path.expanduser("~"), ".local", "share",
                      "FreeCAD", "fccli")


def _home(var, *default):
    root = os.environ.get(var)
    if not root:
        root = os.path.join(os.path.expanduser("~"), *default)
    return os.path.join(root, APP)


def state_dir():
    """History and anything else the program accumulates by being used."""
    return _home("XDG_STATE_HOME", ".local", "state")


def data_dir():
    """Aliases, patches -- what the user wrote down on purpose."""
    return _home("XDG_DATA_HOME", ".local", "share")


def state(name):
    return os.path.join(state_dir(), name)


def data(name):
    return os.path.join(data_dir(), name)


def legacy(name):
    return os.path.join(LEGACY, name)


def readable(preferred, name):
    """The path to read from: the new one if it exists, else the old one.

    A first run after this module landed finds nothing at the new path and
    everything at the old, and should read the old. Once anything has been
    written to the new path it wins, so the fallback stops applying by
    itself rather than needing a flag.
    """
    if os.path.exists(preferred):
        return preferred
    old = legacy(name)
    return old if os.path.exists(old) else preferred


def ensure(path):
    """Make the directory a path sits in. Returns whether it is writable."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return True
    except OSError:
        return False
