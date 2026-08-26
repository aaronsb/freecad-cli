---
command: "Draft_WorkingPlaneProxy"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Working Plane Proxy"
  tooltip: "Creates a proxy object from the current working plane that allows to restore the camera position and visibility of objects"
  toolbar: "Draft Utility"
  menu: "Utils"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_WorkingPlaneProxy"
  wiki_rev: "0499378"
  seed: "ac4838b8e6de"
# authored from here down; the tool never rewrites these
verb: null
example: working_plane_proxy
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft WorkingPlaneProxy command creates a working plane proxy to save the current Draft working plane. A working plane proxy can be used to quickly restore a working plane. The camera position and visibility of the objects in the 3D view are also saved in the working plane proxy and can, optionally, be restored as well.

## See also

- Draft_SelectPlane
