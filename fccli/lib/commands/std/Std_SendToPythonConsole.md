---
command: "Std_SendToPythonConsole"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "&Send to Python Console"
  tooltip: "Sends the selected object to the Python console"
  toolbar: null
  menu: "Edit"
  shortcut: "Ctrl+Shift+P"
  workbench: null
  wiki: "Std_SendToPythonConsole"
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

The Std SendToPythonConsole command creates variables in the Python console referencing a selected object and its selected subshapes, along with some other useful references. The variables and the code involved can be used in the development of Python code.

Depending on the selected object and its selected subshapes, if any, the following variables are created:

+++ | Variable name | Referenced object(s) | +=================+=========================================================================================================================================================+ | | The document containing the selected object | | {{Incode|doc}} | | | | | +++ | | The selected Link object (only created if the selected object is a Link) | | {{Incode|lnk}} | | | | | +++ | | Depending on the selected object: | | {{Incode|obj}} | The selected object itself (if the selected object is not a Link) | | | The Linked object (if the selected object is a Link) | +++ | | Depending on the type of {{Incode|obj}}: | | {{Incode|shp}} | The {{Incode|Shape}} property of {{Incode|obj}} (for objects derived from the {{Incode|Part::Feature}} class) | | | The {{Incode|Mesh}} property of {{Incode|obj}} (for Mesh objects) | | | The {{Incode|Points}} property of {{Incode|obj}} (for Points objects) | +++ | | The first selected subshape (only created if at least one subshape is selected) | | {{Incode|sub}} | | | | | +++ | | A list containing all subshapes (only created if two or more subshapes are selected) | | {{Incode|subs}} | | | | | +++

>>> ### Begin command Std_SendToPythonConsole >>> try: >>> del(doc,lnk,obj,shp,sub,subs) >>> except Exception: >>> pass >>> >>> doc = App.getDocument("Unnamed") >>> lnk = doc.getObject("Link") >>> obj = lnk.getLinkedObject() >>> shp = obj.Shape >>> sub = obj.getSubObject("Edge10") >>> subs = [obj.getSubObject("Edge10"),obj.getSubObject("Face3"),obj.getSubObject("Vertex5"),] >>> ### End command Std_SendToPythonConsole
