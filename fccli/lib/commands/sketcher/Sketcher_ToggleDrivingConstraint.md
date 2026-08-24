---
command: "Sketcher_ToggleDrivingConstraint"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Toggle Driving/Reference Constraints"
  tooltip: "Toggles between driving and reference mode of the selected constraints and commands"
  toolbar: null
  menu: "Constraints"
  shortcut: "K, X"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ToggleDrivingConstraint"
  wiki_rev: "0499378"
  seed: "d2e44b64c810"
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

The Sketcher ToggleDrivingConstraint tool either toggles the dimensional constraint creation tools between driving and reference mode, or toggles selected dimensional constraints between those modes.

Contrary to driving constraints, reference constraints do not constrain the sketch, their value depends on other constraints, they are driven. They can be useful to verify measurements. They can be used in expressions, but not in the sketch itself.

## See also

- Sketcher_ToggleActiveConstraint
