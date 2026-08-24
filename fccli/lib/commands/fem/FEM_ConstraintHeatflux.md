---
command: "FEM_ConstraintHeatflux"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Heat Flux Load"
  tooltip: "Creates a heat flux load acting on a face"
  toolbar: "Thermal Boundary Conditions and Loads"
  menu: "Thermal Boundary Conditions and Loads"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_ConstraintHeatflux"
  wiki_rev: "0499378"
  seed: "727057c42276"
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

By default, defines a convective heat flux load on a surface at a temperature $T$ with a film coefficient $h$ and with the environment (sink/ambient) temperature $T_{0}$. The convective heat flux $q$ will satisfy: $q=h(T-T_{0})$. Optionally, can also define a regular surface heat flux load. Can be also used to define a radiation heat flux on a surface. It satisfies: $q=\epsilon \sigma(T^{4}-T_{0}^{4})$ where $\epsilon$ is the surface emissivity and $\sigma$ is the Stefan-Boltzmann constant.

## See also

- FEM_tutorial
