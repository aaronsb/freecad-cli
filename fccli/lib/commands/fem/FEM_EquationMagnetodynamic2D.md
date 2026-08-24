---
command: "FEM_EquationMagnetodynamic2D"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Magnetodynamic 2D Equation"
  tooltip: "Creates an equation for 2D magnetodynamic forces"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_EquationMagnetodynamic2D"
  wiki_rev: "0499378"
  seed: "e44fe40f6972"
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

This equation performs analyses using a 2D version of the Maxwell's equations when the unknown is the z-component (or φ-component).

For info about the math of the equation, see the Elmer models manual, section *Computation of Magnetic Fields in 2D*.

For more general analyses in 3D using the Maxwell's equations FreeCAD supports Elmer's Magnetodynamic equation. Nevertheless, if it is possible to perform the analysis in 2D, this is recommended since the math behind this is then more simple and the calculation time is therefore faster.

## See also

- FEM_EquationMagnetodynamic
