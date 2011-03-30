# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gettext import gettext as _


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


class Animation():
    """
    """
    
    def __init__(self):
        self.cel_list = []
        self.cel_idx = None
        self._test_mock()
        
    def add_cel(self, cel):
        self.cel_list.append(cel)
        cel.frame_number = len(self.cel_list)
        self.cel_idx = cel.frame_number - 1
    
    def toggle_key(self, cel):
        print unicode(cel)
    
    def get_current_cel(self):
        return self.cel_list[self.cel_idx]
    
    def _test_mock(self):
        for i in range(1, 25):
            self.add_cel(AnimationCel())
        for i in (1, 8, 12, 24):
            self.cel_list[i-1].is_key = True
        
