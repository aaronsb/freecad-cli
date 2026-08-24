---
command: "CAM_Sanity"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Sanity Check"
  tooltip: "Checks the CAM job for common errors"
  toolbar: "Project Setup"
  menu: "CAM"
  shortcut: "P, S"
  workbench: "CAMWorkbench"
  wiki: "CAM_Sanity"
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

Many CAM users are hobbyists and DIYers. As such, they use their CNC machines to run G-code that they configured and generated themselves. That isn\'t the case for most professional/commercial users. In professional shops, different people are responsible for creating the G-code (CNC programmers) from those who run it on the machines (CNC operator).

Hobbyists usually run the G-code just a few minutes after post-processing it and probably only once or twice. In a professional shop, proven G-code may be run many times for months or years after initially generated.

One issue that arises in a professional CNC shop is that there are many assumptions made by the programmer that are NOT communicated in the G-code itself. For example, the G-code can call for a tool \"T3\" but unless its commented, the G-code doesn\'t say what kind of tool \"T3\" refers to. It\'s just assumed that T3 in the CAM system is the same as T3 on the machine. There are many assumptions like this involving machine setup, tooling, material, part orientation, etc. Even if the G-code is perfect, if the operator doesn\'t set up the machine with the same assumptions, it can crash.

Commercial shops will often create a \'setup book\' which documents all these assumptions and gives the operators what they need to configure the machine and produce a part.

CAM Sanity is the tool in CAM workbench to generate this kind of information. The output of this command is a stand-alone .html file with embedded images.
