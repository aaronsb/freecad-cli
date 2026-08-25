---
command: "FEM_ConstraintSectionPrint"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Section Print Feature"
  tooltip: "Creates a section print feature"
  toolbar: "Geometrical Analysis Features"
  menu: "Geometrical Analysis Features"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_ConstraintSectionPrint"
  wiki_rev: "0499378"
  seed: "a8a4ef9801f7"
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

Prints the predefined facial output variables (forces and moments) to the data file. Can also print heat flux and drag stress (the latter requires the support for 3D fluid analyses with CalculiX which has not yet been implemented).
