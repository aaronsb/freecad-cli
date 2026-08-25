# freecad-cli

A command line embedded in FreeCAD, plus a socket client (`bin/fccli`) that
drives a running instance from outside. Python, PySide6, no external deps
beyond what FreeCAD ships.

The idea: FreeCAD has no CLI, but everything it does is a registered command
or a typed object. A factory reads FreeCAD's own registries into
`fccli/descriptor.json` and turns them into verbs. A hand-owned layer — one
Markdown file per command under `fccli/lib/commands/`, seeded from the
FreeCAD wiki — is where a person tunes names, docs, preconditions, families
and type ordering. The command line improves by editing that layer, not the
factory.

## Build and test

```
make check       # lint + version-check + offscreen tests. No GUI.
make check-all   # the above, plus the GUI (bvt) and socket suites.
make dictionary  # compile fccli/lib/commands into fccli/dictionary.json
make lint        # byte-compile, ADR lint, command-tree lint
make reconcile   # harvest FreeCAD afresh and report what changed
```

`make test` is offscreen (`QT_QPA_PLATFORM=offscreen`), no FreeCAD GUI.
`make bvt` drives a real GUI under Xvfb. `make socket` drives one over the
socket. Run `make check-all` before a PR.

## Working on the command tree

Every command has a file: `fccli/lib/commands/<workbench>/<Command>.md`,
Markdown with YAML frontmatter. The frontmatter has two halves.

- `generated:` is the tool's — harvest output (label, tooltip, placement,
  wiki page, seed). **Never edit it by hand.** `make lint` fails on a hand
  edit inside it; a change there belongs in an authored field.
- Everything below it is yours: `verb`, `aliases`, `requires`, `panel`,
  `family`/`choice`/`also`, `rank`, `type`. The body is the page `man`
  shows.

After editing a file, run `make dictionary` then `make lint`. The compiled
`fccli/dictionary.json` is what the factory reads at startup; the tree is
the source, and the lint fails when they disagree.

When FreeCAD itself changes (a new release, an addon), `make reconcile`
harvests afresh and reports what moved — commands added, removed, re-homed,
relabelled, bodies whose wiki page changed. `make reconcile FLAGS=--apply`
brings the tree, the descriptor and the dictionary to the new harvest
together. The decisions behind all of this are ADR-100.

## Living inside FreeCAD

- The addon is symlinked into `~/.local/share/FreeCAD/v1-1/Mod` (`make
  install`). A launch picks up what is on disk, but a **running** instance
  holds the code it imported at startup. Restart FreeCAD after editing.
- FreeCAD's settings are FreeCAD's. Read a preference; never write one to
  suit the CLI. `docs/conventions.md` has the rule and its limits.

## Driving a real GUI (probes, bvt)

- **Always set `QT_QPA_PLATFORM=xcb`** for a GUI probe. Qt6 picks its
  platform from `XDG_SESSION_TYPE`, so on Wayland `xvfb-run`'s DISPLAY is
  ignored and FreeCAD opens on your screen. `xvfb-run -a -s "-screen 0
  1600x1000x24" freecad <script.py>`.
- **Never `pkill -f Xvfb` in a compound Bash command.** It kills the
  agent's own process tree and returns exit 144 with no output.
- Never leave FreeCAD running from a socket session: `bin/fccli cancel`
  then `bin/fccli exec 'quit!'`. `quit!` alone is read as input for an open
  step.
- A probe script uses `QtCore.QTimer.singleShot(9000, run)` to wait for the
  dock, prints `PROBE`-prefixed lines, and quits itself with a second timer
  as a backstop. See the `freecad-probe` skill.

## Discipline that has paid off

- **Falsify a new check before trusting it:** reintroduce its specific
  fault and confirm the check fails. Several checks have passed vacuously
  until this step caught them.
- **Reading a regenerated descriptor or dictionary diff by hand** has found
  bugs no test and no reviewer raised. `make reconcile` is that reading, as
  a tool.
- **Dispatch a code-reviewer with a named axis** on a PR, verify its
  findings against source before acting, and reproduce each as a failing
  check before fixing.

## Where things are

| | |
|---|---|
| `tools/harvest_*.py`, `generate_descriptor.py` | the factory: FreeCAD's registries → `descriptor.json` |
| `tools/generate_commands.py`, `compile_dictionary.py`, `lint_dictionary.py`, `reconcile.py`, `docs_clone.py` | the command tree and its tooling |
| `fccli/factory.py` | composes descriptor + dictionary + patches into verbs |
| `fccli/engine.py` | the command engine (states in `docs/state.md`) |
| `fccli/panels.py`, `picking.py`, `modals.py`, `keyfilter.py` | intercept and normalisation |
| `fccli/dock.py`, `widget.py`, `bin/fccli` | the two terminals |
| `fccli/root.py`, `scripts.py`, `context.py` | the navigable root, scripts, the prompt context |
| `docs/conventions.md` | every rule the command line follows |
| `docs/state.md` | the engine and the six machines around it |
| `docs/architecture/` | decision records (ADRs), by domain — `docs/scripts/adr list --group` |
