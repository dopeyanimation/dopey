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
        self.frames = FrameList(24, self.opacities)
        self._test_mock()
    
    def save_xsheet(self, filename):
        root, ext = os.path.splitext(filename)
        xsheet_fn = root + '.xsheet'
        xsheetfile = open(xsheet_fn, 'w')
        anistorage.save(self.frames, xsheetfile)
    
    def load_xsheet(self, filename):
        root, ext = os.path.splitext(filename)
        xsheet_fn = root + '.xsheet'
        try:
            xsheetfile = open(xsheet_fn, 'r')
        except IOError:
            # TODO new X Sheet
            pass
        anistorage.load(self.frames, xsheetfile)
    
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
    
    def _test_mock(self):
        for i in (1, 8, 12, 24):
            self.frames[i-1].set_key()
        
