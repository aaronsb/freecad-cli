#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Run the GUI build verification test and turn its result into an exit code.

A FreeCAD macro cannot set the process exit code, so the test writes JSON and
this reads it. A missing file means FreeCAD died before finishing, which is
reported as a failure rather than mistaken for success.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT = os.path.join(tempfile.gettempdir(), "fccli-bvt.json")
TIMEOUT = int(os.environ.get("FCCLI_BVT_TIMEOUT", "300"))


def main():
    if os.path.exists(RESULT):
        os.remove(RESULT)
    runner = []
    if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        runner = ["xvfb-run", "-a", "-s", "-screen 0 1600x1000x24"]
    cmd = runner + ["freecad", os.path.join(ROOT, "tests", "bvt.py")]
    # A scratch state directory, so a run does not append its commands to
    # the operator's history -- which now feeds completion ranking.
    #
    # XDG_STATE_HOME only. XDG_DATA_HOME is where FreeCAD looks for its own
    # Mod directory, so repointing it hides the installed addon and the
    # test dies with "No module named 'fccli'" before it reaches a check.
    scratch = tempfile.mkdtemp(prefix="fccli-bvt-")
    env = dict(os.environ, FCCLI_BVT_RESULT=RESULT,
               XDG_STATE_HOME=os.path.join(scratch, "state"))
    try:
        proc = subprocess.run(cmd, env=env, timeout=TIMEOUT,
                              capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print(f"bvt: FreeCAD did not finish within {TIMEOUT}s", file=sys.stderr)
        return 2

    if not os.path.exists(RESULT):
        print("bvt: no result file -- FreeCAD exited before finishing",
              file=sys.stderr)
        print(proc.stdout[-2000:], file=sys.stderr)
        print(proc.stderr[-2000:], file=sys.stderr)
        return 2

    with open(RESULT, encoding="utf-8") as fh:
        data = json.load(fh)
    for line in proc.stdout.splitlines():
        if line.startswith(("  ok  ", "  FAIL", "\n")) or line[:2].isdigit() \
                or line.strip().endswith("failed"):
            print(line)
    if data.get("exception"):
        print(data["exception"], file=sys.stderr)
    for c in data["checks"]:
        if not c["ok"]:
            print(f"  FAIL {c['label']}   got {c['got']} want {c['want']}",
                  file=sys.stderr)
    print(f"\nbvt: {data['passed']} passed, {data['failed']} failed "
          f"in {data['seconds']}s")
    return 1 if data["failed"] or data.get("exception") else 0


if __name__ == "__main__":
    sys.exit(main())
