---
command: "Arch_Survey"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Survey"
  tooltip: "Starts survey"
  toolbar: null
  menu: "Utils"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_Survey"
  wiki_rev: "0499378"
  seed: "4a61ff0b8040"
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

The Arch Survey tool enters a special surveying mode, which allows you to quickly grab measurements and information from a model, and transfer that information to other applications. Once you are in Survey mode, clicking on different subelements of 3D objects gathers the following information (depending on what you click):

- If you click on an edge, you get its length
- If you click on a vertex, you get its height (coordinate on the Z axis)
- If you click on a face, you get its area
- If you double-click anything, therefore select the whole object, you get its volume

When such a piece of information is gathered, several things happen:

- A label is placed on top of the element you clicked, that displays the value (with "a" for area, "l" for length, "z" for height, or "v" for volume)
- The numeric value is copied to the clipboard, so you can paste it in another application
- A line is printed on the FreeCAD output window. After you exit the survey mode, those lines can be copied and pasted in another application (the values are comma-separated, making it easy to convert to spreadsheet data)
- The total length or area of the elements you clicked so far is also printed in the output window
- Each length or area is also recorded in the task dialog

## See also

- Macro_FCInfo
- Macro_SimpleProperties
