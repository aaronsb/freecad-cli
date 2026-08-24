# SPDX-License-Identifier: LGPL-2.1-or-later

"""Ranking by what somebody actually does.

Curation answers what FreeCAD promotes. It is the same answer for everyone,
and it stops being the interesting one the moment a person has a habit:
somebody who draws walls all day should not be offered `box` ahead of
`wall` because Part's toolbar is bigger than BIM's.

The weights are Mozilla's frecency buckets, by way of aaronsb/clicue, which
applies this to zsh: a count multiplied by how recently it last happened,
in integer arithmetic, on buckets rather than a curve. A thing done twice
today beats a thing done six times last spring.

Two departures from clicue, both because of what sits underneath here:

`now` is a parameter, never a clock read inside. Tests pin it, so an
ordering is reproducible rather than drifting with the calendar.

Names with no history keep the order they arrived in instead of falling
back to alphabetical. They arrive in curation order, so the full ordering
reads: what you use, then what FreeCAD promotes, then the rest. Alphabetical
would throw the second of those away.
"""

# Age in whole days -> multiplier. Mozilla's shape.
BUCKETS = ((0, 16), (7, 8), (30, 4), (180, 2))
FLOOR = 1

DAY = 86400


def recency_weight(now, last):
    """How much a last-used time is worth.

    A missing timestamp weighs 1, which degrades the entry to plain
    frequency rather than dropping it. History written before timestamps
    existed still counts.
    """
    if not last or not now:
        return FLOOR
    # A stamp ahead of now is the most recent thing in the ring, not the
    # stalest. A clock that ran fast -- a resumed VM, a bad RTC -- and was
    # then corrected backwards used to bury everything typed in between at
    # weight 1, permanently, since stamps are written once.
    days = max(0, (now - last) // DAY)
    for edge, weight in BUCKETS:
        if days <= edge:
            return weight
    return FLOOR


def score(count, last, now):
    """Frequency, weighted by recency. Zero means never seen."""
    if not count:
        return 0
    return count * recency_weight(now, last)


def partition(names, stats, now):
    """Used names first by score, then everything else as it came in.

    A partition rather than a sort: an unused name is not competing with a
    used one on a score of zero, it is simply behind them, in whatever
    order the caller already put it. Nothing is dropped.
    """
    scored, rest = [], []
    for name in names:
        count, last = stats(name)
        value = score(count, last, now)
        if value > 0:
            scored.append((value, name))
        else:
            rest.append(name)
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [name for _, name in scored] + rest


def tally(entries, key=None):
    """Count and last-seen epoch per verb, from history entries.

    ``entries`` is a sequence of (line, when). The verb is the first token,
    since that is what completion ranks; the rest of the line is the
    argument, and having typed `box 10` twice says something about `box`.
    """
    key = key or (lambda line: line.split(" ")[0].rstrip("!").lower())
    counts, last = {}, {}
    for line, when in entries:
        name = key(line)
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1
        if when and when > last.get(name, 0):
            last[name] = when
    return {name: (counts[name], last.get(name, 0)) for name in counts}
