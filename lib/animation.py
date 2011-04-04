# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gettext import gettext as _
from command import Action, SelectLayer
import layer


class AnimationCel():
    def __init__(self, description=None, drawing=None, is_key=False):
        if description is None:
            description = u""
        self.description = description
        self.drawing = drawing
        self.is_key = is_key
        self.frame_number = None
    
    def __unicode__(self):
        if self.is_key:
            return u"%d. * %s" % (self.frame_number, self.description)
        else:
            return u"%d. %s" % (self.frame_number, self.description)


class SelectCel(Action):
    def __init__(self, doc, idx):
        self.doc = doc
        self.idx = idx
        self.select_layer = None
    
    def redo(self):
        self.prev_value = self.doc.ani.cel_idx
        self.doc.ani.cel_idx = self.idx
        cur_cel = self.doc.ani.cel
        if cur_cel.drawing is not None:
            idx = self.doc.layers.index(cur_cel.drawing)
            self.select_layer = SelectLayer(self.doc, idx)
            self.select_layer.redo()
            for l in self.doc.layers:
                l.opacity = 0.3
                self._notify_canvas_observers(l)
            cur_cel.drawing.opacity = 1.0
            self._notify_canvas_observers(cur_cel.drawing)
        self._notify_document_observers()
    
    def undo(self):
        self.doc.ani.cel_idx = self.prev_value
        cur_cel = self.doc.ani.cel
        if self.select_layer is not None:
            self.select_layer.undo()
        if cur_cel.drawing is not None:
            for l in self.doc.layers:
                l.opacity = 0.3
                self._notify_canvas_observers(l)
            cur_cel.drawing.opacity = 1.0
            self._notify_canvas_observers(cur_cel.drawing)
        self._notify_document_observers()


class ToggleKey(Action):
    def __init__(self, doc, cel):
        self.doc = doc
        self.cel = cel

    def redo(self):
        self.prev_value = self.cel.is_key
        self.cel.is_key = not self.cel.is_key
        self._notify_document_observers()

    def undo(self):
        self.cel.is_key = self.prev_value
        self._notify_document_observers()


class ChangeDescription(Action):
    def __init__(self, doc, cel, new_description):
        self.doc = doc
        self.cel = cel
        self.new_description = new_description

    def redo(self):
        self.prev_value = self.cel.description
        self.cel.description = self.new_description
        self._notify_document_observers()

    def undo(self):
        self.cel.description = self.prev_value
        self._notify_document_observers()


class AddDrawing(Action):
    def __init__(self, doc, cel):
        self.doc = doc
        self.cel = cel
        self.layer = layer.Layer(self.cel.description)
        self.layer.surface.observers.append(self.doc.layer_modified_cb)

    def redo(self):
        self.doc.layers.insert(0, self.layer)
        self.prev_idx = self.doc.layer_idx
        self.doc.layer_idx = 0
        self.prev_value = self.cel.drawing
        self.cel.drawing = self.layer
        self._notify_document_observers()

    def undo(self):
        self.doc.layers.remove(self.layer)
        self.doc.layer_idx = self.prev_idx
        self.cel.drawing = self.prev_value
        self._notify_document_observers()


class Animation():
    """
    """
    
    def __init__(self, doc):
        self.doc = doc
        self.cel_list = []
        self.cel_idx = None
        self._test_mock()
        
    def add_cel(self, cel):
        self.cel_list.append(cel)
        cel.frame_number = len(self.cel_list)
        self.cel_idx = cel.frame_number - 1
    
    def toggle_key(self):
        self.doc.do(ToggleKey(self.doc, self.cel))
    
    def change_description(self, cel, new_description):
        self.doc.do(ChangeDescription(self.doc, cel, new_description))
    
    def add_drawing(self, cel):
        if cel.drawing != None:
            return
        self.doc.do(AddDrawing(self.doc, cel))

    def select_cel(self, idx):
        assert idx >= 0 and idx < len(self.cel_list)
        self.doc.do(SelectCel(self.doc, idx))
    
    def get_current_cel(self):
        return self.cel_list[self.cel_idx]
    cel = property(get_current_cel)
    
    def _test_mock(self):
        for i in range(1, 25):
            self.add_cel(AnimationCel())
        for i in (1, 8, 12, 24):
            self.cel_list[i-1].is_key = True
        
