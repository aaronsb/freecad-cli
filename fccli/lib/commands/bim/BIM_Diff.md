---
command: "BIM_Diff"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "IFC Diff"
  tooltip: "Shows the difference between two IFC-based documents"
  toolbar: null
  menu: "Utils"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_Diff"
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

The BIM Diff tool takes two open FreeCAD documents, and produces a visual diff between them.

"diff" in programming refers to a utility application that takes two text documents and highlights the lines that are different between them. It usually marks in red the lines that have been removed and in green the lines that have been added. Its main purpose is to quickly grasp what has changed in two different versions of the same document.

This tool does the same thing, but graphically. It opens a new document, shows the contents of file B, but highlights:

This tool is primarily suited for IFC files, as it uses the IFC Global ID to make sure one object in one file is still the same in the other file. However, it will also work with two non-IFC FreeCAD files.
