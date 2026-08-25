---
command: "Arch_CurtainWall"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Curtain Wall"
  tooltip: "Creates a curtain wall object from selected line or from scratch"
  toolbar: "3D/BIM Tools"
  menu: "3D/BIM"
  shortcut: "C, W"
  workbench: "BIMWorkbench"
  wiki: "Arch_CurtainWall"
  wiki_rev: "0499378"
  seed: "06a4b0c59276"
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

The Arch CurtainWall tool creates a curtain wall) by subdividing a base face into quadrangular faces, then creating vertical mullion on the vertical edges, horizontal mullions on the horizontal edges, and filling the spaces between mullions with panels.

Curtain Walls can be created from any type of existing object, in which case all the faces of the object will be subdivided. It works therefore best if used with an object that has only one face. Typically, you would first create a face, preferably bound by exactly 4 edges, that represents the area you want to fill with a curtain wall, then apply the tool.

Curtain walls can also be built from a linear object, such as a line, arc or polyline, like the normal wall tool.

Faces that have double curvature, or faces with more than 4 edges will work too, but the result is less predictable.

Faces will be divided in quadrangular facets. If the 4 points of the facet are coplanar, a square facet is created. If not, it is divided into two triangles and a diagonal mullion is added.

In case you need a non-regular subdivision, it is also possible to build your own subdivided object, for example using Arch Grid, and set the vertical and horizontal subdivisions of the curtain wall to 1.

You can also use the curtain wall tool without any selected object, in which case you will be able to draw a baseline, which will the be extruded vertically to form the face on which the curtain wall will be built.
