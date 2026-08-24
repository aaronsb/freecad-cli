# SPDX-License-Identifier: LGPL-2.1-or-later

"""What FreeCAD itself promotes, and what it puts side by side.

The command registry is flat. Part_Box and Std_TestQuestion are peers in
it, and 1124 peers is not a surface anyone can learn. FreeCAD's toolbars
and menus are not flat, and they are the project's own answer to the
question this module asks: putting a command in a default toolbar says
people reach for this, and putting two in the same toolbar says they
belong together.

``tools/harvest_commands.py`` already records both, by activating every
workbench and reading the placement back off the QAction. Until now
nothing read it.

Nothing here hides a command. Rank decides what is offered first at an
empty prompt; every verb stays reachable by typing its name, because
finding out a program does something you did not know it did is most of
what a command line is for. Adjacency is how that discovery is offered:
having run one command, the neighbours are what FreeCAD put next to it.
"""

# How prominently FreeCAD presents a command, lowest first.
def authored(verb):
    """Whether a person wrote this verb, rather than the factory generating it.

    Asked of the verb, not of where its emit came from. The module was
    never really answering this and finally stopped: hand-written
    `transform` shares its emit with every generated command verb, so it
    read as generated, lost promoted rank, and `use <domain>` hid it.

    The factory marks what it makes. Everything else -- fccli/verbs.py,
    fccli/shell.py, an addon's own patch -- is somebody's writing.
    """
    return verb is not None and not getattr(verb, "generated", False)


PROMOTED = 0    # in a default toolbar -- a button somebody can click
MENU = 1        # reachable from a menu, but no button
REGISTRY = 2    # neither: internals, test hooks, context-menu-only

RANK_NAMES = {PROMOTED: "promoted", MENU: "menu", REGISTRY: "registry"}


