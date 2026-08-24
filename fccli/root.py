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


def _link(path, target, notes):
    """A symlink at path to target, when target exists.

    A real directory at path is somebody's and is left alone; a stale
    symlink is replaced; a missing target is noted and skipped.
    """
    if not os.path.isdir(target):
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
    for d in ("bin", "etc", "lib", os.path.join("lib", "addons")):
        os.makedirs(os.path.join(base, d), exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    _link(os.path.join(base, "lib", "commands"),
          os.path.join(here, "lib", "commands"), notes)
    for mod in MOD_DIRS:
        if not os.path.isdir(mod):
            continue
        for name in sorted(os.listdir(mod)):
            shipped = os.path.join(mod, name, ADDON_DIR)
            if os.path.isdir(shipped) and name != "freecad-cli":
                _link(os.path.join(base, "lib", "addons", name), shipped, notes)
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


def listing(virtual, base=None):
    """Names in a directory, marked, directories first."""
    here = real(virtual, base)
    if not os.path.isdir(here):
        raise FileNotFoundError(f"{virtual}: not a directory")
    names = sorted(n for n in os.listdir(here) if not n.startswith("."))
    dirs = [n + "/" for n in names if os.path.isdir(os.path.join(here, n))]
    files = [n + kind(os.path.join(here, n)) for n in names
             if not os.path.isdir(os.path.join(here, n))]
    return dirs + files


def read(virtual, base=None, limit=200_000):
    here = real(virtual, base)
    if os.path.isdir(here):
        raise IsADirectoryError(f"{virtual}: is a directory")
    with open(here, encoding="utf-8", errors="replace") as fh:
        return fh.read(limit)
