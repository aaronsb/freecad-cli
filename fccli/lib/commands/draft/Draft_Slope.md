---
command: "Draft_Slope"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Set Slope"
  tooltip: "Sets the slope of the selected line by changing the value of the Z value of one of its points. If a polyline is selected, it will apply the slope transformation to each of its segments. The slope will always change the Z value, therefore this command only works well for straight Draft lines that are drawn on the XY-plane."
  toolbar: "Draft Modification"
  menu: "Utils"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_Slope"
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

The Draft Slope command slopes selected Draft Lines or Draft Wires by increasing, or decreasing, the Z coordinate of all points after the first one. It can also be used to flatten Draft Wires. Note that the slope is relative to the XY plane defined by the Placement of the objects.
