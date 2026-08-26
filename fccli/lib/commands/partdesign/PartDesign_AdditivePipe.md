---
command: "PartDesign_AdditivePipe"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Additive Pipe"
  tooltip: "Sweeps the selected sketch or profile along a path and adds it to the body"
  toolbar: "Part Design Modeling Features"
  menu: "Additive Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_AdditivePipe"
  wiki_rev: "0499378"
  seed: "6a3c8c877759"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type:
  of: PartDesign::AdditivePipe
  doc: Sweep the selected profile along a spine and add it to the body.
  steps: [Profile, Spine]
  options: [Mode, Transition, Transformation]
  hide: [FuzzyTolerance, AuxiliarySpine, Binormal, UpToFace2, UpToShape2]
---

Additive Pipe creates a solid in the active Body by sweeping one or more sketches (also referred to as cross-sections) along an open or closed path. If the Body already contains features, the additive pipe will be merged to them.

## See also

- PartDesign_AdditiveLoft
- PartDesign_SubtractivePipe
