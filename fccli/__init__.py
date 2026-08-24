# SPDX-License-Identifier: LGPL-2.1-or-later

"""FreeCAD CLI -- a command line for FreeCAD.

The version here is the single source of truth. package.xml carries a copy
because FreeCAD's Addon Manager reads it there; ``make version-check`` keeps
the two honest, and ``make bump`` writes both.
"""

__version__ = "0.2.0"
__version_info__ = tuple(int(p) for p in __version__.split("."))
