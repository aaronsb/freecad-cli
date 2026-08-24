---
command: "TechDraw_View"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "New View"
  tooltip: "Inserts a new view into the current page based on the selected object in the tree view or 3D view. If no object is selected, a file browser opens to select an SVG or image file."
  toolbar: "TechDraw Views"
  menu: "TechDraw Views"
  shortcut: null
  workbench: "TechDrawWorkbench"
  wiki: "TechDraw_View"
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

The TechDraw View tool adds a representation of one or more objects to a Drawing page. It can create a Projection Group Item (a single view), a Projection Group, a Spreadsheet View, an Arch View, a Symbol or an Image View.

In {{VersionMinus|0.21}} the tool can only create a Part View, which is very similar to a Projection Group Item.

## See also

- TechDraw_ProjectionGroup
- TechDraw_SpreadsheetView
- TechDraw_ArchView
- TechDraw_Symbol
- TechDraw_Image
