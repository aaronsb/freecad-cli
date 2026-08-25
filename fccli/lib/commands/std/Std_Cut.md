---
command: "Std_Cut"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Cu&t"
  tooltip: "Removes the selection and copies it to the clipboard"
  toolbar: "Clipboard"
  menu: "Edit"
  shortcut: "Ctrl+X"
  workbench: null
  wiki: "Std_Cut"
  wiki_rev: "0499378"
  seed: "1289bf1eaeab"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Std Cut command is limited: it can only be used for spreadsheet cells. The command copies the contents and properties of cells to the Clipboard and then clears them.

To cut other objects you can use the Std Copy command followed by a delete operation.

## See also

- Std_Copy
- Std_Paste
- Std_DuplicateSelection
