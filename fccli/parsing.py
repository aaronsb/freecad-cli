"""Token parsing and per-character validation.

Both the engine and the syntax highlighter call in here. The highlighter
needs spans rather than a yes/no, so every parse reports which slice of the
input failed.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import FreeCAD as App
from FreeCAD import Units

Vector = App.Vector

REL_PREFIXES = ("@", "r")  # AutoCAD's @, Rhino's r
POLAR = "<"


@dataclass
class Span:
    start: int
    end: int
    role: str          # "number" | "unit" | "prefix" | "bad" | "sep"
    ok: bool = True


@dataclass
class ParseResult:
    ok: bool = False
    value: object = None
    relative: bool = False
    spans: List[Span] = field(default_factory=list)
    error: str = ""


def parse_quantity(text: str, unit_hint: str = "mm") -> ParseResult:
    """Parse one scalar. FreeCAD's own parser handles 3/8in, 2.5cm, 45deg."""
    t = text.strip()
    if not t:
        return ParseResult(ok=False, error="empty")
    try:
        q = Units.Quantity(t)
    except (ValueError, TypeError):
        # FreeCAD says "syntax error" and nothing about where.
        return ParseResult(
            ok=False,
            spans=[Span(0, len(text), "bad", False)],
            error=f"{t!r} is not a number or quantity",
        )
    return ParseResult(ok=True, value=q.Value, spans=[Span(0, len(text), "number")])


def _split_components(text: str) -> List[Tuple[int, str]]:
    """Split on commas, keeping each component's offset for span reporting."""
    out, start, depth = [], 0, 0
    for i, ch in enumerate(text):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append((start, text[start:i]))
            start = i + 1
    out.append((start, text[start:]))
    return out


def parse_point(text: str, last: Optional[Vector] = None) -> ParseResult:
    """Parse a typed point.

    Accepted forms::

        10,20,30      absolute
        10,20         z falls back to the last point's z, else 0
        @10,0,0       relative to the last point
        r10,0,0       relative, Rhino spelling
        100<45        polar: distance at angle, in the XY plane
    """
    raw = text.strip()
    if not raw:
        return ParseResult(ok=False, error="empty")

    spans: List[Span] = []
    offset = 0
    relative = False
    body = raw

    for pfx in REL_PREFIXES:
        if body.lower().startswith(pfx) and len(body) > len(pfx):
            # A bare leading "r" is only a prefix when a digit or sign follows,
            # otherwise "rect" would parse as relative point "ect".
            if pfx == "r" and not (body[1].isdigit() or body[1] in "+-."):
                continue
            relative = True
            spans.append(Span(0, len(pfx), "prefix"))
            offset = len(pfx)
            body = body[len(pfx):]
            break

    if relative and last is None:
        return ParseResult(ok=False, spans=[Span(0, len(raw), "bad", False)],
                           error="no previous point to be relative to")

    if POLAR in body:
        dist_s, _, ang_s = body.partition(POLAR)
        d = parse_quantity(dist_s)
        a = parse_quantity(ang_s)
        for res, base in ((d, offset), (a, offset + len(dist_s) + 1)):
            for s in res.spans:
                spans.append(Span(base + s.start, base + s.end, s.role, s.ok))
        spans.append(Span(offset + len(dist_s), offset + len(dist_s) + 1, "sep"))
        if not (d.ok and a.ok):
            return ParseResult(ok=False, spans=spans, error="bad polar coordinate")
        import math
        rad = math.radians(a.value)
        vec = Vector(d.value * math.cos(rad), d.value * math.sin(rad), 0.0)
        if relative:
            vec = last.add(vec)
        return ParseResult(ok=True, value=vec, relative=relative, spans=spans)

    comps = _split_components(body)
    if not 2 <= len(comps) <= 3:
        return ParseResult(ok=False, spans=[Span(0, len(raw), "bad", False)],
                           error="expected 2 or 3 comma-separated components")

    vals, all_ok = [], True
    for start, comp in comps:
        res = parse_quantity(comp)
        base = offset + start
        for s in res.spans:
            spans.append(Span(base + s.start, base + s.end, s.role, s.ok))
        if res.ok:
            vals.append(res.value)
        else:
            all_ok = False
            vals.append(0.0)

    if not all_ok:
        bad = [comp.strip() for _, comp in comps
               if not parse_quantity(comp).ok]
        return ParseResult(
            ok=False, spans=spans, relative=relative,
            error="bad coordinate: " + ", ".join(repr(b) for b in bad))

    if len(vals) == 2:
        vals.append(last.z if (last is not None and not relative) else 0.0)

    vec = Vector(*vals)
    if relative:
        vec = last.add(vec)
    return ParseResult(ok=True, value=vec, relative=relative, spans=spans)


def format_point(v: Vector) -> str:
    """Serialize a point back to typed form, for history replay."""
    def n(x: float) -> str:
        s = f"{x:.6g}"
        return "0" if s in ("-0", "-0.0") else s
    return f"{n(v.x)},{n(v.y)},{n(v.z)}"


def format_quantity(value: float, unit: str = "mm") -> str:
    """Serialize a scalar back to typed form, in the configured schema.

    No space before the unit: the replay line is split on whitespace, so
    "10 mm" would arrive as two tokens. FreeCAD's parser accepts "10mm".
    """
    from .units import format_quantity as _format
    return _format(value, unit)
