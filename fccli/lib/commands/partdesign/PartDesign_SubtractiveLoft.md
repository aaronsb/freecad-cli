---
command: "PartDesign_SubtractiveLoft"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Subtractive Loft"
  tooltip: "Lofts the selected sketch or profile along a path and removes it from the body"
  toolbar: "Part Design Modeling Features"
  menu: "Subtractive Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_SubtractiveLoft"
  wiki_rev: "0499378"
  seed: "daad804bfd7e"
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

Subtractive Loft creates a subtractive solid in the active Body by making a transition between two or more sketches (also referred to as cross-sections). Its shape is then subtracted from the existing solid.

## See also

- PartDesign_AdditiveLoft
- PartDesign_SubtractivePipe
