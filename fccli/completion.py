# SPDX-License-Identifier: LGPL-2.1-or-later

"""What completes here, computed once.

The widget used to work this out for itself, which meant a terminal client
would have needed its own copy that drifted. It lives here so the dock and
the socket give the same answer, from the same live engine state.
"""

from .grammar import CHOICE, PATH, POINT, QUANTITY, SELECTION, TEXT


def step_for(engine, head):
    """Which getter the token being typed belongs to.

    A whole command typed on one line never reaches the engine until Enter,
    so there is no open step to consult. Resolve the verb from the first
    token and count the arguments already given.
    """
    live = engine.current_step()
    if live is not None:
        return live
    tokens = head.split()
    if not tokens:
        return None
    hits = engine.registry.resolve_prefix(tokens[0].rstrip("!"))
    if len(hits) != 1:
        return None
    verb = engine.registry.get(hits[0])
    index = len(tokens) - 1
    if verb is None or index >= len(verb.steps):
        return None
    return verb.steps[index]


def is_bare_number(token):
    if not token:
        return False
    try:
        float(token)
    except ValueError:
        return False
    return True


def candidates(engine, text, history=None, scope=None):
    """Return (head, tail, candidates) for the text before the cursor.

    Candidates replace ``tail``. One may contain a space, which is how a
    remembered command hands back its next argument.
    """
    head, _, tail = text.rpartition(" ")
    step = step_for(engine, head)

    if step is not None and step.kind == QUANTITY and is_bare_number(tail):
        # "cylinder 5" + Tab -> "cylinder 5mm", in whatever the schema says.
        from .units import preferred
        unit = preferred("angle" if step.unit == "deg" else "length")
        return head, tail, [tail + unit]

    # Tab on an empty line. Shells answer this by listing every executable
    # on PATH, which is so noisy they prompt first; here it would be 1250
    # entries starting with 1_front. Recent commands are what someone
    # actually wants at an empty prompt, and there is no convention being
    # broken -- Tab has never meant history anywhere.
    if not head and not tail:
        recent = recent_commands(history)
        if recent:
            return head, tail, recent
        return head, tail, sorted(_starter_verbs(engine))

    # The first token is a verb; everything after a space is an argument.
    # So verb names complete only at the start of a line, or at a step that
    # declares its value is a command -- man, alias, check.
    pool = []
    if not head:
        pool += engine.registry.names()
    if step is not None:
        pool += list(step.option_names())
        if step.choices:
            pool += list(step.choices)
        pool += from_source(engine, step.completes or _default_source(step))

    lowered = tail.lower()
    # A candidate identical to what is already typed adds nothing. Dropping
    # it is what lets a fully typed verb fall through to its arguments.
    hits = [c for c in pool
            if c.lower().startswith(lowered) and c.lower() != lowered]
    if scope and not head:
        narrowed = [c for c in hits if in_scope(engine.registry, c, scope)]
        hits = narrowed or hits

    # The grammar has nothing left to offer, but a command run before may
    # know what came next here. Hand back one argument at a time, so Tab
    # walks the remembered command out rather than dumping the whole line.
    #
    # This is prefix matching over the history ring. No verb is named here
    # and none is special-cased: whatever was run before completes the same
    # way, including verbs generated from FreeCAD's registries and any an
    # addon declared.
    if not hits and history is not None:
        remembered = next_from_history(history, text, tail)
        if remembered:
            hits = [remembered]
    return head, tail, hits


RECENT_LIMIT = 12


def recent_commands(history, limit=RECENT_LIMIT):
    """The last few distinct commands, newest first."""
    if history is None:
        return []
    seen, out = set(), []
    for line in reversed(history.tail(200)):
        recalled = history.recall(line)
        if recalled in seen:
            continue
        seen.add(recalled)
        out.append(recalled)
        if len(out) >= limit:
            break
    return out


def _starter_verbs(engine):
    """With no history, the verbs somebody wrote by hand -- the ones that
    pick points, and the ones that manage a document."""
    names = []
    for name in engine.registry.names():
        verb = engine.registry.get(name)
        module = getattr(verb.emit, "__module__", "")
        if module.endswith((".verbs", ".shell")):
            names.append(name)
    return names or engine.registry.names()[:RECENT_LIMIT]


def domain_of(verb):
    """Which corner of FreeCAD a verb belongs to.

    Read off what the verb already carries -- the command it runs or the
    type it builds -- so nothing has to be tagged by hand.
    """
    command = getattr(verb, "gui_command", None)
    if command and "_" in command:
        return command.split("_")[0]
    creates = getattr(verb, "creates", None)
    if creates and "::" in creates:
        return creates.split("::")[0]
    return None


def domains(registry):
    """Every domain, with how many verbs are in it."""
    counts = {}
    for name in registry.names():
        domain = domain_of(registry.get(name))
        if domain:
            counts[domain] = counts.get(domain, 0) + 1
    return counts


def in_scope(registry, name, scope):
    """Whether a verb survives the current scope.

    Hand-written, patched and family verbs are always in: they are the ones
    someone chose, and hiding them behind a scope would be perverse. The
    scope narrows the thousand launchers.
    """
    if not scope:
        return True
    verb = registry.get(name)
    if verb is None:
        return True
    module = getattr(verb.emit, "__module__", "")
    if module.endswith((".verbs", ".shell")) or "patches" in module:
        return True
    domain = domain_of(verb)
    return domain is None or domain.lower() == scope.lower()


def _default_source(step):
    """What a step completes from when it has not said."""
    return "objects" if step.kind == SELECTION else None


def from_source(engine, source):
    if source == "verbs":
        return engine.registry.names()
    if source == "objects":
        return document_labels()
    if source == "aliases":
        return sorted({a for name in engine.registry.names()
                       for a in engine.registry.get(name).aliases})
    if source == "domains":
        return sorted(domains(engine.registry)) + ["off"]
    if source == "schemas":
        try:
            from .units import schemas
            return [s.lower() for s in schemas()]
        except Exception:
            return []
    return []


def next_from_history(history, text, tail):
    """The next argument of the most recent command that began this way."""
    remembered = history.latest_starting(text)
    if not remembered:
        return None
    suffix = remembered[len(text):]
    if not suffix:
        return None
    if suffix.startswith(" "):
        nxt = suffix[1:].split(" ")[0]
        return f"{tail} {nxt}" if nxt else None
    return tail + suffix.split(" ")[0]


def document_labels():
    try:
        import FreeCAD as App
        doc = App.ActiveDocument
        return [o.Label for o in doc.Objects] if doc else []
    except Exception:
        return []
