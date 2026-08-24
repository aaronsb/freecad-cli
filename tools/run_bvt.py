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

# xvfb-run sets DISPLAY, and that used to be the whole story. Qt6 on a
# Wayland session never reads it -- the platform plugin comes from
# XDG_SESSION_TYPE and WAYLAND_DISPLAY, and the wayland plugin talks to the
# operator's compositor. The suite ran on their desktop anyway, dialogs and
# all, which is the thing the comment below says it fixed.
HEADLESS_ENV = {"QT_QPA_PLATFORM": "xcb"}


def main():
    if os.path.exists(RESULT):
        os.remove(RESULT)
    # Always its own display when one can be had. This used to fall back to
    # DISPLAY whenever it was set, which meant running the suite on a
    # desktop opened FreeCAD windows on that desktop and popped its dialogs
    # at whoever was sitting there. A build verification test should be
    # invisible. FCCLI_BVT_DISPLAY=1 asks for the real one, for watching it
    # run on purpose.
    runner, headless = [], {}
    if os.environ.get("FCCLI_BVT_DISPLAY"):
        if not os.environ.get("DISPLAY"):
            print("bvt: FCCLI_BVT_DISPLAY is set but DISPLAY is not",
                  file=sys.stderr)
            return 2
        # Watching it run means seeing it. An exported QT_QPA_PLATFORM of
        # offscreen is inherited, and there would be nothing to watch.
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            headless = {"QT_QPA_PLATFORM": ""}
    elif shutil.which("xvfb-run"):
        runner = ["xvfb-run", "-a", "-s", "-screen 0 1600x1000x24"]
        headless = HEADLESS_ENV
    elif not os.environ.get("DISPLAY"):
        print("bvt: needs xvfb-run, or a DISPLAY with FCCLI_BVT_DISPLAY=1",
              file=sys.stderr)
        return 2
    cmd = runner + ["freecad", os.path.join(ROOT, "tests", "bvt.py")]
    # A scratch state directory, so a run does not append its commands to
    # the operator's history -- which now feeds completion ranking.
    #
    # XDG_STATE_HOME only. XDG_DATA_HOME is where FreeCAD looks for its own
    # Mod directory, so repointing it hides the installed addon and the
    # test dies with "No module named 'fccli'" before it reaches a check.
    scratch = tempfile.mkdtemp(prefix="fccli-bvt-")
    env = dict(os.environ, FCCLI_BVT_RESULT=RESULT,
               XDG_STATE_HOME=os.path.join(scratch, "state"), **headless)
    try:
        proc = subprocess.run(cmd, env=env, timeout=TIMEOUT,
                              capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print(f"bvt: FreeCAD did not finish within {TIMEOUT}s", file=sys.stderr)
        return 2
    finally:
        # One of these per run, otherwise kept forever.
        shutil.rmtree(scratch, ignore_errors=True)

    if not os.path.exists(RESULT):
        print("bvt: no result file -- FreeCAD exited before finishing",
              file=sys.stderr)
        if "xcb" in (proc.stderr or "") and "plugin" in (proc.stderr or ""):
            print("bvt: the xcb platform plugin is missing. Several distros "
                  "ship it apart from qt6-wayland -- install it (Debian: "
                  "libqt6gui6 / qt6-qpa-plugins, Arch: qt6-base, Fedora: "
                  "qt6-qtbase-gui).", file=sys.stderr)
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
