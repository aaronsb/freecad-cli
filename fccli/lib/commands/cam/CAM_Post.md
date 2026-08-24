---
command: "CAM_Post"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Post Process"
  tooltip: "Post Processes the selected job"
  toolbar: "Project Setup"
  menu: "CAM"
  shortcut: "P, P"
  workbench: "CAMWorkbench"
  wiki: "CAM_Post"
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

The tool Post exports the selected CAM Job to a G-code file.

Each CNC Controller speaks a specific G-code dialect, requiring a Dialect-correct Postprocessor to translate the final output from the agnostic internal FreeCAD G-code dialect.

### Typical functions of the Postprocessor include

- Using a correct Job output G-code file extension. - Selecting the G-code commands. CNC controllers typically support a subset of available G-code commands. The super-set of G-code commands contains powerful and specialized commands that otherwise must be processed using multiple simpler commands. Postprocessors are written to select the best G-code for an Operation, available on the target. - Formatting the G-code syntax by reordering the Feed, X, Y, Z, A, and B inputs, and the precision. - Inserting a Pre-amble to set units, units format, Work plane, coordinate system, etc\... - Inserting a Post-amble to park the machine, stop it, process any arguments. - Inserting Tool changes, or suppressing them between subsequent operations using the same tool. - Formatting the Feed and Speed rate information to revolutions per minute, or per second. - Formatting Function Call Naming and Calling.

### Postprocessor Customization

If you want to write your own postprocessor, have a look at the CAM Postprocessor Customization page.

Note: Several provided Postprocessors generate suitable code for many CNC controllers, or can be used as templates for modification

Postprocessors contain configuration flags and are designed to be tuned by adding G-codes and M-codes to provided definitions for:

- Machine initialization - Job finalization - Tool-Changes - Cooling on /off - Etc\...

Postprocessors use FreeCAD\'s internal G-code dialect in conjunction with the Postprocessor configuration definitions, to generate Dialect-Correct G-code for target machines. This allows the CAM workbench to generate correct G-code to target various CNC machine controllers by invoking different Postprocessors.

CNC Machine Controller types include:

- CNC mills - CNC lathes - 3D Printers - DragKnife Cutters - Laser Cutters - Engravers - Plasma Torch Cutters - Wire Benders - EDM Cutters - Etc\...

If only one CNC machine is used, or if all CNC machines share a common Postprocesor, the CAM workbench would need to include only a single Postprocessor. If a single Postprocessor is inadequate to output G-code for all target CNC controllers, then multiple Postprocessors must be installed.
