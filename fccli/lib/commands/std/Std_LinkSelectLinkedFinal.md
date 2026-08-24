---
command: "Std_LinkSelectLinkedFinal"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Go to &Deepest Linked Object"
  tooltip: "Selects the deepest linked object and switches to its original document"
  toolbar: null
  menu: "Link Navigation"
  shortcut: "S, D"
  workbench: null
  wiki: "Std_LinkSelectLinkedFinal"
  wiki_rev: "0499378"
  seed: "d37809ede153"
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

The Std LinkSelectLinkedFinal command selects the Linked Object, the source object, of an App Link object, a link. But if that source object is also a link its linked object is selected instead. This is repeated until the linked object is not a link. This final source object is the deepest linked object.

## See also

- Std_LinkSelectLinked
- Std_LinkSelectAllLinks
