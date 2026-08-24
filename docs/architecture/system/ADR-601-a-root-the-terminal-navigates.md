---
status: Accepted
date: 2026-08-24
deciders:
  - aaronsb
  - claude
related:
  - ADR-100
  - ADR-600
---

# ADR-601: A root the terminal navigates

## Context

`fccli exec < file` already runs a file of command lines, history already
replays them, and FreeCAD already has the Python tier: `.FCMacro` files, a
macro directory preference, and `Std_DlgMacroExecuteDirect`. What is
missing is a place: scripts an operator writes, notes beside them, and a
way to reach both from either terminal without leaving FreeCAD.

`paths.py` owns `$XDG_DATA_HOME/fccli/` with `patches/` and the alias file
in it. The operator uses a keyboard fluently and a GUI by hunt-and-peck; a
directory tree navigated by `cd` and `ls` is the keyboard's way of
organising work.

## Decision

A real directory on disk, laid out after the Filesystem Hierarchy
Standard, that the terminal treats as `/`:

```
~/.local/share/fccli/            /
  bin/                           .fccli scripts on the path; run by bare name
  lib/  -> <addon>/fccli/lib     shipped, read-only: the command tree (ADR-100)
  lib/addons/<name> -> <Mod>/<name>/fccli   what each addon ships
  etc/                           local overrides: commands/, patches/, aliases
  macros/ -> FreeCAD MacroPath   the Python tier
  <anything>/                    the operator's own directories
```

`lib/commands`, `lib/addons/*` and `macros` are symlinks the tool creates
on first run, targets read from the addon's install path and FreeCAD's
`MacroPath` preference. `lib` itself is a real directory: the addon links
are per machine and cannot live inside the repository. A directory the
tool would make that is already a link, or a file, is left as it is and
said once. Nothing is written to FreeCAD's directories.

`cd`, `ls`, `pwd` and `cat` are not recorded: a replayed `cd` would move
a later session, and Up does not recall them.

*Amended 2026-08-24 on building it: `lib` is a directory of links, not
one link; the four navigation verbs stay out of history; a script run by
path takes its arguments inline rather than prompting; `rehash` re-reads
`bin/`.*

**The working directory is session state.** One session, one cwd; `cd`
in the dock moves the socket client too, in lockstep, the same way `use`
scope already is. The prompt shows it beside the workbench.

**The root is a jail.** `cd ..` at `/` stays at `/`; no path resolves
outside the root. What lies outside is reached by a symlink somebody made
on purpose.

**Three file kinds.** `.fccli` is executable: YAML frontmatter and a body
of command lines. `.md` is a note, rendered by `cat` and by `man` when it
sits beside a script or a command file of the same name. `.FCMacro` is
run through FreeCAD's macro manager, the way `Std_DlgMacroExecuteDirect`
runs one.

**Name resolution.** A bare token resolves against the verb registry
first; a `.fccli` in `/bin` registers as a verb by file name and so
completes and replays like any verb. Elsewhere a script runs by path,
`./tower` or `plinth/tower`. A project directory never shadows a launcher.

**Scripts take arguments.** The frontmatter declares them in the step
syntax `PATCH["verbs"]` already uses, and the body refers to them as
`$id`:

```yaml
---
doc: A square plinth with a cylinder on it.
steps:
  - {id: size, kind: quantity, prompt: Plinth size, unit: mm}
  - {id: height, kind: quantity, prompt: Height, unit: mm, default: 20}
---
box 0,0,0 $size $size $height
cylinder $size/4 $height
```

This format is experimental. The frontmatter keys, `$` substitution, and
the absence of control flow are the first cut; the ADR that settles the
syntax supersedes this section.

**A script runs line by line** through `submit`, stopping at the first
error or incomplete line. The call goes into history as one line; the
lines inside do not. **A script is not undone as a unit**: each line
remains the FreeCAD undo step it is today. Unit undo is future work.

**Builtins added:** `cd`, `ls`, `pwd`, `cat`. Completion over directory
entries at a path-shaped token.

## Consequences

### Positive

- Scripts, notes, overrides and macros in one tree the operator can
  manage with ordinary tools and keep in git.
- Both terminals see the same tree and the same cwd with no client work,
  because the builtins are verbs on the shared session.
- The parser gains nothing. A script is lines it already accepts.

### Negative

- A session-level cwd means one client's `cd` surprises another. That is
  the shared-line model applied consistently, and the prompt shows where
  the session is.
- YAML frontmatter parsing depends on PyYAML, which FreeCAD itself
  requires; no new dependency, but a dependency on FreeCAD's environment
  rather than the standard library.

### Neutral

- `patches/` and the alias file move under `etc/`. `paths.py` already
  carries one legacy fallback and gains a second.
- `/lib` is read-only by convention; the lint (ADR-100) refuses a hand
  edit inside a generated block, and an override belongs in `/etc`.

## Alternatives Considered

- **Scripts as registry entries, no directory.** No place for notes, no
  organisation, nothing to `ls`.
- **Per-client cwd.** Mirrors real shells and breaks the one-transcript
  rule; the socket would show a path the dock does not.
- **FreeCAD's macro directory as the root.** FreeCAD cannot run a `.fccli`
  file, and writing there is writing into FreeCAD's settings. A symlink in
  gives the macros without the ownership.
- **A virtual filesystem** mapping `/lib` to install paths in code.
  Symlinks on disk do the same and are visible to every other tool.
- **Unit undo now.** FreeCAD transactions do not nest; a script as one
  step means its lines skip theirs, which changes the engine for a
  feature nobody has used yet.
