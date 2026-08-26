---
command: "Part_Mirror"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Mirror"
  tooltip: "Mirrors the selected shape"
  toolbar: "Part Tools"
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Mirror"
  wiki_rev: "0499378"
  seed: "e7da605bf3be"
# authored from here down; the tool never rewrites these
verb: null
example: select Box; part_mirror
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

Part Mirror creates a new object (image) which is a reflection of the original object (source). The image object is created behind a mirror plane. The mirror plane may be standard plane (XY, YZ, or XZ), any plane parallel to a standard plane, or ( ) any arbitrary plane by using a reference object.

An example:
