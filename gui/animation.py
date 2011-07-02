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
        self.model = doc.model.ani
    
    def get_init_actions(self):
        # name, stock id, label, accelerator, tooltip, callback
        actions = [
            ('PrevFrame', gtk.STOCK_GO_UP, _('Previous Frame'), 'Up', None, self.previous_frame_cb),
            ('NextFrame', gtk.STOCK_GO_DOWN, _('Next Frame'), 'Down', None, self.next_frame_cb),
            ('PrevFrameWithCel', None, _('Previous frame with cel'), '<control>Up', None, self.previous_celframe_cb),
            ('NextFrameWithCel', None, _('Next frame with cel'), '<control>Down', None, self.next_celframe_cb),
            ('PrevKeyFrame', None, _('Previous Keyframe'), '<shift>Up', None, self.previous_keyframe_cb),
            ('NextKeyFrame', None, _('Next Keyframe'), '<shift>Down', None, self.next_keyframe_cb),
            ('PlayPauseAnimation', None, _('Play/Pause animation'), '<control>p', None, self.playpause_animation_cb),
            ('StopAnimation', None, _('Stop animation'), None, None, self.stop_animation_cb),
            ('AddCel', gtk.STOCK_ADD, _('Add cel to this frame'), 'c', None, self.add_cel_cb),
            ('ToggleKey', gtk.STOCK_JUMP_TO, _('Toggle Keyframe'), 'k', None, self.toggle_key_cb),
            ('InsertFrame', gtk.STOCK_ADD, _('Insert frame'), None, None, self.insert_frame_cb),
            ('RemoveFrame', gtk.STOCK_REMOVE, _('Remove frame'), None, None, self.remove_frame_cb),
            ('CutCel', gtk.STOCK_REMOVE, _('Cut cel at frame'), None, None, self.cut_cel_cb),
            ('CopyCel', gtk.STOCK_REMOVE, _('Copy cel at frame'), None, None, self.copy_cel_cb),
            ('PasteCel', gtk.STOCK_REMOVE, _('Paste cel at frame'), None, None, self.paste_cel_cb),
        ]
        return actions

    def previous_frame_cb(self, action):
        if self.model.frames.has_previous():
            self.model.previous_frame()
    
    def next_frame_cb(self, action):
        if self.model.frames.has_next():
            self.model.next_frame()

    def previous_celframe_cb(self, action):
        if self.model.frames.has_previous(with_cel=True):
            self.model.previous_frame(with_cel=True)

    def next_celframe_cb(self, action):
        if self.model.frames.has_next(with_cel=True):
            self.model.next_frame(with_cel=True)

    def previous_keyframe_cb(self, action):
        if self.model.frames.has_previous_key():
            self.model.previous_keyframe()

    def next_keyframe_cb(self, action):
        if self.model.frames.has_next_key():
            self.model.next_keyframe()

    def add_cel_cb(self, action):
        self.model.add_cel()

    def playpause_animation_cb(self, action):
        self.model.playpause_animation()

    def stop_animation_cb(self, action):
        if self.model.player_state == "play":
            self.model.stop_animation()

    def toggle_key_cb(self, action):
        self.model.toggle_key()

    def insert_frame_cb(self, action):
        self.model.insert_frames()

    def remove_frame_cb(self, action):
        self.model.remove_frames()

    def cut_cel_cb(self, action):
        self.model.cutcopy_cel('cut')

    def copy_cel_cb(self, action):
        self.model.cutcopy_cel('copy')

    def paste_cel_cb(self, action):
        if self.model.can_paste():
            self.model.paste_cel()
