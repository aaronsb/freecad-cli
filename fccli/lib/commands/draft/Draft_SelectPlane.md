---
command: "Draft_SelectPlane"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Working Plane"
  tooltip: "Defines the working plane from 3 vertices, 1 or more shapes, or an object"
  toolbar: null
  menu: "Snapping"
  shortcut: "W, P"
  workbench: "DraftWorkbench"
  wiki: "Draft_SelectPlane"
  wiki_rev: "0499378"
  seed: "07cd7a7da602"
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

The Draft SelectPlane command defines the current Draft working plane. This is the plane in the 3D view where new Draft objects are created. A working plane can be based on one of several presets or on a selection. The selection can be created before (pre-selection) or after (post-selection) starting the command. For each 3D view a separate working plane is stored.

The button in the Draft Tray changes depending on the current working plane. If the working plane is not set to Auto an asterisk (*) is appended to the button label if the origin of the working plane does not match the global origin.

## See also

- Draft_WorkingPlaneProxy
