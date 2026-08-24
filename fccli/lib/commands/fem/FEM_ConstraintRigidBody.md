---
command: "FEM_ConstraintRigidBody"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Rigid Body Constraint"
  tooltip: "Creates a rigid body constraint for a geometric entity"
  toolbar: "Mechanical Boundary Conditions and Loads"
  menu: "Mechanical Boundary Conditions and Loads"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_ConstraintRigidBody"
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

Defines the CalculiX's rigid body constraint that constrains the motion of the nodes of a selected geometrical entity to the motion of a reference node whose location is defined by the user. In practice, this can be used to apply a boundary condition or load that will be propagated to the selected object. Since the reference node has rotational degrees of freedom, it's possible to apply a moment load or a rotational boundary condition to any face this way. The location of the reference node can be selected, if it's offset from a geometrical entity, a remote load (a force acting on a lever) can be applied.

## See also

- FEM_ConstraintDisplacement
