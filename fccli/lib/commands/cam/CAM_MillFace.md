---
command: "CAM_MillFace"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Face"
  tooltip: "Create a Facing Operation from a model or face"
  toolbar: "New Operations"
  menu: "CAM"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_MillFace"
  wiki_rev: "0499378"
  seed: "49748ebcad66"
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

The Mill Face tool creates a path to perform a facing operation on a horizontal surface. This operation is generally used:

- to smooth out a rough stock surface,
- to mill selected face(s) to desired depth in preparation for performing subsequent clearing operations within the boundary of the regions affected by this operation,
- or to apply a finishing surface to the selected face(s).

This operation contains a BoundaryShape property that allows for a modified selection area based upon the selected face(s).
