---
command: "PartDesign_Migrate"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Migrate"
  tooltip: "Migrates the document to the modern Part Design workflow"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Migrate"
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

The PartDesign workbench in FreeCAD v0.17 introduces new tools and elements that are not recognized by older FreeCAD versions (0.16 and older). FreeCAD documents created in older versions can still be opened and edited. To benefit from the new features, they must be migrated via the menu PartDesign → Migrate.
