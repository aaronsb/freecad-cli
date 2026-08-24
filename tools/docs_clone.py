#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The FreeCAD wiki, as the markdown conversion the project publishes.

FreeCAD/FreeCAD-documentation is ~560 MB with images. Only wiki/*.md is
wanted here, so the clone is blob-filtered and sparse: ~30 MB, 2600 pages.
It lives in the tool's cache, never in the repository, and is refreshed on
request rather than on every run.

    python3 tools/docs_clone.py            # ensure, print path and commit
    python3 tools/docs_clone.py --refresh  # fetch the latest
"""

import argparse
import os
import subprocess
import sys

URL = "https://github.com/FreeCAD/FreeCAD-documentation.git"


def cache_dir():
    root = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache")
    return os.path.join(root, "fccli", "FreeCAD-documentation")


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, check=True, timeout=600).stdout.strip()


def ensure(refresh=False, quiet=False):
    """The clone's path, cloning or refreshing as asked. None if git failed."""
    path = cache_dir()
    try:
        # The wiki directory is what a clone is for. A .git with no wiki
        # is an interrupted clone, and it is removed and done again.
        if os.path.isdir(path) and not os.path.isdir(os.path.join(path, "wiki")):
            import shutil
            shutil.rmtree(path, ignore_errors=True)
        if not os.path.isdir(os.path.join(path, "wiki")):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            _git("clone", "-q", "--filter=blob:none", "--no-checkout",
                 "--depth", "1", URL, path)
            _git("sparse-checkout", "set", "--no-cone", "/wiki/*.md", cwd=path)
            _git("checkout", "-q", "main", cwd=path)
        elif refresh:
            _git("fetch", "-q", "--depth", "1", "origin", "main", cwd=path)
            _git("reset", "-q", "--hard", "origin/main", cwd=path)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            OSError) as exc:
        if not quiet:
            print(f"docs_clone: {exc}", file=sys.stderr)
        return None
    return path


def revision(path):
    return _git("rev-parse", "--short", "HEAD", cwd=path)


def pages(path):
    """Page name -> file path, for every wiki/*.md in the clone."""
    wiki = os.path.join(path, "wiki")
    return {f[:-3]: os.path.join(wiki, f)
            for f in os.listdir(wiki) if f.endswith(".md")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    path = ensure(refresh=args.refresh)
    if path is None:
        return 1
    print(f"{path}  @ {revision(path)}  ({len(pages(path))} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
