---
command: "BIM_IfcExplorer"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "IFC Explorer"
  tooltip: "Opens the IFC explorer utility"
  toolbar: null
  menu: "Utils"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_IfcExplorer"
  wiki_rev: "0499378"
  seed: "13486591f536"
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

The BIM IfcExplorer is a simple utility to explore the contents of an IFC file. IFC files are text files, and are therefore readable in a text editor, but the information is condensed, unformatted, and difficult to browse. This utility presents to the user the exact same content, but displayed in an organized and readable method. The "IfcOpenShell" software library must be installed for this utility to work.

The purpose of this explorer is simply to allow you to check what is really written in an IFC file, in case you want to verify if the contents were correctly imported or exported to and from an IFC-aware application such as FreeCAD.

## See also

- Arch_IFC
