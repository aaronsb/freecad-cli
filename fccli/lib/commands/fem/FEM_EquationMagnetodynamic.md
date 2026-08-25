---
command: "FEM_EquationMagnetodynamic"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Magnetodynamic Equation"
  tooltip: "Creates an equation for magnetodynamic forces"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_EquationMagnetodynamic"
  wiki_rev: "0499378"
  seed: "cd3416b24121"
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

This equation perform analyses using the Maxwell's equations.

For info about the math of the equation, see the Elmer models manual, section *Computation of Magnetic Fields in 3D*.

If it is possible to calculate in 2D, simpler math can be used resulting in faster solving times. For 2D, FreeCAD supports therefore Elmer's Magnetodynamic 2D equation.

## See also

- FEM_EquationMagnetodynamic2D
