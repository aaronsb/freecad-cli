---
command: "Part_Defeaturing"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Defeaturing"
  tooltip: "Removes the selected features from a shape"
  toolbar: "Boolean Tools"
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Defeaturing"
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

The Defeaturing tool is intended for removal of selected features from the model. In this context, features are meant as holes, protrusions, gaps, chamfers, fillets etc. found on the model.

The defeaturing tool can be very useful in different contexts:

- To edit an imported solid where no history of operations is available.
- Fixing defects in the model, e.g. filling gaps, holes etc.
- Model simplification for numeric analysis, display on mobile devices, etc.

The removed features are filled by the extension of the adjacent faces, thus no unexpected parts should appear in the result. Please note that the result is a new shape that is not linked to the original; thus, it is non-parametric.

To be available, this tool requires FreeCAD to be based on Open Cascade 7.3.0 or greater. If it is not available in your version of FreeCAD, you may have a look at the Defeaturing Workbench add-on, which proposes similar functionality even with older versions of OCC or FreeCAD.

## See also

- Defeaturing_Workbench
- Macro_Parametric_Defeaturing
