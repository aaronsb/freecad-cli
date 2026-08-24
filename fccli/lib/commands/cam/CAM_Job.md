---
command: "CAM_Job"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "New Job"
  tooltip: "Creates a CAM job"
  toolbar: "Project Setup"
  menu: "CAM"
  shortcut: "P, J"
  workbench: "CAMWorkbench"
  wiki: "CAM_Job"
  wiki_rev: "0499378"
  seed: "b58a5c61fb84"
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

The Job tool creates a new Job object in the active document. The Job object contains the following information:

1. A list of Tool-Controller definitions, specifying the geometry, Feeds, and Speeds for the Path Operations Tools.
2. A Workflow sequential list of Path Operations.
3. A Base Body---a clone used for offset.
4. A Stock, representing the raw material that will be milled to CAM Workbench.
5. A SetupSheet, containing inputs used by the Path Operations, including static values and formulas.
6. Configuration parameters specifying the output G-Code job's destination path, file name, and extension, and the postprocessor (used to generate the appropriate dialect for the target CNC Controller, and customize Units, Tool Changes, Parking, etc.).

## See also

- CAM_Post
- CAM_Postprocessor_Customization
