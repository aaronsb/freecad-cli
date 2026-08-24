---
command: "Std_LinkMakeRelative"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Make Sub-Link"
  tooltip: "Creates a sub-object or sub-element link"
  toolbar: null
  menu: null
  shortcut: null
  workbench: null
  wiki: "Std_LinkMakeRelative"
  wiki_rev: "0499378"
  seed: "2b1e7d276658"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
rank: null
type: null
---

[Std LinkMakeRelative

creates an App Link (`App::Link` class), just like [Std LinkMake, but it operates on selected subelements first, and sets the Link Transform to `True`.

## See also

- Std_Part
- Std_Group
- Std_LinkMake
