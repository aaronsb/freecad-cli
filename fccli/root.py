# SPDX-License-Identifier: LGPL-2.1-or-later

"""The directory the terminal navigates (ADR-601).

A real directory on disk, laid out after the Filesystem Hierarchy
Standard, that the terminal treats as `/`:

    ~/.local/share/fccli/            /
      bin/                           .fccli scripts on the path
      lib/commands -> <addon>/fccli/lib/commands   what ships, read-only
      lib/addons/<name> -> <Mod>/<name>/fccli      what each addon ships
      etc/                           local overrides
      macros -> FreeCAD's MacroPath  the Python tier
      <anything>/                    the operator's own directories

`lib` is a real directory holding symlinks rather than one symlink to the
addon: the per-machine addon links have to live somewhere that is not the
repository. The other symlinks are made on first run, targets read from
the addon's install path and FreeCAD's preference, never written to.

The root is a jail. A path is resolved against it and never escapes;
`cd ..` at `/` stays at `/`. What lies outside is reached by a symlink
somebody made on purpose.

The working directory is session state: one per FreeCAD process, shown
in both terminals, moved by `cd` from either.
"""

import os
import posixpath

from . import paths as _paths

MOD_DIRS = [
    os.path.expanduser("~/.local/share/FreeCAD/v1-1/Mod"),
    os.path.expanduser("~/.local/share/FreeCAD/Mod"),
]
ADDON_DIR = "fccli"          # what an addon ships beside its code
DEFAULT_MACROS = os.path.expanduser("~/.local/share/FreeCAD/Macro")


def root():
    return _paths.data_dir()


def _macro_path():
    """FreeCAD's macro directory, from its preference. Read, never set."""
    try:
        import FreeCAD as App
        grp = App.ParamGet("User parameter:BaseApp/Preferences/Macro")
        return grp.GetString("MacroPath", "") or DEFAULT_MACROS
    except Exception:
        return DEFAULT_MACROS


def _mkdir(path, notes, base=None):
    """A real directory at path. Returns whether there is one.

    A symlink inside the root where a directory should be is somebody's,
    and nothing is made inside it: makedirs would follow it and write
    into whatever it points at. The root itself may be a link -- that is
    the operator saying where their root lives, to keep it in git -- and
    is followed. A file where a directory should be is said once.
    """
    name = os.path.relpath(path, base) if base else "the root"
    if os.path.islink(path) and base is not None:
        notes.append(f"{name} is a link; nothing is made inside it")
        return False
    if os.path.isdir(path):
        return True
    if os.path.exists(path):
        notes.append(f"{name} is a file where a directory should be")
        return False
    try:
        os.makedirs(path)
        return True
    except OSError as exc:
        notes.append(f"{name}: {exc}")
        return False


def _link(path, target, notes):
    """A symlink at path to target, when target exists.

    A real directory at path is somebody's and is left alone; a stale
    symlink is replaced; a missing or relative target is noted and
    skipped -- a relative one would be resolved from the link's own
    directory and dangle.
    """
    if not os.path.isabs(target) or not os.path.isdir(target):
        notes.append(f"{os.path.basename(path)}: {target} is not there")
        return
    if os.path.islink(path):
        if os.readlink(path) == target:
            return
        os.remove(path)
    elif os.path.exists(path):
        return
    try:
        os.symlink(target, path)
    except OSError as exc:
        notes.append(f"{os.path.basename(path)}: {exc}")


def layout(base=None):
    """Make the root as the ADR lays it out. Returns notes worth saying."""
    base = base or root()
    notes = []
    if not _mkdir(base, notes):
        return notes
    _mkdir(os.path.join(base, "bin"), notes, base)
    _mkdir(os.path.join(base, "etc"), notes, base)
    if _mkdir(os.path.join(base, "lib"), notes, base):
        here = os.path.dirname(os.path.abspath(__file__))
        _link(os.path.join(base, "lib", "commands"),
              os.path.join(here, "lib", "commands"), notes)
        if _mkdir(os.path.join(base, "lib", "addons"), notes, base):
            for mod in MOD_DIRS:
                if not os.path.isdir(mod):
                    continue
                for name in sorted(os.listdir(mod)):
                    shipped = os.path.join(mod, name, ADDON_DIR)
                    if os.path.isdir(shipped) and name != "freecad-cli":
                        _link(os.path.join(base, "lib", "addons", name),
                              shipped, notes)
    _link(os.path.join(base, "macros"), _macro_path(), notes)
    return notes


# --------------------------------------------------------------- paths

def resolve(cwd, path=""):
    """A virtual path, absolute, inside the jail.

    `cwd` is virtual (`/plinth`), `path` is what was typed. `..` above
    the root stays at the root; nothing here follows a symlink, so a link
    that points outside is reached through its name and never resolved
    past it.
    """
    if not path:
        return cwd or "/"
    joined = path if path.startswith("/") else posixpath.join(cwd or "/", path)
    parts = []
    for piece in joined.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            if parts:
                parts.pop()
            continue
        parts.append(piece)
    return "/" + "/".join(parts)


def real(virtual, base=None):
    """The on-disk path of a virtual one."""
    return os.path.join(base or root(), *[p for p in virtual.split("/") if p])


def kind(real_path):
    """One character after a name, the way `ls -F` says it."""
    if os.path.islink(real_path):
        return "@" if not os.path.isdir(real_path) else "/"
    if os.path.isdir(real_path):
        return "/"
    if real_path.endswith(".fccli"):
        return "*"
    return ""


def listing(virtual, base=None, marked=True):
    """Names in a directory, directories first and ending in /.

    `marked` adds the other `ls -F` characters -- * for a script, @ for a
    link -- for a listing somebody reads. Completion asks without them:
    a marker inserted into the line is a name that is not there.
    """
    here = real(virtual, base)
    if not os.path.isdir(here):
        raise FileNotFoundError(f"{virtual}: not a directory")
    try:
        names = sorted(n for n in os.listdir(here) if not n.startswith("."))
    except OSError as exc:
        raise FileNotFoundError(f"{virtual}: {exc.strerror}")
    dirs = [n + "/" for n in names if os.path.isdir(os.path.join(here, n))]
    files = [n + (kind(os.path.join(here, n)) if marked else "")
             for n in names if not os.path.isdir(os.path.join(here, n))]
    return dirs + files


LIMIT = 200_000


def read(virtual, base=None, limit=LIMIT):
    """(text, truncated) of a file, printable characters only."""
    here = real(virtual, base)
    if os.path.isdir(here):
        raise IsADirectoryError(f"{virtual}: is a directory")
    try:
        with open(here, encoding="utf-8", errors="replace") as fh:
            text = fh.read(limit + 1)
    except OSError as exc:
        raise FileNotFoundError(f"{virtual}: {exc.strerror}")
    truncated = len(text) > limit
    text = "".join(c if c.isprintable() or c in "\t\n" else "?"
                   for c in text[:limit])
    return text, truncated
