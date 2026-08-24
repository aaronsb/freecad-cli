---
command: "Draft_Rotate"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Rotate"
  tooltip: "Rotates the selected objects. If the \"Copy\" option is active, it will create rotated copies."
  toolbar: "General Tools"
  menu: "Modify"
  shortcut: "R, O"
  workbench: "DraftWorkbench"
  wiki: "Draft_Rotate"
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

The Draft Rotate command rotates or copies selected objects around a center point by a given angle. The axis of rotation is perpendicular to the current working plane and the rotation angle is relative to that plane. In subelement mode the command rotates selected points and edges, or copies selected edges, of Draft Lines and Draft Wires.

The command can be used on 2D objects created with the Draft Workbench or Sketcher Workbench, but also on many 3D objects such as those created with the Part Workbench, PartDesign Workbench or BIM Workbench.

## See also

- Draft_SubelementHighlight
