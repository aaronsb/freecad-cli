---
command: "Assembly_CreateAssembly"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "New Assembly"
  tooltip: "Creates an assembly object in the current document, or in the current active assembly (if any). Limit of one root assembly per file."
  toolbar: "Assembly"
  menu: "Assembly"
  shortcut: "A"
  workbench: "AssemblyWorkbench"
  wiki: "Assembly_CreateAssembly"
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

The Assembly CreateAssembly tool creates a root assembly (Assembly object) in the current document, or a sub-assembly in a pre-existing active assembly. A document can only hold one root assembly.

Each Assembly object is created with an Origin object and an empty Joints container by default.
