---
command: "Std_LinkReplace"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Replace With Link"
  tooltip: "Replaces the selected objects with links"
  toolbar: null
  menu: null
  shortcut: null
  workbench: null
  wiki: "Std_LinkReplace"
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

[Std LinkReplace

replaces an object that is inside another for an App Link version of the former.

This operation acts on the \"children\" of a \"parent\" object as seen in the tree view. For example, given two objects (A and B) that participate in a [Part Boolean operation, say, C = A + B, the A object can be replaced by a Link, so that C = A_link + B.

This operation can be done to replace nested objects that are in a complex assembly for a Link, which may be more efficient if that nested object is used many times in different sub-assemblies. The inverse operation is [Std LinkUnlink. To create a generic Link see [Std LinkMake.

## See also

- Std_LinkMake
- Std_LinkMakeRelative
- Std_LinkUnlink
