---
command: "BIM_IfcProperties"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Manage IFC Properties"
  tooltip: "Manages the different IFC properties of the BIM objects"
  toolbar: "Manage Tools"
  menu: "Manage"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_IfcProperties"
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

The IFC properties manager allows you to edit the IFC properties of one selected object, many selected objects or all objects of the document. IFC properties are pieces of information attached to individual objects. They can only be attached to BIM objects, so any non-BIM object must first be converted to a BIM object using the Component tool before being able to hold IFC properties.

IFC properties can be custom, that is, you can define your own name and value for them, or follow a preset schema defined by the IFC standard. These properties are defined in Property sets and are usually made available for the most common IFC types. For example, the Pset_BeamCommon property set is made to be attached to beams. Predefined property sets usually contains usual properties that the IFC schema has defined for a particular type. For example, the Pset_WallCommon, that should be attached to walls, contains properties that define if the wall is load-bearing or is exterior or interior.

You can create your own properties and property sets and attribute them to any object. There is no requirement in the IFC schema to add predefined Psets for common types or any restriction to add custom properties. This is a decision left to users. Usually, when working in a team, these things get decided alongside other BIM requirements, to make sure all BIM models produced meet the same requirements.

## Defining your own property sets

The available predefined property sets are stored in the FreeCAD resource directory which can be found by entering this in the Python console:

```python FreeCAD.getResourceDir() ```

The predefined property sets are in /Mod/BIM/Presets/pset_definitions.csv.

Inside the CSV file, each line represents a different property set, beginning with the name of the set, and any number of Name;Type pairs, defining a property name and its type. For example:

This would define a property set named "FreeCAD" (the "Pset\_" prefix is not mandatory but is a common practice) that contains two properties: one called "Name" which is an IfcLabel (a piece of text), and another called "Version" which is an IfcReal (a numeric value with decimals).

You can add a custom csv file with your own property sets. This file must be named CustomPsets.csv and be placed in $USERAPPDATA/BIM.

The $USERAPPDATA folder depends on your platform/operating system:

- On Windows it is usually: %APPDATA%/FreeCAD
- On Linux it is usually: $HOME/.FreeCAD
- On macOS it is usually: $HOME/Library/Preferences/FreeCAD

It can also be found by entering this in the Python console:

```python FreeCAD.getUserAppDataDir() ```
