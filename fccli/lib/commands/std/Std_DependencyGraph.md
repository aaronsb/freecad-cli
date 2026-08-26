---
command: "Std_DependencyGraph"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Dependency Gra&ph"
  tooltip: "Shows the dependency graph of the objects in the active document"
  toolbar: null
  menu: "Tools"
  shortcut: null
  workbench: null
  wiki: "Std_DependencyGraph"
  wiki_rev: "0499378"
  seed: "ca966d97e64d"
# authored from here down; the tool never rewrites these
verb: null
example: dependency_graph
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Std DependencyGraph command displays the dependencies between objects in the active document in a graph. As opposed to the Tree view, objects are listed in reverse chronological order, with the first created object at the bottom.

It can be useful in analyzing a FreeCAD document and locating forks in a tree. The dependency graph layout will depend on which workbench was used to create the objects in the document. For example a model made exclusively in the PartDesign workbench can display a linear dependency graph with a single vertical branch. A model made with Part operations will have many branches, but for a single part they will join up at the top after Boolean operations. If they don't, it means that they are separate objects.

The dependency graph is purely a visualization tool, therefore it cannot be edited. It automatically updates if changes are made to the model.

## See also

- Std_ExportDependencyGraph
