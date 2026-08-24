---
command: "CAM_SimulatorGL"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "CAM Simulator"
  tooltip: "Simulates G-code on stock"
  toolbar: null
  menu: "CAM"
  shortcut: "P, N"
  workbench: "CAMWorkbench"
  wiki: "CAM_SimulatorGL"
  wiki_rev: "0499378"
  seed: "4594a528dc13"
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

The SimulatorGL tool is a new alternative to CAM Simulator. It's based on low-level OpenGL functions. To eliminate interference with the 3D view of FreeCAD, it works in a separate window with a separate OpenGL context. It's meant to be faster and more precise than the old simulator.

## See also

- CAM_Simulator
