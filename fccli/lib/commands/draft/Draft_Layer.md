---
command: "Draft_Layer"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "New Layer"
  tooltip: "Adds a layer to the document. Objects added to this layer can share the same visual properties."
  toolbar: null
  menu: "Utilities"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_Layer"
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

The Draft Layer command creates a Draft Layer. A layer is a special kind of group with a number of visual properties. These properties, and any changes to them, are propagated to the objects placed inside the layer. The layers themselves are put in another special group: the Draft LayerContainer.

## See also

- Draft_AutoGroup
- Draft_LayerManager
