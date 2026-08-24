---
command: "Draft_Downgrade"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Downgrade"
  tooltip: "Downgrades the selected objects into simpler shapes. The result of the operation depends on the types of objects, which may be downgraded several times in a row. For example, a 3D solid is deconstructed into separate faces, wires, and then edges. Faces can also be subtracted."
  toolbar: "Object Tools"
  menu: "Modify"
  shortcut: "D, N"
  workbench: "DraftWorkbench"
  wiki: "Draft_Downgrade"
  wiki_rev: "0499378"
  seed: "a39544f2b148"
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

The Draft Downgrade command downgrades selected objects. The result depends on the number of selected objects and their type. The command can for example deconstruct a 3D solid into separate faces and a wire into separate edges. If two face are selected a Part Cut object is created from them. Note that not all objects can be downgraded. This command is the counterpart of the Draft Upgrade command.

## See also

- Draft_Upgrade
- Part_Cut
