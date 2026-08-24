---
command: "CAM_Vcarve"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Vcarve"
  tooltip: "Creates a medial line engraving toolpath"
  toolbar: null
  menu: "CAM"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_Vcarve"
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

The Vcarve tool is primarily for center-line engraving a Draft ShapeString onto a part. However, it may be useful for other kinds of 2D.

Unlike engraving which follows the lines in the shapestring, V-carving uses a V-shaped cutter and attempts to clear the area by moving the cutter down the center of the region and varying the depth of cut. Since a v-cutter radius varies with the depth, the width of cut varies as well. The result is a more natural looking cut, particularly for serif fonts.

The V-carve algorithm calculates a path down the center-line of a region using a Voronoi diagram. This center-line is the path the tool will follow in the XY plane. It next calculates a 'maximum inscribed circle' along the path. This is the largest circle that can be drawn at that point and remain entirely inside the clearing area. Using the circle radius and the tip angle of the cutter, the depth of cut is calculated.
