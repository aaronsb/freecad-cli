---
command: "Draft_Label"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Label"
  tooltip: "Creates a label, optionally attached to a selected object or subelement"
  toolbar: "Annotation Tools"
  menu: "Annotation"
  shortcut: "D, L"
  workbench: "DraftWorkbench"
  wiki: "Draft_Label"
  wiki_rev: "0499378"
  seed: "9f10436c9dff"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft Label command creates a multi-line text with a 2-segment leader line and an arrow.

If an object or a sub-element (face, edge or vertex) is selected when starting the command, the text can be made to display one or two attributes of the selected element, including position, length, area, volume and material. The text will then be linked to the attributes and will update if their values change.

To insert a text element without an arrow use the Draft Text command instead.

## See also

- Draft_Text
- Draft_ShapeString
