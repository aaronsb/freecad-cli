# SPDX-License-Identifier: LGPL-2.1-or-later

"""Where the running code actually came from.

A semantic version alone cannot answer "is this the build with the fix?" for
anyone running from a checkout, which is everyone during development. So the
banner carries a commit too.

Two sources. Live git wins wherever there is a checkout to ask, because a
dev install is a symlink into the working tree and the answer there changes
with every commit. The ``_build.py`` stamped at release time answers for a
build shipped without git, which is what it was written for.

Reading the stamp first, as this did, meant a release froze the reported
commit for every run afterwards: `make release` stamps, and from then on a
working tree reports the released commit no matter what was committed
since. Neither source being available is fine -- the version prints alone.
"""

import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
_CACHE = None


def _stamped():
    try:
        from ._build import COMMIT, BUILT  # noqa: F401
        return {"commit": COMMIT, "built": BUILT, "source": "release"}
    except Exception:
        return None


def _from_git():
    """The addon directory, or whatever it is a symlink to."""
    root = os.path.dirname(os.path.realpath(HERE))
    if not os.path.isdir(os.path.join(root, ".git")):
        return None
    def git(*args):
        return subprocess.run(("git", "-C", root) + args, capture_output=True,
                              text=True, timeout=2).stdout.strip()
    try:
        commit = git("rev-parse", "--short", "HEAD")
        if not commit:
            return None
        dirty = bool(git("status", "--porcelain"))
        return {"commit": commit + ("-dirty" if dirty else ""),
                "built": git("log", "-1", "--format=%cs"),
                "source": "git"}
    except Exception:
        return None


def info():
    global _CACHE
    if _CACHE is None:
        _CACHE = _from_git() or _stamped() or {}
    return _CACHE


def describe():
    """``<version>+<commit> (<date>)`` -- version, build, and when.

    The date is the commit date rather than an install or import time, so
    two people running the same build see the same string.
    """
    from . import __version__
    data = info()
    commit, built = data.get("commit"), data.get("built")
    out = f"{__version__}+{commit}" if commit else __version__
    return f"{out} ({built})" if built else out
