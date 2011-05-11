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
    'current':    1.0,
    'nextprev':   0.5,
    'key':        0.4,
    'inbetweens': 0.2,
    'other keys': 0.3,
    'other':      0,
    }
    
    def __init__(self, doc):
        self.doc = doc
        self.cleared = False
    
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
    
    def _play_penciltest(self, tempdir):
        
        # TODO using external program for now:
        call('blender-2.49b -a -f 24 1 ' + tempdir + '/*png', shell=True)
    
    def penciltest(self, fast=True):
        tempdir = tempfile.mkdtemp(prefix='penciltest')
        idx = self.frames.idx
        
        def select_without_undo(idx):
            "Like the command but without undo/redo"
            self.frames.select(idx)
            opacities = self.frames.get_opacities()
            for cel, opa in opacities.items():
                cel.opacity = opa
                self.doc.call_doc_observers()
        
        def frames_to_png_opacities():
            """
            Saves one png for each frame, with the lightbox on, that
            is, maybe showing other cels transparented.
            
            """
            doc_bbox = self.doc.get_effective_bbox()
            for i in range(len(self.frames)):
                select_without_undo(i)
                prefix = 'cel-' + str(i).zfill(3)
                suffix = '.png'
                tempf = tempfile.mkstemp(suffix, prefix, tempdir)
                pixbufsurface.save_as_png(self.doc, tempf[1],
                                          *doc_bbox, alpha=False)
        
        def frames_to_png():
            """
            Saves one png for each frame.
            
            """
            doc_bbox = self.doc.get_effective_bbox()
            for i in range(len(self.frames)):
                prefix = 'cel-' + str(i).zfill(3)
                suffix = '.png'
                tempf = tempfile.mkstemp(suffix, prefix, tempdir)
                cel = self.frames.cel_at(i)
                cel.surface.save(tempf[1], *doc_bbox)
        
        def frames_to_png2():
            """
            TODO HACK, remove and use the other after finding a
            solution for penciltest playback.

            """
            previous_active_cels = dict(self.frames.active_cels)
            active_cels = {'current': True, 'nextprev': False, 
                           'key': False, 'inbetweens': False,
                           'other keys': False, 'other': False}
            self.frames.setup_active_cels(active_cels)
            doc_bbox = self.doc.get_effective_bbox()
            for i in range(len(self.frames)):
                select_without_undo(i)
                prefix = 'cel-' + str(i).zfill(3)
                suffix = '.png'
                tempf = tempfile.mkstemp(suffix, prefix, tempdir)
                pixbufsurface.save_as_png(self.doc, tempf[1],
                                          *doc_bbox, alpha=False)
            self.frames.setup_active_cels(previous_active_cels)
        
        if fast:
#            frames_to_png()
            frames_to_png2()
        else:
            frames_to_png_opacities()
        
        select_without_undo(idx)
        self._play_penciltest(tempdir)
    
    def get_xsheet_list(self):
        return list(enumerate(self.frames))
    
    def toggle_key(self):
        self.doc.do(anicommand.ToggleKey(self.doc, self.frames))
    
    def previous_frame(self):
        self.doc.do(anicommand.GoToPrevious(self.doc, self.frames))
    
    def next_frame(self):
        self.doc.do(anicommand.GoToNext(self.doc, self.frames))
    
    def change_description(self, new_description):
        self.doc.do(anicommand.ChangeDescription(self.doc, self.frames,
                                                 new_description))
    
    def add_cel(self):
        # TODO remove, the button should not provide this:
        if self.frames.get_selected().cel != None:
            return
        self.doc.do(anicommand.AddCel(self.doc, self.frames))

    def select_frame(self, idx):
        self.doc.do(anicommand.SelectFrame(self.doc, self.frames, idx))
        
    def toggle_opacity(self, attr, is_active):
        self.doc.do(anicommand.ToggleOpacity(self.doc, self.frames,
                                             attr, is_active))
    
