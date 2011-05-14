# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from command import Action, SelectLayer
import layer


class AniAction(Action):
    def __init__(self, frames):
        self.frames = frames 
    
    def update_opacities(self):
        opacities = self.frames.get_opacities()
        for cel, opa in opacities.items():
            cel.opacity = opa
            self._notify_canvas_observers(cel)
        

class SelectFrame(AniAction):
    def __init__(self, doc, frames, idx):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.idx = idx
        self.select_layer = None
    
    def redo(self):
        cel = self.frames.cel_at(self.idx)
        if cel is not None:
            # Select the corresponding layer:
            layer_idx = self.doc.layers.index(cel)
            self.select_layer = SelectLayer(self.doc, layer_idx)
            self.select_layer.redo()
        
        self.prev_value = self.frames.idx
        self.frames.select(self.idx)
        self.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        if self.select_layer is not None:
            self.select_layer.undo()
        
        self.frames.select(self.prev_value)
        self.update_opacities()
        self._notify_document_observers()


class ToggleKey(AniAction):
    def __init__(self, doc, frames):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.f = self.frames.get_selected()
    
    def redo(self):
        self.prev_value = self.f.is_key
        self.f.toggle_key()
        self.update_opacities()
        self._notify_document_observers()

    def undo(self):
        self.f.is_key = self.prev_value
        self.update_opacities()
        self._notify_document_observers()


class GoToPrevious(AniAction):
    def __init__(self, doc, frames):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.f = self.frames.get_selected()
    
    def redo(self):
        self.frames.goto_previous()
        self.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.frames.goto_next()
        self.update_opacities()
        self._notify_document_observers()


class GoToNext(AniAction):
    def __init__(self, doc, frames):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.f = self.frames.get_selected()
    
    def redo(self):
        self.frames.goto_next()
        self.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.frames.goto_previous()
        self.update_opacities()
        self._notify_document_observers()


class GoToPrevKey(AniAction):
    def __init__(self, doc, frames):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.idx = self.frames.idx
    
    def redo(self):
        self.frames.goto_previous_key()
        self.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.frames.idx = self.idx
        self.update_opacities()
        self._notify_document_observers()


class GoToNextKey(AniAction):
    def __init__(self, doc, frames):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.idx = self.frames.idx
    
    def redo(self):
        self.frames.goto_next_key()
        self.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.frames.idx = self.idx
        self.update_opacities()
        self._notify_document_observers()


class ChangeDescription(AniAction):
    def __init__(self, doc, frames, new_description):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.f = self.frames.get_selected()
        self.new_description = new_description

    def redo(self):
        self.prev_value = self.f.description
        self.f.description = self.new_description
        self._notify_document_observers()

    def undo(self):
        self.f.description = self.prev_value
        self._notify_document_observers()


class AddCel(AniAction):
    def __init__(self, doc, frames):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.f = self.frames.get_selected()
        self.layer = layer.Layer(self.f.description)
        self.layer.surface.observers.append(self.doc.layer_modified_cb)
    
    def redo(self):
        self.doc.layers.insert(0, self.layer)
        self.prev_idx = self.doc.layer_idx
        self.doc.layer_idx = 0
        
        self.f.add_cel(self.layer)
        self.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.doc.layers.remove(self.layer)
        self.doc.layer_idx = self.prev_idx
        self.f.remove_cel()
        self.update_opacities()
        self._notify_document_observers()


class RemoveCel(AniAction):
    def __init__(self, doc, frames):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.f = self.frames.get_selected()
        self.layer = self.f.cel
    
    def redo(self):
        self.doc.layers.remove(self.layer)
        self.prev_idx = self.doc.layer_idx
        self.doc.layer_idx = 0
        
        self.f.remove_cel()
        self.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.doc.layers.insert(0, self.layer)
        self.doc.layer_idx = self.prev_idx

        self.f.add_cel(self.layer)
        self.update_opacities()
        self._notify_document_observers()


class ToggleOpacity(AniAction):
    def __init__(self, doc, frames, attr, is_active):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.attr = attr
        self.is_active = is_active
        self.prev_value = not is_active
    
    def redo(self):
        self.frames.setup_active_cels({self.attr: self.is_active})
        self.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.frames.setup_active_cels({self.attr: self.prev_value})
        self.update_opacities()
        self._notify_document_observers()


class AppendFrames(AniAction):
    def __init__(self, doc, frames, length):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.length = length

    def redo(self):
        self.frames.append_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()

    def undo(self):
        self.frames.pop_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()


class InsertFrames(AniAction):
    def __init__(self, doc, frames, length):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.idx = frames.idx
        self.length = length

    def redo(self):
        self.frames.insert_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()

    def undo(self):
        self.frames.pop_frames(self.length, at_current=True)
        self.doc.ani.cleared = True
        self._notify_document_observers()


class PopFrames(AniAction):
    def __init__(self, doc, frames, length):
        AniAction.__init__(self, frames)
        self.doc = doc
        self.idx = frames.idx
        self.length = length
        self.layers_to_remove = self.frames.cels_to_pop(self.length,
                                                        at_current=True)
    
    def redo(self):
        self.frames.pop_frames(self.length, at_current=True)
        for layer in self.layers_to_remove:
            self.doc.layers.remove(layer)
            
        self.doc.ani.cleared = True
        self._notify_document_observers()

    def undo(self):
        self.frames.insert_frames(self.length)
        for layer in self.layers_to_remove:
            self.doc.layers.insert(0, layer)
        
        self.doc.ani.cleared = True
        self._notify_document_observers()
