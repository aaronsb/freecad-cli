# SPDX-License-Identifier: LGPL-2.1-or-later

"""Unsaved-changes tracking.

FreeCAD exposes no unsaved-changes flag to Python. ``Document.isSaved()``
reports whether the document has a file at all and stays true after every
later edit, and the GUI's modified flag is C++ only.

``App.addDocumentObserver`` is the way in. It reports object changes,
creations, deletions and saves regardless of where they came from -- the
command line, a toolbar click, a macro, or a script -- so the flag is
accurate for the whole application rather than only for what this addon did.

Recompute noise is filtered out: Shape and the underscore-prefixed internals
change every time anything recomputes, including on open, which would mark a
freshly opened document dirty before anyone touched it.
"""

import FreeCAD as App

# Properties that change as a consequence of other changes.
DERIVED = {"Shape", "AttachmentSupport", "_ElementMapVersion"}


class DirtyTracker:
    """Document names with unsaved changes."""

    def __init__(self):
        self.names = set()
        self._installed = False

    # ----------------------------------------------------------- queries

    def is_dirty(self, doc=None):
        doc = doc if doc is not None else App.ActiveDocument
        return doc is not None and doc.Name in self.names

    def mark(self, doc):
        if doc is not None:
            self.names.add(getattr(doc, "Name", doc))

    def clear(self, doc=None, name=None):
        if name is None:
            if doc is None:
                doc = App.ActiveDocument
            if doc is None:
                return
            name = getattr(doc, "Name", doc)
        self.names.discard(name)

    def dirty_documents(self):
        return sorted(n for n in App.listDocuments() if n in self.names)

    # --------------------------------------------------- observer slots

    def slotChangedObject(self, obj, prop):
        if prop.startswith("_") or prop in DERIVED:
            return
        self.mark(getattr(obj, "Document", None))

    def slotCreatedObject(self, obj):
        self.mark(getattr(obj, "Document", None))

    def slotDeletedObject(self, obj):
        self.mark(getattr(obj, "Document", None))

    def slotRelabelObject(self, obj):
        self.mark(getattr(obj, "Document", None))

    def slotUndoDocument(self, doc):
        self.mark(doc)

    def slotRedoDocument(self, doc):
        self.mark(doc)

    def slotCreatedDocument(self, doc):
        self.clear(doc)

    def slotFinishSaveDocument(self, doc, path=None):
        self.clear(doc)

    def slotDeletedDocument(self, doc):
        self.clear(doc)

    # ------------------------------------------------------------ wiring

    def install(self):
        if self._installed:
            return True
        try:
            App.addDocumentObserver(self)
            self._installed = True
        except Exception as exc:
            App.Console.PrintWarning(f"[fccli] dirty tracking: {exc}\n")
        return self._installed

    def remove(self):
        if not self._installed:
            return
        try:
            App.removeDocumentObserver(self)
        except Exception:
            pass
        self._installed = False


TRACKER = DirtyTracker()


def install():
    return TRACKER.install()


def is_dirty(doc=None):
    return TRACKER.is_dirty(doc)


def mark_dirty(doc=None):
    TRACKER.mark(doc if doc is not None else App.ActiveDocument)


def mark_clean(doc=None, name=None):
    TRACKER.clear(doc, name)


def dirty_documents():
    return TRACKER.dirty_documents()
