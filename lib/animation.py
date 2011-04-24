# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from gettext import gettext as _

import anicommand
import anistorage
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
    """
    """
    
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
    
    def save_xsheet(self, filename):
        root, ext = os.path.splitext(filename)
        xsheet_fn = root + '.xsheet'
        xsheetfile = open(xsheet_fn, 'w')
        anistorage.save(self.frames, xsheetfile, self.doc)
    
    def load_xsheet(self, filename):
        root, ext = os.path.splitext(filename)
        xsheet_fn = root + '.xsheet'
        try:
            xsheetfile = open(xsheet_fn, 'r')
        except IOError:
            self.clear_xsheet()
        else:
            anistorage.load(self.frames, xsheetfile, self.doc)
    
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
        
