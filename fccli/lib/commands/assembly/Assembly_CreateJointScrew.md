---
command: "Assembly_CreateJointScrew"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Screw Joint"
  tooltip: "Creates a screw joint that links a part with a sliding joint to a part with a revolute jointSelect the same coordinate systems as the revolute and sliding joints. The pitch radius defines the movement ratio between the rotating screw and the sliding part."
  toolbar: "Assembly Joints"
  menu: "Assembly"
  shortcut: "W"
  workbench: "AssemblyWorkbench"
  wiki: "Assembly_CreateJointScrew"
  wiki_rev: "0499378"
  seed: "6f0fb804fbab"
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

The Assembly CreateJointScrew tool creates a screw joint (helical joint) that couples the translation of a part of a slider joint and the rotation of a part of a revolute joint. In connection with the already existing joints this joint can be used to simulate a lead screw gear.
