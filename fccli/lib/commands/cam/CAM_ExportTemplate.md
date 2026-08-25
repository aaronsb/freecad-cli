---
command: "CAM_ExportTemplate"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Export Template"
  tooltip: "Exports the CAM job as a template to be used for other jobs"
  toolbar: null
  menu: "CAM"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_ExportTemplate"
  wiki_rev: "0499378"
  seed: "d56e32a25486"
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

The Export Template tool provides a convenient mechanism to save commonly used Job definitions from within an existing Job. This facilitates the setup of future Jobs, that are largely similar, by allowing Job template import during the Job creation process.

The Edit → Preferences... → CAM → Job Preferences → Defaults → Template sets the default template.

## See also

- CAM_SetupSheet
