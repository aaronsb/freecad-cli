---
command: "BIM_Layers"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Manage Layers"
  tooltip: "Sets/modifies the different layers of your BIM project"
  toolbar: "Manage Tools"
  menu: "Manage"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_Layers"
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

The Layers Manager allows you to manage layers. Layers are a special kind of group that controls the visual properties of objects placed inside of it. By changing the properties of the Layer, such as line width, line color, shape color and transparency, the changes are propagated to its child objects. Layers don't interfere with any other FreeCAD structure such as groups or Building parts, so any object can be at the same time part of a layer and part of a group.

Layers are imported and exported from/to IFC and DXF/DWG.

The layers manager allow you to manage your layers, add or remove layers, or change their visual properties. To add objects to a layer, simply drag them into the layer in the tree view. To remove them, drag them from the layer and drop them into the document root.
