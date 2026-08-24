---
command: "OpenSCAD_AddOpenSCADElement"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Add OpenSCAD Element"
  tooltip: "Adds an OpenSCAD element based on entered OpenSCAD code using the OpenSCAD binary"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "OpenSCADWorkbench"
  wiki: "OpenSCAD_AddOpenSCADElement"
  wiki_rev: "0499378"
  seed: "5c448fb09462"
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

Add an OpenSCAD element by entering OpenSCAD code into the task panel and executing the OpenSCAD binary (requires OpenSCAD)

When 'as mesh' is selected, OpenSCAD renders a Mesh.

Each time Add is pressed the OpenSCAD code is executed and elements are imported.

If OpenSCAD returns successfully, its messages are displayed as warnings in the report window. This will be the case if the path to imported, included and used files is broken. In case of undesired results it is highly recommend to have a look at the report windows, as there might be a lot of other output, created by the importer. If OpenSCAD fails, its messages will be logged as errors.

Libraries should be accessible as usual, whereas example can be reached as stated below.

```python include ; ```

would include the first examples also known as the OpenSCAD icon.
