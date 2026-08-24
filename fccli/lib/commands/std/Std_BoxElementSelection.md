---
command: "Std_BoxElementSelection"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Bo&x Element Selection"
  tooltip: "Activates box element selection"
  toolbar: null
  menu: "Edit"
  shortcut: "Shift+E"
  workbench: null
  wiki: "Std_BoxElementSelection"
  wiki_rev: "0499378"
  seed: "ad6db8ff0a28"
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

The Std BoxElementSelection command selects faces from a user defined rectangular area, a box, in the 3D view.

Note that if a whole object falls inside the rectangle, the object itself, instead of its faces, is selected. To avoid this create two box selections for each object (hold down Ctrl while dragging the 2nd rectangle), or use the Part BoxSelection command instead.

## See also

- Part_BoxSelection
- Std_BoxSelection
- Std_SelectAll
