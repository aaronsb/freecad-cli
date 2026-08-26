---
command: "Arch_Site"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Site"
  tooltip: "Creates a site including selected objects"
  toolbar: "3D/BIM Tools"
  menu: "3D/BIM"
  shortcut: "S, I"
  workbench: "BIMWorkbench"
  wiki: "Arch_Site"
  wiki_rev: "0499378"
  seed: "c4123dc586f0"
# authored from here down; the tool never rewrites these
verb: null
example: site
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Arch Site is a special object that combines properties of a standard FreeCAD group object and Arch objects. It is particularly suited for representing a whole project site, or terrain. In IFC-based architectural work, it is mostly used to organize your model, by containing building objects. The site is also used to manage and display a physical terrain, and can compute volumes of earth to be added or removed.
