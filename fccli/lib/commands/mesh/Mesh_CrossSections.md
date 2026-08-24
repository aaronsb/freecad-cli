---
command: "Mesh_CrossSections"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Cross-Sections"
  tooltip: "Creates cross-sections of the mesh"
  toolbar: "Mesh Cutting"
  menu: "Cutting"
  shortcut: null
  workbench: "MeshWorkbench"
  wiki: null
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

The Mesh CrossSections command creates multiple cross sections across mesh objects. The cross sections are taken parallel to one of the main global planes (XY, XZ or YZ). For each set of cross sections a single Part Feature is created.

## See also

- Mesh_SectionByPlane
