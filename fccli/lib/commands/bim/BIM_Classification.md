---
command: "BIM_Classification"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Manage Classification"
  tooltip: "Manages classification systems and apply classification to objects"
  toolbar: "Manage Tools"
  menu: "Manage"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_Classification"
  wiki_rev: "0499378"
  seed: "a255ea6cc925"
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

The Classification manager allows you to attribute a standard class to a BIM object or material. Several classification systems are available in XML or IFC form (both are supported by this tool) from , or directly from their publishers, or from . To make these XML or IFC files known to FreeCAD they must be placed in a BIM subfolder of your FreeCAD user folder. The exact location for your system is informed on the BIM classification dialog. If both an IFC and XML file are available, the BIM Classification tool will prefer the IFC one.
