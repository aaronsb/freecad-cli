#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Read, check and write the version across the files that carry it.

fccli/__init__.py is authoritative. package.xml holds a copy because the
Addon Manager reads it from there, and a copy that drifts is worse than no
copy, so `check` is wired into the release target.

    python3 tools/version.py              print the version
    python3 tools/version.py check        fail if the copies disagree
    python3 tools/version.py bump minor   write the next version everywhere
    python3 tools/version.py set 1.2.3
    python3 tools/version.py stamp        freeze the commit into fccli/_build.py
"""

import datetime
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INIT = os.path.join(ROOT, "fccli", "__init__.py")
PACKAGE = os.path.join(ROOT, "package.xml")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

INIT_RE = re.compile(r'^__version__ = "([^"]+)"', re.M)
PKG_RE = re.compile(r"<version>([^<]+)</version>")
PKG_DATE_RE = re.compile(r"<date>([^<]+)</date>")


def read():
    with open(INIT, encoding="utf-8") as fh:
        match = INIT_RE.search(fh.read())
    if not match:
        raise SystemExit("no __version__ in fccli/__init__.py")
    return match.group(1)


def read_package():
    with open(PACKAGE, encoding="utf-8") as fh:
        match = PKG_RE.search(fh.read())
    return match.group(1) if match else None


def check():
    ours, theirs = read(), read_package()
    if ours != theirs:
        print(f"version mismatch: fccli/__init__.py={ours} "
              f"package.xml={theirs}", file=sys.stderr)
        return 1
    print(f"{ours} (consistent)")
    return 0


def next_version(current, part):
    major, minor, patch = (int(p) for p in current.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit("bump takes major, minor or patch")


def write(version):
    today = datetime.date.today().isoformat()

    with open(INIT, encoding="utf-8") as fh:
        text = fh.read()
    with open(INIT, "w", encoding="utf-8") as fh:
        fh.write(INIT_RE.sub(f'__version__ = "{version}"', text))

    with open(PACKAGE, encoding="utf-8") as fh:
        text = fh.read()
    text = PKG_RE.sub(f"<version>{version}</version>", text)
    text = PKG_DATE_RE.sub(f"<date>{today}</date>", text)
    with open(PACKAGE, "w", encoding="utf-8") as fh:
        fh.write(text)

    if os.path.exists(CHANGELOG):
        with open(CHANGELOG, encoding="utf-8") as fh:
            text = fh.read()
        if f"## {version}" not in text:
            # Notes written during the cycle live under "## Unreleased".
            # Retitling that is what a release is; inserting a fresh
            # section above it would strand them under the new heading.
            if "## Unreleased\n" in text:
                text = text.replace("## Unreleased\n",
                                    f"## {version} -- {today}\n", 1)
            else:
                entry = f"## {version} -- {today}\n\n- \n\n"
                text = text.replace("<!-- next -->\n",
                                    "<!-- next -->\n\n" + entry, 1)
            with open(CHANGELOG, "w", encoding="utf-8") as fh:
                fh.write(text)
    print(version)


def stamp():
    """Freeze the commit into the package, for builds shipped without git."""
    import subprocess
    def git(*args):
        return subprocess.run(("git", "-C", ROOT) + args, capture_output=True,
                              text=True).stdout.strip()
    commit = git("rev-parse", "--short", "HEAD")
    built = git("log", "-1", "--format=%cs")
    path = os.path.join(ROOT, "fccli", "_build.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('"""Generated at release time. Not tracked."""\n\n')
        fh.write(f'COMMIT = "{commit}"\nBUILT = "{built}"\n')
    print(f"{read()}+{commit}")


def main():
    args = sys.argv[1:]
    if not args:
        print(read())
        return 0
    if args[0] == "check":
        return check()
    if args[0] == "stamp":
        stamp()
        return 0
    if args[0] == "bump":
        write(next_version(read(), args[1] if len(args) > 1 else "patch"))
        return 0
    if args[0] == "set":
        write(args[1])
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
