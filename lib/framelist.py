# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

DEFAULT_OPACITIES = {
    'current':    1.0,  # The current cel
    'nextprev':   1./2, # The inmediate next and previous cels
    'key':        1./2, # The cel keys that are after and before the current cel 
    'inbetweens': 1./4, # The cels that are between the keys mentioned above
    'other keys': 1./4, # The other keys
    'other':      0,    # The rest of the cels
}

class Frame(object):
    def __init__(self, is_key=False, cel=None):
        self.is_key = is_key
        self.description = ""
        self.cel = cel
    
    def set_key(self):
        self.is_key = True
    
    def unset_key(self):
        self.is_key = False
    
    def toggle_key(self):
        self.is_key = not self.is_key
    
    def add_cel(self, cel):
        self.cel = cel
    
    def remove_cel(self):
        self.cel = None
    

class FrameList(list):
    """
    The list of frames that constitutes an animation.
    
    """
    def __init__(self, length, opacities=None):
        for l in range(length):
            self.append(Frame())
        self.idx = 0
        if opacities is None:
            opacities = {}
        self.opacities = dict(DEFAULT_OPACITIES)
        self.config_opacities(opacities)
    
    def config_opacities(self, opacities):
        self.opacities.update(opacities)
    
    def get_selected(self):
        return self[self.idx]
    
    def select(self, n):
        if not 0 <= n <= len(self)-1:
            raise IndexError("Trying to select inexistent frame.")
        self.idx = n
    
    def goto_next(self):
        if not self.has_next():
            raise IndexError("Trying to go to next at the last frame.")
        self.idx += 1
    
    def goto_previous(self):
        if not self.has_previous():
            raise IndexError("Trying to go to previous at the first frame.")
        self.idx -= 1
    
    def has_next(self):
        if self.idx == len(self)-1:
            return False
        return True
    
    def has_previous(self):
        if self.idx == 0:
            return False
        return True
    
    def get_next_key(self):
        for f in (self[self.idx+1:]):
            if f.is_key:
                return f
        return None
    
    def get_previous_key(self):
        for f in reversed(self[:self.idx]):
            if f.is_key:
                return f
        return None
    
    def goto_next_key(self):
        f = self.get_next_key()
        if f is None:
            raise IndexError("Trying to go to inexistent next keyframe.")
        self.idx = self.index(f)
    
    def goto_previous_key(self):
        f = self.get_previous_key()
        if f is None:
            raise IndexError("Trying to go to inexistent previous keyframe.")
        self.idx = self.index(f)
    
    def has_next_key(self):
        f = self.get_next_key()
        if f is None:
            return False
        return True
    
    def has_previous_key(self):
        f = self.get_previous_key()
        if f is None:
            return False
        return True
    
    def cel_at(self, n):
        """
        Return the cel at the nth frame.
        
        """
        if self[n].cel is not None:
            return self[n].cel
        for f in reversed(self[:n]):
            if f.cel is not None:
                return f.cel
        return None
    
    def get_previous_cel(self):
        """
        Return the previous cel that is different than the cel of the
        current frame.
        
        """
        cur_cel = self.cel_at(self.idx)
        if not cur_cel:
            return None
        for f in reversed(self[:self.idx]):
            if f.cel != cur_cel:
                return f.cel
        return None
    
    def get_next_cel(self):
        """
        Return the next cel that is different than the cel of the
        current frame.
        
        """
        cur_cel = self.cel_at(self.idx)
        if not cur_cel:
            return None
        for f in (self[self.idx+1:]):
            if f.cel != cur_cel:
                return f.cel
        return None
    
    def cel_for_frame(self, frame):
        """
        Return the cel for the frame.
        
        If no cel is defined for this frame, look back the frame list
        for the first cel that appears.  The returned cel is the one
        to be shown in the animation at the nth frame.
        
        """
        return self.cel_at(self.index(frame))
    
    def get_opacities(self):
        """
        Return a map of cels and the opacity they should have.
        
        To draw the current cel, the artist have to see it 100%
        opaque, and she may want to see the neighbour cels
        transparented.
        
        """
        opacities = {}
        
        cel = self.cel_for_frame(self.get_selected())
        if cel:
            opacities[cel] = self.opacities['current']
        
        cel = self.get_previous_cel()
        if cel and cel not in opacities.keys():
            opacities[cel] = self.opacities['nextprev']
        
        cel = self.get_next_cel()
        if cel and cel not in opacities.keys():
            opacities[cel] = self.opacities['nextprev']
        
        prevkey_idx = 0
        if self.has_previous_key():
            prevkey = self.get_previous_key()
            prevkey_idx = self.index(prevkey)
            cel = self.cel_for_frame(prevkey)
            if cel and cel not in opacities.keys():
                opacities[cel] = self.opacities['key']
        
        nextkey_idx = len(self)-1
        if self.has_next_key():
            nextkey = self.get_next_key()
            nextkey_idx = self.index(nextkey)
            cel = self.cel_for_frame(nextkey)
            if cel and cel not in opacities.keys():
                opacities[cel] = self.opacities['key']
        
        def has_cel(f):
            return f.cel is not None
        
        # inbetweens:
        inbetweens_range = self[prevkey_idx:nextkey_idx]
        for frame in filter(has_cel, inbetweens_range):
            cel = frame.cel
            if cel not in opacities.keys():
                opacities[cel] = self.opacities['inbetweens']
        
        # frames outside inmediate keys:
        outside_range = self[:prevkey_idx] + self[nextkey_idx:]
        for frame in filter(has_cel, outside_range):
            cel = frame.cel
            if cel not in opacities.keys():
                if frame.is_key:
                    opacities[cel] = self.opacities['other keys']
                else:
                    opacities[cel] = self.opacities['other']
        
        return opacities


def print_list(frames):
    """
    Utility funtion for debugging.
    
    """
    def info(f):
        all_info = []
        if frames.get_selected() == f:
            all_info.append("selected")
        if frames.get_previous_key() == f:
            all_info.append("previous key")
        if frames.get_next_key() == f:
            all_info.append("next key")
        return ', '.join(all_info)
    
    def key(f):
        if f.is_key:
            return '*'
        return ''
    
    for n, f in enumerate(frames):
        print n, key(f), info(f)


__test__ = dict(allem="""
>>> frames = FrameList(4)
>>> frames.index(frames.get_selected()) # same as frames.idx
0
>>> frames.goto_previous()
Traceback (most recent call last):
IndexError: Trying to go to previous at the first frame.
>>> frames.has_previous()
False
>>> frames.goto_next()
>>> frames.has_previous()
True
>>> frames.has_next()
True
>>> frames.goto_next()
>>> frames.idx
2
>>> frames.goto_previous()
>>> frames.goto_previous()
>>> frames.idx
0
>>> frames.select(len(frames)-1)
>>> frames.idx
3
>>> frames.has_next()
False
>>> frames.goto_next()
Traceback (most recent call last):
IndexError: Trying to go to next at the last frame.
>>> frames.select(100)
Traceback (most recent call last):
IndexError: Trying to select inexistent frame.
>>> frames.select(0)
>>> frames.get_previous_key()

>>> frames.get_next_key()

>>> frames[0].set_key()
>>> frames[3].set_key()
>>> frames.get_previous_key()

>>> frames.index(frames.get_next_key())
3
>>> frames.select(2)
>>> frames.idx
2
>>> frames.index(frames.get_previous_key())
0
>>> frames.index(frames.get_next_key())
3
>>> frames.get_opacities()
{}
>>> frames.cel_at(0)

>>> frames.cel_at(2)

>>> frames.cel_at(3)

>>> frames[0].add_cel('a')
>>> frames[1].add_cel('b')
>>> frames[3].add_cel('c')
>>> frames.cel_at(0)
'a'
>>> frames.cel_at(2)
'b'
>>> frames.cel_at(3)
'c'
>>> frames.cel_for_frame(frames.get_next_key())
'c'
>>> set(frames.get_opacities().items()) == set([('a', 0.5), ('b', 1.0), ('c', 0.5)])
True
>>> frames.goto_previous_key()
>>> frames.idx
0
>>> frames.goto_previous_key()
Traceback (most recent call last):
IndexError: Trying to go to inexistent previous keyframe.
>>> frames.has_previous_key()
False
>>> frames.goto_next_key()
>>> frames.has_previous_key()
True
>>> frames.has_next_key()
False
>>> frames.goto_next_key()
Traceback (most recent call last):
IndexError: Trying to go to inexistent next keyframe.
>>> frames.idx
3

""")

import doctest
doctest.testmod()
