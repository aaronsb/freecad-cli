---
command: "Sketcher_SelectElementsWithDoFs"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Select Under-Constrained Elements"
  tooltip: "Selects geometrical elements where the solver still detects unconstrained degrees of freedom"
  toolbar: null
  menu: "Visual Helpers"
  shortcut: "Z, F"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_SelectElementsWithDoFs"
  wiki_rev: "0499378"
  seed: "e8275321ad63"
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

The Sketcher SelectElementsWithDoFs tool selects the not fully constrained elements in the sketch.

If such elements exist in a sketch the Solver messages section of the Sketcher Dialog displays this message:

- Under constrained: n DoF(s)

Where *n* is the remaining number of degrees of freedom. Clicking the underlined text will select the under-constrained elements.

Please note that a sketch can also have redundant constraints if one of the other solver messages is displayed.
