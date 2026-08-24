---
command: "Sketcher_SwitchVirtualSpace"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Switch Virtual Space"
  tooltip: "Switches the selected constraints or the view to the other virtual space"
  toolbar: "Visual Helpers"
  menu: "Visual Helpers"
  shortcut: "Z, Z"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_SwitchVirtualSpace"
  wiki_rev: "0499378"
  seed: "3e118457c32f"
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

The Sketcher SwitchVirtualSpace tool either (un)hides constraints or switches the visible virtual space.

A sketch has two virtual spaces that can contain constraints. All constraints are created in the main virtual space, but they can be hidden which moves them to the other virtual space.
