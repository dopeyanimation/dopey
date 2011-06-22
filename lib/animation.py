# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from gettext import gettext as _
import json
import tempfile
from subprocess import call

import pixbufsurface

import anicommand
from framelist import FrameList

class AnimationCel(object):
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


class Animation(object):
    
    opacities = {
    'nextprev':   0.5,
    'key':        0.4,
    'inbetweens': 0.2,
    'other keys': 0.3,
    'other':      0,
    }
    
    def __init__(self, doc):
        self.doc = doc
        self.cleared = False
        self.penciltest_state = None

        # For cut/copy/paste operations:
        self.edit_operation = None
        self.edit_frame = None

    def clear_xsheet(self, init=False):
        self.frames = FrameList(24, self.opacities)
        self.cleared = True
    
    def _write_xsheet(self, xsheetfile):
        """
        Save FrameList to file.
        
        """
        data = []
        for f in self.frames:
            if f.cel is not None:
                layer_idx = self.doc.layers.index(f.cel)
            else:
                layer_idx = None
            data.append((f.is_key, f.description, layer_idx))
        str_data = json.dumps(data, sort_keys=True, indent=4)
        xsheetfile.write(str_data)

    def _read_xsheet(self, xsheetfile):
        """
        Update FrameList from file.
    
        """
        str_data = xsheetfile.read()
        data = json.loads(str_data)
        self.frames = FrameList(len(data), self.opacities)
        self.cleared = True
        for i, d in enumerate(data):
            is_key, description, layer_idx = d
            if layer_idx is not None:
                cel = self.doc.layers[layer_idx]
            else:
                cel = None
            self.frames[i].is_key = is_key
            self.frames[i].description = description
            self.frames[i].cel = cel
    
    def save_xsheet(self, filename):
        root, ext = os.path.splitext(filename)
        xsheet_fn = root + '.xsheet'
        xsheetfile = open(xsheet_fn, 'w')
        self._write_xsheet(xsheetfile)
    
    def load_xsheet(self, filename):
        root, ext = os.path.splitext(filename)
        xsheet_fn = root + '.xsheet'
        try:
            xsheetfile = open(xsheet_fn, 'r')
        except IOError:
            self.clear_xsheet()
        else:
            self._read_xsheet(xsheetfile)
    
    def save_png(self, filename, **kwargs):
        prefix, ext = os.path.splitext(filename)
        # if we have a number already, strip it
        l = prefix.rsplit('-', 1)
        if l[-1].isdigit():
            prefix = l[0]
        doc_bbox = self.doc.get_effective_bbox()
        for i in range(len(self.frames)):
            filename = '%s-%03d%s' % (prefix, i+1, ext)
            cel = self.frames.cel_at(i)
            cel.surface.save(filename, *doc_bbox, **kwargs)
    
    def _notify_canvas_observers(self, affected_layer):
        bbox = affected_layer.surface.get_bbox()
        for f in self.doc.canvas_observers:
            f(*bbox)

    def update_opacities(self):
        opacities, visible = self.frames.get_opacities()

        for cel, opa in opacities.items():
            cel.opacity = opa
            self._notify_canvas_observers(cel)

        for cel, vis in visible.items():
            cel.visible = vis
            self._notify_canvas_observers(cel)

    def select_without_undo(self, idx):
        """Like the command but without undo/redo."""
        self.frames.select(idx)
        self.update_opacities()

    def play_penciltest(self):
        self.penciltest_state = "play"
        self.doc.call_doc_observers()

    def pause_penciltest(self):
        self.penciltest_state = "pause"

    def playpause_penciltest(self):
        if self.penciltest_state != "play":
            self.penciltest_state = "play"
        else:
            self.penciltest_state = "pause"
        self.doc.call_doc_observers()

    def stop_penciltest(self):
        self.penciltest_state = "stop"

    def penciltest_next(self):
        if self.frames.has_next():
            self.frames.goto_next()
        else:
            self.frames.select(0)
        self.update_opacities()
    
    def toggle_key(self):
        frame = self.frames.get_selected()
        self.doc.do(anicommand.ToggleKey(self.doc, frame))
    
    def previous_frame(self):
        self.frames.goto_previous()
        self.update_opacities()
        self.doc.call_doc_observers()
    
    def next_frame(self):
        self.frames.goto_next()
        self.update_opacities()
        self.doc.call_doc_observers()

    def previous_keyframe(self):
        self.frames.goto_previous_key()
        self.update_opacities()
        self.doc.call_doc_observers()

    def next_keyframe(self):
        self.frames.goto_next_key()
        self.update_opacities()
        self.doc.call_doc_observers()
    
    def change_description(self, new_description):
        frame = self.frames.get_selected()
        self.doc.do(anicommand.ChangeDescription(self.doc, frame, new_description))
    
    def add_cel(self):
        frame = self.frames.get_selected()
        if frame.cel is not None:
            return
        self.doc.do(anicommand.AddCel(self.doc, frame))

    def remove_cel(self):
        frame = self.frames.get_selected()
        if frame.cel is None:
            return
        self.doc.do(anicommand.RemoveCel(self.doc, frame))

    def select_frame(self, idx):
        self.doc.do(anicommand.SelectFrame(self.doc, idx))

    def change_opacityfactor(self, opacityfactor):
        self.frames.set_opacityfactor(opacityfactor)
        self.update_opacities()

    def toggle_opacity(self, attr, is_active):
        self.frames.setup_active_cels({attr: is_active})
        self.update_opacities()
    
    def insert_frames(self):
        self.doc.do(anicommand.InsertFrames(self.doc, 1))

    def remove_frames(self):
        self.doc.do(anicommand.RemoveFrames(self.doc, 1))

    def cutcopy_cel(self, edit_operation):
        frame = self.frames.get_selected()
        self.doc.ani.edit_operation = edit_operation
        self.doc.ani.edit_frame = frame
        self.doc.call_doc_observers()

    def paste_cel(self):
        frame = self.frames.get_selected()
        self.doc.do(anicommand.PasteCel(self.doc, frame))
