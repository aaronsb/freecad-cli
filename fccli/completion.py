"""What completes here, computed once.

The widget used to work this out for itself, which meant a terminal client
would have needed its own copy that drifted. It lives here so the dock and
the socket give the same answer, from the same live engine state.
"""

from .grammar import QUANTITY, SELECTION


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


def candidates(engine, text):
    """Return (head, tail, candidates) for the text before the cursor."""
    head, _, tail = text.rpartition(" ")
    step = step_for(engine, head)

    if step is not None and step.kind == QUANTITY and is_bare_number(tail):
        # "cylinder 5" + Tab -> "cylinder 5mm", in whatever the schema says.
        from .units import preferred
        unit = preferred("angle" if step.unit == "deg" else "length")
        return head, tail, [tail + unit]

    if step is None and not head:
        pool = engine.registry.names()
    elif step is not None:
        pool = list(step.option_names())
        if step.kind == SELECTION:
            pool += document_labels()
        if step.choices:
            pool += list(step.choices)
        pool += engine.registry.names()
    else:
        pool = engine.registry.names()

    lowered = tail.lower()
    return head, tail, [c for c in pool if c.lower().startswith(lowered)]


def document_labels():
    try:
        import FreeCAD as App
        doc = App.ActiveDocument
        return [o.Label for o in doc.Objects] if doc else []
    except Exception:
        return []
