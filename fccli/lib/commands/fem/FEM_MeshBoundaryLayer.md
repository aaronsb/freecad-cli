---
command: "FEM_MeshBoundaryLayer"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Mesh Boundary Layer"
  tooltip: "Creates a mesh boundary layer"
  toolbar: "Mesh"
  menu: "Mesh"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_MeshBoundaryLayer"
  wiki_rev: "0499378"
  seed: "9f57e06de852"
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

The FEM MeshBoundaryLayer command enables the user to set a localized set of meshing parameters by selecting a set of elements (Vertex, Edge, Face) and applying the parameters to it.

It is especially useful for refining meshes close to edges or surfaces in flow simulations. For example, it can be used to refine the mesh in the vicinity of an air foil or obstacle in a flow.

The boundary layer has the advantage of creating highly defined, anisotropic meshes. As the name implies it supports accurate calculations near boundaries, e.g. a wall where friction occurs, generating a velocity gradient.

## See also

- FEM_tutorial
