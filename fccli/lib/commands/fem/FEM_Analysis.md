---
command: "FEM_Analysis"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "New Analysis"
  tooltip: "Creates an analysis container with default solver"
  toolbar: "Model"
  menu: "Model"
  shortcut: "S, A"
  workbench: "FemWorkbench"
  wiki: "FEM_Analysis"
  wiki_rev: "0499378"
  seed: "fd8fbda48496"
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

The FEM Analysis could be seen as a container that holds all objects of a Finite Element Analysis. It is mandatory to have an analysis container that holds all the needed objects. At least one of the following objects (apart from the mesh) is necessary for a mechanical analysis:

- solid material,
- fixed boundary condition or displacement boundary condition or rigid body constraint.

## See also

- FEM_tutorial
