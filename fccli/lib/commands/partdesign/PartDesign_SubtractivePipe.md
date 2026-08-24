---
command: "PartDesign_SubtractivePipe"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Subtractive Pipe"
  tooltip: "Sweeps the selected sketch or profile along a path and removes it from the body"
  toolbar: "Part Design Modeling Features"
  menu: "Subtractive Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_SubtractivePipe"
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

Subtractive Pipe creates a subtractive solid in the active Body by sweeping one or more sketches (also referred to as cross-sections) along an open or closed path. Its shape is then subtracted from the existing solid. SubtractivePipe is often used in connection with Part Helix and PartDesign ShapeBinder to create a thread; see the Thread for Screw Tutorial for details.

## See also

- PartDesign_AdditivePipe
- PartDesign_SubtractiveLoft
