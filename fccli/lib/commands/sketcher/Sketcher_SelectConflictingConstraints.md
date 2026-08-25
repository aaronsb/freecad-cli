---
command: "Sketcher_SelectConflictingConstraints"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Select Conflicting Constraints"
  tooltip: "Selects all conflicting constraints"
  toolbar: null
  menu: "Visual Helpers"
  shortcut: "Z, P, C"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_SelectConflictingConstraints"
  wiki_rev: "0499378"
  seed: "7a7bb87dadcd"
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

The Sketcher SelectConflictingConstraints tool selects the conflicting constraints in the sketch.

If such constraints exist in a sketch the Solver messages section of the Sketcher Dialog displays this message:

- Over-constrained: (#, #, #)

Where *(#, #, #)* are the indices of the constraints. Clicking the underlined text will select the conflicting constraints.
