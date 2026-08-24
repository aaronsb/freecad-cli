# SPDX-License-Identifier: LGPL-2.1-or-later

"""A rubber band from the last point to the cursor.

A point getter that shows nothing between clicks makes placing a polyline
feel like typing with the monitor off. Rhino draws from the last point to
the cursor at frame rate, and most of what makes placing feel direct is
that line.

This deliberately does not go through the message bus. The bus carries
roles that a dock renders in Qt colours and a terminal renders in ANSI, and
it crosses a socket; a scene update that happens on every mouse move has no
business on it, and a terminal has nothing to do with the answer. The
widget and the tracker are peers, both fed by the engine through the
picker.

The node is an SoAnnotation so it draws over the model rather than
z-fighting with it, and carries SoPickStyle UNPICKABLE so the line the
operator is drawing cannot be the thing they snap to.
"""


class RubberBand:
    """One dashed line, owned by the picker that draws it."""

    # Draft's own construction colour, so this reads as the same kind of
    # thing as the snap markers already on screen.
    COLOR = (1.0, 0.9, 0.3)
    PATTERN = 0xF0F0        # dashed, like a dimension witness line
    WIDTH = 1.5

    def __init__(self):
        self.node = None
        self._coords = None
        self._view = None

    def attach(self, view):
        """Put the line in the view's scene graph. Idempotent."""
        if self.node is not None or view is None:
            return False
        try:
            from pivy import coin
        except Exception:
            return False
        try:
            root = view.getSceneGraph()
            node = coin.SoAnnotation()

            pick = coin.SoPickStyle()
            pick.style = coin.SoPickStyle.UNPICKABLE
            node.addChild(pick)

            colour = coin.SoBaseColor()
            colour.rgb = self.COLOR
            node.addChild(colour)

            style = coin.SoDrawStyle()
            style.lineWidth = self.WIDTH
            style.linePattern = self.PATTERN
            node.addChild(style)

            coords = coin.SoCoordinate3()
            coords.point.setValues(0, 2, [(0, 0, 0), (0, 0, 0)])
            node.addChild(coords)

            line = coin.SoLineSet()
            line.numVertices.setValue(2)
            node.addChild(line)

            root.addChild(node)
            self.node, self._coords, self._view = node, coords, view
            return True
        except Exception:
            self.node = self._coords = self._view = None
            return False

    def update(self, start, end):
        """Move the line. Called on every mouse move, so it stays cheap."""
        if self._coords is None or start is None or end is None:
            return False
        try:
            self._coords.point.setValues(
                0, 2, [(start.x, start.y, start.z), (end.x, end.y, end.z)])
            return True
        except Exception:
            return False

    def detach(self):
        """Take the line out again. Safe to call when never attached."""
        node, view = self.node, self._view
        self.node = self._coords = self._view = None
        if node is None or view is None:
            return False
        try:
            view.getSceneGraph().removeChild(node)
            return True
        except Exception:
            return False

    @property
    def attached(self):
        return self.node is not None
