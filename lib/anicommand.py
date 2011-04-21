# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from command import Action, SelectLayer
import layer

class SelectFrame(Action):
    def __init__(self, doc, frames, idx):
        self.doc = doc
        self.frames = frames
        self.idx = idx
        self.select_layer = None
    
    def redo(self):
        cel = self.frames.cel_at(self.idx)
        if cel is not None:
            idx = self.doc.layers.index(cel)
            self.select_layer = SelectLayer(self.doc, idx)
            self.select_layer.redo()
        
        self.prev_value = self.frames.idx
        self.frames.select(self.idx)
        opacities = self.frames.get_opacities()
        for cel, opa in opacities.items():
            cel.opacity = opa
            self._notify_canvas_observers(cel)
        self._notify_document_observers()
    
    def undo(self):
        if self.select_layer is not None:
            self.select_layer.undo()
        
        self.frames.select(self.prev_value)
        opacities = self.frames.get_opacities()
        for cel, opa in opacities.items():
            cel.opacity = opa
            self._notify_canvas_observers(cel)
        self._notify_document_observers()


class ToggleKey(Action):
    def __init__(self, doc, frames):
        self.doc = doc
        self.frames = frames
        self.f = self.frames.get_selected()
    
    def redo(self):
        self.prev_value = self.f.is_key
        self.f.toggle_key()
        self._notify_document_observers()

    def undo(self):
        self.f.is_key = self.prev_value
        self._notify_document_observers()


class ChangeDescription(Action):
    def __init__(self, doc, frames, new_description):
        self.doc = doc
        self.frames = frames
        self.f = self.frames.get_selected()
        self.new_description = new_description

    def redo(self):
        self.prev_value = self.f.description
        self.f.description = self.new_description
        self._notify_document_observers()

    def undo(self):
        self.f.description = self.prev_value
        self._notify_document_observers()


class AddCel(Action):
    def __init__(self, doc, frames):
        self.doc = doc
        self.frames = frames
        self.f = self.frames.get_selected()
        self.layer = layer.Layer(self.f.description)
        self.layer.surface.observers.append(self.doc.layer_modified_cb)
    
    def redo(self):
        self.doc.layers.insert(0, self.layer)
        self.prev_idx = self.doc.layer_idx
        self.doc.layer_idx = 0
        
        self.f.add_cel(self.layer)
        self._notify_document_observers()
    
    def undo(self):
        self.doc.layers.remove(self.layer)
        self.doc.layer_idx = self.prev_idx
        self.f.remove_cel()
        self._notify_document_observers()