class Curation:
    """Rank and adjacency, read off a descriptor's command table."""

    def __init__(self, commands=None):
        self.commands = commands or {}
        self._families = self._rank_families()
        self._siblings = {}
        for name, meta in self.commands.items():
            for field in ("toolbar", "menu"):
                where = (meta or {}).get(field)
                if where:
                    self._siblings.setdefault((field, where), []).append(name)

    def _rank_families(self):
        """A family ranks as its best member.

        `view` runs no command of its own, so it has no placement to read.
        What it collects does: a family gathering toolbar buttons is as
        findable as the buttons, and offering it below them would bury the
        one name that makes them discoverable.
        """
        from .families import families
        out = {}
        for name, members in families(self.commands).items():
            commands = [m["command"] for m in members.values()]
            out[name] = (min((self.rank(c) for c in commands),
                             default=REGISTRY), commands, members)
        return out

    # ------------------------------------------------------------- rank

    def rank(self, command):
        """How prominently FreeCAD presents one command."""
        meta = self.commands.get(command or "")
        if not meta:
            return REGISTRY
        if meta.get("toolbar"):
            return PROMOTED
        if meta.get("menu"):
            return MENU
        return REGISTRY

    def rank_of(self, verb):
        """A verb's rank.

        A verb someone wrote by hand outranks anything generated: it exists
        because a person decided the command line needed it. Otherwise the
        rank is that of the command it runs.
        """
        if verb is None:
            return REGISTRY
        if authored(verb):
            return PROMOTED
        command = getattr(verb, "gui_command", None)
        if command:
            return self.rank(command)
        if verb.family and verb.family in self._families:
            return self._families[verb.family][0]
        # A tier 1 verb builds a type rather than running a command. It was
        # named and parameterized from a documented type, so it is at least
        # as findable as a menu entry.
        return MENU if getattr(verb, "creates", None) else REGISTRY

    def placement(self, command):
        """Where FreeCAD puts a command, for `man` to cite."""
        meta = self.commands.get(command or "") or {}
        return meta.get("toolbar"), meta.get("menu")

    # -------------------------------------------------------- adjacency

    def adjacent(self, command, limit=8):
        """The commands FreeCAD placed beside this one.

        The toolbar is the tighter grouping, so it answers first; a command
        with no button falls back to its menu.
        """
        meta = self.commands.get(command or "")
        if not meta:
            return []
        for field in ("toolbar", "menu"):
            where = meta.get(field)
            if not where:
                continue
            near = [n for n in self._siblings.get((field, where), [])
                    if n != command]
            if near:
                return sorted(near)[:limit]
        return []

    def _family_neighbours(self, commands, limit):
        """Neighbours of a family, from the one place most of it lives.

        A family is gathered by name, so its members can be scattered over a
        dozen toolbars -- `view` reaches into Sketcher and Mesh. Pooling all
        of their neighbours returns the union of those toolbars, which is
        noise. The toolbar holding the most members is the family's home,
        and only that one is asked.
        """
        members = set(commands)
        homes = {}
        for command in commands:
            toolbar = (self.commands.get(command) or {}).get("toolbar")
            if toolbar:
                homes[toolbar] = homes.get(toolbar, 0) + 1
        if not homes:
            return []
        home = max(homes, key=lambda k: (homes[k], k))
        near = [n for n in sorted(self._siblings.get(("toolbar", home), []))
                if n not in members][:limit]
        return near or self._family_siblings(homes, members, limit)

    def _family_siblings(self, homes, members, limit):
        """Other families sharing a toolbar with this one.

        A family whose members fill their toolbar has no neighbours by the
        usual reading -- everything beside `view front` is another view.
        What is genuinely next to it is the other families gathered from the
        same row: select, align, tree. Answered in commands, so the caller
        translates them to verb names the same way as any other neighbour.
        """
        out = []
        for name, (_, commands, _members) in self._families.items():
            if members & set(commands):
                continue
            for command in commands:
                toolbar = (self.commands.get(command) or {}).get("toolbar")
                if toolbar in homes:
                    out.append(command)
                    break
            if len(out) >= limit:
                break
        return out

    def choice_groups(self, name, verb=None):
        """A family's choices, under the menu headings FreeCAD filed them in.

        Forty-one view commands is a wall of names. FreeCAD already sorted
        them -- Standard Views, Stereo, Zoom, Axonometric -- when it built
        its menus, and that grouping is better than any this could invent.
        The menu is the field that answers: most of these commands have no
        toolbar at all.

        Returns [(heading, [choice, ...]), ...], largest group first, with
        whatever FreeCAD filed nowhere last under None.
        """
        if verb is not None and getattr(verb, "family", None) != name:
            return []       # the name collides with a family it is not
        family = self._families.get(name)
        if not family:
            return []
        groups = {}
        for choice, member in family[2].items():
            menu = (self.commands.get(member["command"]) or {}).get("menu")
            groups.setdefault(menu or None, []).append(choice)
        if len(groups) < 2:
            return []
        ordered = sorted(((k, sorted(v)) for k, v in groups.items() if k),
                         key=lambda kv: (-len(kv[1]), kv[0]))
        loose = groups.get(None)
        return ordered + ([(None, sorted(loose))] if loose else [])

    def neighbours(self, registry, verb, limit=8):
        """`adjacent`, answered in verb names rather than command names.

        A neighbour reachable under a name someone chose is offered under
        that name; the rest are offered as the launchers they are.
        """
        command = getattr(verb, "gui_command", None)
        family = (self._families.get(verb.family)
                  if getattr(verb, "family", None) else None)
        if not command and not family:
            return []
        by_command = {}
        for name in registry.names():
            other = registry.get(name)
            source = getattr(other, "gui_command", None)
            if source and source not in by_command:
                by_command[source] = name
        if command:
            near_commands = self.adjacent(command, limit=limit * 2)
        else:
            near_commands = self._family_neighbours(family[1], limit)

        out = []
        for near in near_commands:
            name = by_command.get(near)
            if name and name not in out:
                out.append(name)
            if len(out) >= limit:
                break
        return out

    # ------------------------------------------------------------ order

    def order(self, registry, names):
        """Sort verb names by rank, then alphabetically.

        Stable within a rank, so the answer does not move around between
        keystrokes. Nothing is dropped -- a registry-rank verb sorts last
        and is still there.
        """
        def key(name):
            return (self.rank_of(registry.get(name)), name)
        return sorted(names, key=key)

    def census(self, registry=None):
        """Counts per rank, for `commands` to report."""
        if registry is None:
            ranks = [self.rank(n) for n in self.commands]
        else:
            ranks = [self.rank_of(registry.get(n)) for n in registry.names()]
        return {RANK_NAMES[r]: ranks.count(r)
                for r in (PROMOTED, MENU, REGISTRY)}


_CURATION = Curation()


def load(descriptor):
    """Install the curation the descriptor describes."""
    global _CURATION
    _CURATION = Curation((descriptor or {}).get("commands", {}))
    return _CURATION


def current():
    return _CURATION
