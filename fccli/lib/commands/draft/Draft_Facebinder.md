---
command: "Draft_Facebinder"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Facebinder"
  tooltip: "Creates a facebinder from the selected faces"
  toolbar: "Draft Creation"
  menu: "Drafting"
  shortcut: "F, F"
  workbench: "DraftWorkbench"
  wiki: "Draft_Facebinder"
  wiki_rev: "0499378"
  seed: "f6f41aabdfd4"
# authored from here down; the tool never rewrites these
verb: null
example: select Box.Face6; facebinder
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft Facebinder command creates a surface object from selected faces. A Draft Facebinder is parametric, it will update if you modify its source object(s).

It can be used to create an extrusion from a collection of faces. This extrusion can for example represent a wall finish in architectural design.
