---
command: "Std_ViewIvIssueCamPos"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Issue Camera &Position"
  tooltip: "Issues the camera position to the console and to a macro, to easily recall this position"
  toolbar: null
  menu: "Stereo"
  shortcut: null
  workbench: null
  wiki: "Std_ViewIvIssueCamPos"
  wiki_rev: "0499378"
  seed: "6205b916c0b5"
# authored from here down; the tool never rewrites these
verb: null
example: issue_camera_position
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Std ViewIvIssueCamPos command prints the camera settings of the active 3D view in the Report view and the Python console.

```python OrthographicCamera { viewportMapping ADJUST_CAMERA position 57.73505 -57.73502 57.735027 orientation 0.74290609 0.30772209 0.59447283 1.2171158 nearDistance 81.588844 farDistance 109.60551 aspectRatio 1 focalDistance 100 height 100 } ``` *Example output: camera settings after changing to isometric view in a new document*

## See also

- Std_FreezeViews
