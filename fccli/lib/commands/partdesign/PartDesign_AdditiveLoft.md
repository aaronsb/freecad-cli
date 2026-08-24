---
command: "PartDesign_AdditiveLoft"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Additive Loft"
  tooltip: "Lofts the selected sketch or profile along a path and adds it to the body"
  toolbar: "Part Design Modeling Features"
  menu: "Additive Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_AdditiveLoft"
  wiki_rev: "0499378"
  seed: "ada107a30f8c"
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

Additive Loft creates a solid in the active Body by making a transition between two or more sketches (also referred to as cross-sections). If the Body already contains features, the additive loft will be merged to them.

## See also

- PartDesign_AdditivePipe
- PartDesign_SubtractiveLoft
