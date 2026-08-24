---
command: "Std_PythonHelp"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Python &Modules Documentation"
  tooltip: "Opens the Python Modules documentation"
  toolbar: null
  menu: "Help"
  shortcut: null
  workbench: null
  wiki: "Std_PythonHelp"
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

The Std PythonHelp command starts a web server that communicates with the system's default Internet browser over a local socket. The web server displays information about the available Python modules, classes and functions of FreeCAD. The required pages are generated automatically.

The web server is based on Python's pydoc module, and thus extracts the docstrings of Python files (*.py), and textual documentation defined in the Python wrappers (*.xml) which expose the underlying C++ code.

## See also

- Std_FreeCADPowerUserHub
