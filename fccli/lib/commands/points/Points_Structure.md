---
command: "Points_Structure"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Structured Point Cloud"
  tooltip: "Converts points to a structured point cloud"
  toolbar: "Points Tools"
  menu: "Points"
  shortcut: null
  workbench: "PointsWorkbench"
  wiki: "Points_Structure"
  wiki_rev: "0499378"
  seed: "850b0fa6f6c1"
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

The Points Structure command creates a structured point cloud from the points of an existing scattered point cloud. A structured point cloud has the advantage that tessellation is much easier.

The command only works for point clouds whose points, when viewed from a certain direction, are organized in a regular 2D grid. These point clouds are typically produced by structured-light 3D scanners and do not have undercuts. For complex objects, point clouds from many different view directions have to be combined.
