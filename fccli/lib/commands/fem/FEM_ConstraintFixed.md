---
command: "FEM_ConstraintFixed"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Fixed Boundary Condition"
  tooltip: "Creates a fixed boundary condition for a geometric entity"
  toolbar: "Mechanical Boundary Conditions and Loads"
  menu: "Mechanical Boundary Conditions and Loads"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_ConstraintFixed"
  wiki_rev: "0499378"
  seed: "42481b3062a2"
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

Creates a FEM boundary condition for a fixed geometrical entity by locking all the available degrees of freedom of the nodes underlying the selected geometrical entity (6 DOFs for beam and shell elements, 3 for solid elements).

## See also

- FEM_ConstraintContact
