---
command: "FEM_ConstraintContact"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Contact Constraint"
  tooltip: "Creates a contact constraint between faces"
  toolbar: "Mechanical Boundary Conditions and Loads"
  menu: "Mechanical Boundary Conditions and Loads"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_ConstraintContact"
  wiki_rev: "0499378"
  seed: "be7ffae96fbf"
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

Creates a contact constraint between 2 surfaces. Unlike in the case of tie constraint, the surfaces can separate and slide on each other (with or without friction) during the analysis.

## See also

- FEM_ConstraintFixed
