#!/usr/bin/env python3
"""Print one version's section from CHANGELOG.md.

The changelog is already the release notes; extracting them keeps the tag,
the GitHub release and the file from telling three versions of the story.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def section(version):
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as fh:
        text = fh.read()
    match = re.search(rf"^## {re.escape(version)}\b.*?$(.*?)(?=^## |\Z)",
                      text, re.M | re.S)
    return match.group(1).strip() if match else ""


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else None
    if version is None:
        sys.path.insert(0, ROOT)
        from fccli import __version__ as version
    body = section(version)
    if not body:
        raise SystemExit(f"no CHANGELOG section for {version}")
    print(body)
