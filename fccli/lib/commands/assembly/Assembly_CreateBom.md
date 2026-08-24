---
command: "Assembly_CreateBom"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Bill of Materials"
  tooltip: "Creates a bill of materials of the current assembly. If an assembly is active, it will be a BOM of this assembly. Else it will be a BOM of the whole document.The BOM object is a document object that stores the settings of your BOM. It is also a spreadsheet object so you can easily visualize the BOM. If you do not need the BOM object to be saved as a document object, you can simply export and cancel the task.The columns 'Index', 'Name', 'File Name' and 'Quantity' are automatically generated on recompute. The 'Description' and custom columns are not overwritten."
  toolbar: "Assembly"
  menu: "Assembly"
  shortcut: "O"
  workbench: "AssemblyWorkbench"
  wiki: "Assembly_CreateBom"
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

The Assembly CreateBom tool derives a bill of materials (BOM), from a selected assembly, or from the document if no assembly is selected.
