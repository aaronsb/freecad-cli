---
command: "Draft_ApplyStyle"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Apply Current Style"
  tooltip: "Applies the current style to the selected objects and groups"
  toolbar: null
  menu: "Utilities"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_ApplyStyle"
  wiki_rev: "0499378"
  seed: "e77f5e30807a"
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

The Draft ApplyStyle command applies the current style settings to selected objects. This command handles only five of the settings the Draft SetStyle command offers. This command changes the view properties of objects. It applies all settings the Draft SetStyle command offers. It also changes these additional properties:

- Decimals(for dimensions): See Draft Preferences.

- ShowLine(for dimensions): Idem.

## See also

- Draft_SetStyle
