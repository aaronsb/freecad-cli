---
command: "CAM_Profile"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Profile"
  tooltip: "Profile entire model, selected face(s) or selected edge(s)"
  toolbar: "New Operations"
  menu: "CAM"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_Profile"
  wiki_rev: "0499378"
  seed: "79b210540ee7"
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

The Profile tool creates a contour operation based on selected features of the model. The tool was introduced in version 0.19. It offers three operations that were handled by separate tools in previous versions.

All operations create objects that are made to be part of a CAM Job.

These are the available operations:

## Contour operation

A Contour operation is the default. It creates a simple external contour cut of complex 3D Part-based objects. The entire Job Model serves as the input for the Operation, regardless of whether any Body Geometry is selected when the Contour command is invoked.

## Profile Face operation

A Profile Face operation creates a simple contour path from one or more selected faces of an object.

## Profile Edges operation

A Profile Edges operation creates a simple contour path from selected edges.
