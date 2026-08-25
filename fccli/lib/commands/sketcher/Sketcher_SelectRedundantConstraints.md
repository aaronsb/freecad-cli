---
command: "Sketcher_SelectRedundantConstraints"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Select Redundant Constraints"
  tooltip: "Selects all redundant constraints"
  toolbar: null
  menu: "Visual Helpers"
  shortcut: "Z, P, R"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_SelectRedundantConstraints"
  wiki_rev: "0499378"
  seed: "6cfea588ed1f"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Sketcher SelectRedundantConstraints tool selects the redundant constraints in the sketch.

If such constraints exist in a sketch the Solver messages section of the Sketcher Dialog displays this message:

- Redundant constraints: (#, #, #)

Where *(#, #, #)* are the indices of the constraints. Clicking the underlined text will select the redundant constraints.

Please note that a sketch can also have redundant constraints if one of the other solver messages is displayed.
