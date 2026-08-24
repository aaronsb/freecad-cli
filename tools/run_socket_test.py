#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""End-to-end test of the socket, from outside FreeCAD.

Launches a real FreeCAD under its own virtual display, waits for the socket
to appear, then drives it with the same client a person would use. Nothing
here imports FreeCAD -- if the client can do it, so can a terminal.
"""

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(ROOT, "bin", "fccli")
BOOT_TIMEOUT = int(os.environ.get("FCCLI_BOOT_TIMEOUT", "90"))
CHECKS = []


def check(label, got, want):
    ok = got == want
    CHECKS.append(ok)
    print(f"  {'ok  ' if ok else 'FAIL'} {label}"
          + ("" if ok else f"\n         got  {got!r}\n         want {want!r}"))
    return ok


def truthy(label, got):
    return check(label, bool(got), True)


def socket_dir():
    root = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return os.path.join(root, "fccli")


def fccli(*args, **kw):
    kw.setdefault("stdin", subprocess.DEVNULL)
    kw.setdefault("timeout", 60)
    if "input" in kw:
        kw.pop("stdin")
    proc = subprocess.run([sys.executable, CLIENT, *args],
                          capture_output=True, text=True, **kw)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


class _Handle:
    """Just enough of a Popen to ask whether the process is still alive.

    fccli start detaches the process, so there is no child to wait on.
    """

    def __init__(self, pid):
        self.pid = pid

    def poll(self):
        try:
            os.kill(self.pid, 0)
        except OSError:
            return 0
        return None

    def kill(self):
        try:
            os.kill(self.pid, 9)
        except OSError:
            pass


def wait_for_socket(before, deadline):
    while time.monotonic() < deadline:
        now = set(os.listdir(socket_dir())) if os.path.isdir(socket_dir()) else set()
        fresh = now - before
        if fresh:
            time.sleep(0.5)
            return sorted(fresh)[0]
        time.sleep(0.5)
    return None


def main():
    # A scratch state directory, inherited by the FreeCAD this launches, so
    # the suite does not append its commands to the operator's history --
    # which now feeds completion ranking.
    #
    # XDG_STATE_HOME only. XDG_DATA_HOME is where FreeCAD looks for its own
    # Mod directory, so repointing it hides the installed addon. And
    # XDG_RUNTIME_DIR is left alone: the socket belongs where it belongs.
    scratch = tempfile.mkdtemp(prefix="fccli-socket-")
    atexit.register(shutil.rmtree, scratch, True)   # one per run, else kept
    os.environ["XDG_STATE_HOME"] = os.path.join(scratch, "state")

    os.makedirs(socket_dir(), mode=0o700, exist_ok=True)

    # The suite assumes one reachable instance, so it will not run alongside
    # a FreeCAD someone is using -- that would be its session under test.
    code, out, _ = fccli("ls")
    if code == 0:
        print("socket: a FreeCAD is already running, and the suite would be "
              "testing the session someone is using. Clear it with:\n"
              "    bin/fccli cancel && bin/fccli exec 'quit!'\n"
              "(cancel first: a session part-way through a command reads "
              "quit! as input for the step it is waiting on)\n"
              "An aborted run leaves one behind, so this is often its own "
              "leftover rather than yours.", file=sys.stderr)
        print(out, file=sys.stderr)
        return 2

    print("launching FreeCAD through `fccli start`...")
    code, out, err = fccli("start", "--headless",
                           "--timeout", str(BOOT_TIMEOUT),
                           "--log", "/tmp/fccli-socket-test.log")
    check("start exits clean", code, 0)
    truthy("it reports the pid it started", "started FreeCAD, pid" in out)
    truthy("  and that no --pid is needed", "no --pid" in out)
    if code != 0:
        print(err, file=sys.stderr)
        return 2

    # Ask again in JSON rather than scraping the friendly output.
    code, out, _ = fccli("--json", "ls")
    rows = json.loads(out)
    check("exactly one instance is reachable", len(rows), 1)
    pid = str(rows[0]["pid"])
    proc = _Handle(rows[0]["pid"])
    print()

    try:
        print("0. bare invocation orients the caller")
        code, out, err = fccli()
        check("it exits clean", code, 0)
        truthy("it shows usage", "usage: fccli" in (out + err))
        truthy("it names the single instance",
               "One instance running" in out and pid in out)
        truthy("  and says no --pid is needed", "no --pid" in out)

        print("\n1. the client finds the instance")
        code, out, _ = fccli("ls")
        check("ls exits clean", code, 0)
        truthy("it lists the running pid", pid in out)

        code, out, _ = fccli("state")
        check("state exits clean", code, 0)
        truthy("the engine is idle", "engine    idle" in out)
        truthy("the floor is free", "floor     free" in out)

        print("\n2. commands run through the socket")
        check("new", fccli("exec", "new sockdoc")[0], 0)
        code, out, err = fccli("exec", "box 0,0,0 40 30 20")
        check("a command exits clean", code, 0)
        truthy("its result comes back", "box 0,0,0" in out)

        print("\n3. errors are faults, and say so")
        code, out, err = fccli("exec", "box 0,0,0 40 zz 20")
        check("a rejected command exits 1", code, 1)
        truthy("the reason is on stderr", "not a number" in err)
        truthy("nothing went to stdout", out == "")

        print("\n4. an incomplete command does not hang")
        code, out, err = fccli("exec", "cylinder 12")
        check("it exits 1 rather than waiting", code, 1)
        truthy("it says what is missing", "still wants" in err)
        fccli("exec", "")            # let the engine settle
        subprocess.run([sys.executable, CLIENT, "exec", "--", ""],
                       capture_output=True)

        print("\n4b. a command FreeCAD refuses does not hang either")
        # PartDesign_Revolution wants an active body and says so in a modal.
        # Nobody is sitting in front of a socket, so the dialog waited for a
        # click that never came and the caller waited with it -- while the
        # same instance went on answering everything else, so it did not
        # even look wedged. 25s, not the usual 60: a regression here should
        # report, not stall the suite.
        try:
            code, out, err = fccli("exec", "revolve", timeout=25)
        except subprocess.TimeoutExpired:
            check("a refused command answers instead of hanging",
                  "hung", "answered")
            code, out, err = 1, "", ""
        else:
            check("a refused command exits 1", code, 1)
            truthy("FreeCAD's own words come back",
                   "body" in err.lower() or "select" in err.lower())
            truthy("  and it says the answer was cancelled",
                   "cancelled" in err.lower())
        code, out, _ = fccli("state")
        truthy("the instance is still idle afterwards", "engine    idle" in out)

        print("\n4c. a session part-way through a command can be cleared")
        # Every line goes to the step being collected, so `exec quit!` was
        # answered with "still wants The radius" and an instance mid-command
        # could not be shut down from outside at all. The server has always
        # had a cancel op; nothing offered it.
        code, out, err = fccli("exec", "cylinder")
        check("an incomplete command leaves the engine collecting", code, 1)
        code, out, _ = fccli("state")
        truthy("  and state says so", "engine    collecting" in out)
        code, out, _ = fccli("exec", "quit!")
        code, out, _ = fccli("state")
        truthy("quit! is read as input for the open step, not as a command",
               "engine    collecting" in out)
        code, out, _ = fccli("cancel")
        check("cancel exits clean", code, 0)
        truthy("  and says what it did", "cancelled" in out)
        code, out, _ = fccli("state")
        truthy("the engine is idle again", "engine    idle" in out)

        print("\n5. check never mutates")
        fccli("exec", "cancel") if False else None
        code, out, _ = fccli("check", "cylinder", "12", "40")
        check("check exits clean", code, 0)
        truthy("it reports what would be created", "Part::Cylinder" in out)

        print("\n6. stdin is a script")
        code, out, _ = fccli("exec", input="circle 0,0,0 20\ncircle 0,0,0 30\n")
        check("both lines ran", code, 0)
        truthy("both results returned", out.count("circle") >= 2)

        print("\n7. history is the session's, not a widget's")
        code, out, _ = fccli("history", "-n", "20")
        check("history exits clean", code, 0)
        truthy("it holds what the socket ran", "box 0,0,0" in out)
        truthy("assembled, not fragments", "circle 0,0,0" in out)
        # The file stores "<epoch>\tcommand"; the epoch is the file's
        # business and must not reach anybody reading their history.
        truthy("no stored timestamp leaks into what is printed",
               not any(ln.strip()[:10].isdigit() and "\t" in ln
                       for ln in out.splitlines()))
        truthy("  and the commands are intact",
               all("\t" not in ln for ln in out.splitlines()))

        print("\n8. two clients, one session")
        code, out, _ = fccli("--json", "state")
        state = json.loads(out)
        truthy("the server counts its clients", state.get("clients", 0) >= 1)
        a = subprocess.Popen([sys.executable, CLIENT, "history", "-f"],
                             stdout=subprocess.PIPE, text=True)
        time.sleep(1.5)
        fccli("exec", "sphere 9")
        time.sleep(1.5)
        a.terminate()
        watched = a.stdout.read() if a.stdout else ""
        truthy("a watching client saw another client's command",
               "sphere" in watched)

        print("\n8b. the line being typed is shared")
        code, out, _ = fccli("--json", "state")
        before = json.loads(out)
        truthy("the session reports a floor", "floor" in before)
        watcher = subprocess.Popen([sys.executable, CLIENT, "watch"],
                                   stdout=subprocess.PIPE, text=True,
                                   stdin=subprocess.DEVNULL)
        time.sleep(2.0)
        fccli("exec", "cylinder 7 21")
        time.sleep(2.0)
        watcher.terminate()
        seen = watcher.stdout.read() if watcher.stdout else ""
        truthy("a watching pane sees what another client ran",
               "cylinder" in seen)

        print("\n9. instances identify themselves by what they have open")
        fccli("exec", "save " + os.path.join(tempfile.gettempdir(),
                                             "fccli-sock.FCStd"))
        code, out, _ = fccli("--json", "docs")
        docs = json.loads(out)
        truthy("docs lists something", docs)
        first = docs[0]
        truthy("  with a file path",
               (first.get("file") or "").endswith(".FCStd"))
        truthy("  an object count", isinstance(first.get("objects"), int))
        truthy("  and which one is active",
               any(d.get("active") for d in docs))
        code, out, _ = fccli("ls")
        truthy("ls shows the file too", ".FCStd" in out)
        code, out, _ = fccli("--json", "ls")
        rows = json.loads(out)
        check("ls reports one reachable instance",
              [r["reachable"] for r in rows], [True])

        code, out, _ = fccli("--json", "exec", "man box")
        check("a read-only verb works over the socket", code, 0)

    finally:
        print("\n10. shutdown through the socket, no dialogs")
        code, out, err = fccli("exec", "quit!")
        check("quit! exits clean", code, 0)
        for _ in range(30):
            if proc.poll() is not None:
                break
            time.sleep(0.5)
        check("FreeCAD exited", proc.poll() is not None, True)
        if proc.poll() is None:
            proc.kill()
        leftover = os.path.join(socket_dir(), f"{pid}.sock")
        check("the socket was cleaned up", os.path.exists(leftover), False)

    passed = sum(1 for c in CHECKS if c)
    print(f"\nsocket: {passed} passed, {len(CHECKS) - passed} failed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
