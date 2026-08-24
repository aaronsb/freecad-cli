---
command: "Assembly_CreateView"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Exploded View"
  tooltip: "Creates an exploded view of the current assembly"
  toolbar: "Assembly"
  menu: "Assembly"
  shortcut: "E"
  workbench: "AssemblyWorkbench"
  wiki: "Assembly_CreateView"
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

The Assembly CreateView tool creates an exploded views container (Exploded_Views object) in the active Assembly that contains one (default) or more exploded views (Exploded_View objects). An assembly can only hold one exploded views container.

An exploded view collects the moves (Move objects) used to relocate parts from assembled position to exploded position. The altered positions of assembled parts and the representations of the moves are only visible when an exploded view is being edited and in TechDraw views derived from an exploded view.
