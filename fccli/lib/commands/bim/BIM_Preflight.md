---
command: "BIM_Preflight"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Preflight Checks"
  tooltip: "Checks several characteristics of this model before exporting to IFC"
  toolbar: "Manage Tools"
  menu: "Manage"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_Preflight"
  wiki_rev: "0499378"
  seed: "47aeb2e2c260"
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

The BIM Preflight tool allows you to perform several tests on your model to verify its compatibility with IFC standards and best practices, and help you to detect possible issues you might want to fix.

As FreeCAD is a very loose and free-style modelling platform, the requirements are very low. You can basically model and organize your BIM model the way you like, using all the tools that FreeCAD offers, both from the BIM workbench and other workbenches. The IFC format, however, has some strict requirements, and other BIM applications that can read IFC files often bring additional limitations as they more than often have difficulties with certain entities or the way certain objects are modeled.

The results of most of the tests provided by this tool are optional, which means you can choose to export your model even if they fail. You are the one to assess if you need the test to pass or not. We tried our best to give sound information to help you decide.
