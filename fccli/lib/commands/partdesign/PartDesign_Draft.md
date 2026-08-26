---
command: "PartDesign_Draft"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Draft"
  tooltip: "Applies a draft to the selected faces"
  toolbar: "Part Design Dress-Up Features"
  menu: "Dress-Up Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Draft"
  wiki_rev: "0499378"
  seed: "37018c71fa00"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type:
  of: PartDesign::Draft
  doc: Taper the selected faces away from a neutral plane.
  hide: [FuzzyTolerance]
---

The PartDesign Draft tool creates angular draft on the selected faces of an object. It adds a Draft object to the document with its corresponding representation in the Tree view.

--

--
