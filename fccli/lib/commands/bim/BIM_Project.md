---
command: "BIM_Project"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "IFC Project"
  tooltip: "Creates an empty NativeIFC project"
  toolbar: null
  menu: "Utils"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_Project"
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

The BIM Project tool creates a native IFC project in the current document. In IFC, a project (IfcProject) is the root object of all the contents of the model. It is mandatory to have one in each IFC file.

It is not necessary to create a project to export a FreeCAD model to IFC, as a default one will be added each time you export an IFC file. However, when working with NativeIFC, an IFC file is attached to the model, and all the geometry and properties of that model and its components come from the attached IFC file. The project is where the IFC file is attached to the document.

Typically, you create a BIM project to attach an IFC file. When creating the project, the attached IFC file is blank, and not saved. The next time you will save the FreeCAD file, you will also be asked to save the IFC file.

If you distribute the FreeCAD file, all attached IFC files must be distributed together, otherwise FreeCAD won\'t be able to extract the geometry. However, if the shape mode property of all objects contained in a project is set to Shape, then the FreeCAD file can be distributed without the accompanying IFC file, and will still open correctly on other computers. The IFC objects, however, won\'t be editable anymore.

When inserting an IFC file, a project object is created, that contains all the contents of the file. Like all NativeIFC objects, the project can be expanded by double-clicking it in the tree.
