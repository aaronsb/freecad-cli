---
command: "FEM_ResultsPurge"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Purge Results"
  tooltip: "Purges all results from the active analysis"
  toolbar: "Results"
  menu: "Results"
  shortcut: "R, P"
  workbench: "FemWorkbench"
  wiki: "FEM_ResultsPurge"
  wiki_rev: "0499378"
  seed: "2a40423881a9"
# authored from here down; the tool never rewrites these
verb: null
example: purge_results
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

FEM ResultsPurge deletes all result objects and all result meshes from the active analysis container in the Tree view. Deletes all output objects from all solvers (CalculiX results objects, pipelines, filters and text reports).

If you only want to delete a result object and keep the result mesh, create a copy of the result mesh, then select the Result object in the tree view and delete it by pressing Del. This way the created copy of the mesh will remain. (Using FEM ResultsPurge would also delete the copy.)

## See also

- FEM_tutorial
