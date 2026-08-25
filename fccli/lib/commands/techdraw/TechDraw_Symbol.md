---
command: "TechDraw_Symbol"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Insert SVG"
  tooltip: "Inserts a symbol from an SVG file"
  toolbar: null
  menu: "TechDraw Views"
  shortcut: null
  workbench: "TechDrawWorkbench"
  wiki: "TechDraw_Symbol"
  wiki_rev: "0499378"
  seed: "dd6b803acfa6"
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

The TechDraw Symbol tool inserts a Symbol object. A Symbol is a stripped down view that contains only a single SVG file complying with the svg-tiny specification (see TechDraw Templates).

A Symbol can be anything that helps annotate a drawing and that doesn't need to be further modified, it may however contain editable texts. The TechDraw View tool can also create a Symbol.

## See also

- TechDraw_Templates
- Draft_SVG
