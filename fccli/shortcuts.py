# SPDX-License-Identifier: LGPL-2.1-or-later

"""FreeCAD's own key chords, offered as aliases.

FreeCAD ships 940 shortcuts and 250 of them use unmodified keys. The Draft
and Arch two-letter chords -- A,X for an axis, C,I for a circle, B,U for a
building -- are already a command language. A bad one: nothing lists them,
nothing completes them, and none of them takes an argument. But they are in
somebody's fingers.

Dropping the comma turns each into an alias, so `ax` and Enter does what
A,X did. Muscle memory survives the move to typing, and the same keys now
lead somewhere that can be completed and can take arguments.

The issue proposed parsing Shortcuts.cfg. That turned out to be
unnecessary: harvest_commands.py already reads the shortcut off each
QAction, so the descriptor has them -- and a running GUI has the live ones,
which is better still, because it reflects whatever the operator has
remapped rather than what FreeCAD shipped.

Three rules, in the order they are applied. A chord never shadows a verb
somebody wrote. The operator's own aliases always win. And where two
commands claim one chord, the one FreeCAD promotes takes it.
"""

from . import curation as _curation

MODIFIERS = ("ctrl", "alt", "shift", "meta")

# Keys with names rather than characters. "Esc" reads as a word and would
# become one -- typing e-s-c would fire a command -- so a shortcut using
# any of them is left as a keystroke.
NAMED_KEYS = {
    "esc", "escape", "del", "delete", "space", "tab", "backspace",
    "return", "enter", "home", "end", "ins", "insert",
    "pgup", "pgdown", "pageup", "pagedown",
    "up", "down", "left", "right",
} | {f"f{n}" for n in range(1, 25)}


def chord_to_alias(shortcut):
    """"A, X" -> "ax". Returns None for anything needing a modifier.

    A modified shortcut is not competing with typing -- Ctrl+S is still
    Ctrl+S while the command line has focus -- so only the bare ones are
    worth turning into words.
    """
    if not shortcut:
        return None
    text = shortcut.strip()
    if not text or any(m in text.lower() for m in MODIFIERS):
        return None
    parts = [p.strip().lower() for p in text.split(",") if p.strip()]
    if not parts or any(p in NAMED_KEYS for p in parts):
        return None
    slug = "".join(ch for ch in "".join(parts) if ch.isalnum())
    # A single character is a keystroke, not a word: `c` as an alias would
    # collide with completion on every command starting with c.
    return slug if len(slug) >= 2 else None


def live_shortcuts():
    """What the QActions say right now, so remapping is respected."""
    try:
        import FreeCADGui as Gui
        from .qt import QtGui
        mw = Gui.getMainWindow()
        if mw is None:
            return {}
        out = {}
        for act in mw.findChildren(QtGui.QAction):
            name = act.objectName()
            if not name:
                continue
            try:
                text = act.shortcut().toString()
            except Exception:
                continue
            if text:
                out[name] = text
        return out
    except Exception:
        return {}


def harvested_shortcuts(descriptor):
    return {name: meta.get("shortcut")
            for name, meta in (descriptor or {}).get("commands", {}).items()
            if meta.get("shortcut")}


def proposals(registry, descriptor=None, user_aliases=None):
    """What could be imported, and what each one would collide with.

    Returns (accepted, rejected). ``accepted`` maps alias -> verb name;
    ``rejected`` maps alias -> the reason, so `shortcuts` can say why a
    chord somebody expects is not there.
    """
    user_aliases = user_aliases or {}
    source = live_shortcuts() or harvested_shortcuts(descriptor)
    curated = _curation.current()

    # Group by alias first: a chord claimed twice has to be arbitrated
    # rather than silently going to whichever was seen last.
    claims = {}
    for command, shortcut in source.items():
        alias = chord_to_alias(shortcut)
        if alias:
            claims.setdefault(alias, []).append(command)

    accepted, rejected = {}, {}
    for alias in sorted(claims):
        commands = claims[alias]
        if registry.get(alias) is not None:
            rejected[alias] = f"{alias} is already a command"
            continue
        if alias in user_aliases:
            rejected[alias] = f"you alias {alias} to {user_aliases[alias]}"
            continue
        # FreeCAD's own ranking breaks the tie; the name settles a draw so
        # the answer does not depend on dictionary order.
        commands = sorted(commands, key=lambda c: (curated.rank(c), c))
        verb = None
        for command in commands:
            verb = registry.by_gui_command(command)
            if verb is not None:
                break
        if verb is None:
            rejected[alias] = f"no verb runs {commands[0]}"
            continue
        if alias in verb.aliases:
            rejected[alias] = f"{verb.name} already answers to {alias}"
            continue
        accepted[alias] = verb.name
    return accepted, rejected
