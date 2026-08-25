---
command: "FEM_SolverCalculiX"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Solver CalculiX"
  tooltip: "Creates a FEM solver CalculiX"
  toolbar: null
  menu: "Solve"
  shortcut: "S, C"
  workbench: "FemWorkbench"
  wiki: "FEM_SolverCalculiX"
  wiki_rev: "0499378"
  seed: "c5b37bd25fe7"
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

The Solver CalculiX (new framework) command creates a SolverCalculix object, which uses the same framework as Elmer and Z88 solvers (the code is not visible for the user). It is preferred to use the original framework Solver CalculiX Standard because it contains extra checks, e.g. showing the elements with nonpositive Jacobian which might cause solution difficulties.
