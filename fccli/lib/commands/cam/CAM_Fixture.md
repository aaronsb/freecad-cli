---
command: "CAM_Fixture"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Fixture"
  tooltip: "Creates a fixture offset"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_Fixture"
  wiki_rev: "0499378"
  seed: "f072aa10416a"
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

The tool Fixture sets the Work Offset Coordinate Fixture of the machine CNC controller.

Target Work Offset Coordinates typically include: Fixtures G53 to G59. The G-code is simply the Fixture (G53, G54, etc...). The coordinate offset fixtures represent:

- G53 → Machine coordinate system.
- G54 → Scratchpad coordinate system.
- G55 to G59.9 → Coordinate fixtures allowing work offsets, relative to Homing switches located on the CNC machine, to be used.

The G59 Fixture is used to expand available fixtures. The degree of expansion implemented is CNC machine specific, and this command allows provides for G59.1 to G59.9.
