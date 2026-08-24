---
command: "Std_LinkImportAll"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Import All Links"
  tooltip: "Imports all links of the active document"
  toolbar: null
  menu: null
  shortcut: null
  workbench: null
  wiki: "Std_LinkImportAll"
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

[Std LinkImportAll

imports all Linked Objects from Links into the current document, and then changes the attachment to point to these imported objects.

This command essentially runs [Std LinkImport for all Links in a document.

## See also

- Std_LinkMake
- Std_LinkMakeRelative
- Std_LinkImport
