---
command: "FEM_SolverElmer"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Solver Elmer"
  tooltip: "Creates a FEM solver Elmer"
  toolbar: null
  menu: "Solve"
  shortcut: "S, E"
  workbench: "FemWorkbench"
  wiki: "FEM_SolverElmer"
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

Elmer is an open source multiphysical simulation software mainly developed by CSC - IT Center for Science (CSC). Elmer development was started 1995 in collaboration with Finnish Universities, research institutes and industry. After it's open source publication in 2005, the use and development of Elmer has become international.

Elmer includes physical models of fluid dynamics, structural mechanics, electromagnetics, heat transfer and acoustics, for example. These are described by partial differential equations which Elmer solves by the Finite Element Method (FEM).

Creating the SolverElmer object in the Analysis container in FreeCAD, gives access to the Elmer Equations for simple or multiphysical analysis.

Since FreeCAD already has an extensive integration of Calculix and Z88 as solvers for mechanical and thermo-mechanical analysis, Elmer will be preferred for computational fluid dynamics (CFD), heat, electrostatics and electrodynamics. It can also be used for mechanical FEA through the Elasticity equation or any combination of the aforementioned equations. This combination makes Elmer the preferred choice for multi-physics analyses.

## See also

- FEM_SolverElmer_SolverSettings
- FEM_SolverCalculixCxxtools
- FEM_SolverZ88
- FEM_tutorial
