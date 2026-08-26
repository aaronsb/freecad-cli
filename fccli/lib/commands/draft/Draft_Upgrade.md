---
command: "Draft_Upgrade"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Upgrade"
  tooltip: "Upgrades the selected objects into more complex shapes. The result of the operation depends on the types of objects, which may be able to be upgraded several times in a row. For example, it can join the selected objects into one, convert simple edges into parametric polylines, convert closed edges into filled faces and parametric polygons, and merge faces into a single face."
  toolbar: "Object Tools"
  menu: "Modify"
  shortcut: "U, P"
  workbench: "DraftWorkbench"
  wiki: "Draft_Upgrade"
  wiki_rev: "0499378"
  seed: "e047a0a42f67"
# authored from here down; the tool never rewrites these
verb: null
example: select Wire; upgrade
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft Upgrade command upgrades selected objects. The result depends on the number of selected objects and their type. The command can for example fuse elements and create faces. It is worth trying to upgrade a selection several times to see if a better result can be obtained. See the example in the image. Note that not all objects can be upgraded. This command is the counterpart of the Draft Downgrade command.

## See also

- Draft_Downgrade
