---
command: "FEM_ConstraintTie"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Tie Constraint"
  tooltip: "Creates a tie constraint"
  toolbar: "Mechanical Boundary Conditions and Loads"
  menu: "Mechanical Boundary Conditions and Loads"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_ConstraintTie"
  wiki_rev: "0499378"
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

Defines a tie constraint that connects the two selected surfaces in such a way that (as opposed to how contact works) they can\'t separate or slide on each other throughout the analysis. Thus, the surfaces remain permanently bonded all the time. Can be also used to define cyclic symmetry.

## See also

- FEM_ConstraintPressure
