# -*- coding: utf-8 -*-
#
# This file is part of MyPaint.
# Copyright (C) 2007-2010 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import gtk
from gettext import gettext as _

class Animation(object):
    def __init__(self, doc):
        self.doc = doc

    def get_init_actions(self):
        # name, stock id, label, accelerator, tooltip, callback
        actions = [
            ('PrevFrame', gtk.STOCK_GO_UP, _('Previous Frame'), 'Up', None, self.previous_frame_cb),
            ('NextFrame', gtk.STOCK_GO_DOWN, _('Next Frame'), 'Down', None, self.next_frame_cb),
            ('AddCel', gtk.STOCK_ADD, _('Add cel to this frame'), 'c', None, self.add_cel_cb),
        ]
        return actions

    def previous_frame_cb(self, action):
        if self.doc.model.ani.frames.has_previous():
            self.doc.model.ani.previous_frame()
    
    def next_frame_cb(self, action):
        if self.doc.model.ani.frames.has_next():
            self.doc.model.ani.next_frame()

    def add_cel_cb(self, action):
        self.doc.model.ani.add_cel()
