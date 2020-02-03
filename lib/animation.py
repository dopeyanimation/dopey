# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import glob
from gettext import gettext as _
import json
import tempfile
from subprocess import call
import logging
logger = logging.getLogger('animation subsystem')


import pixbufsurface

import anicommand
from framelist import FrameList
from xdna import XDNA


class Animation(object):
    
    opacities = {
    'cel':   0.5,
    'key':        0.4,
    'inbetweens': 0.2,
    'other keys': 0.3,
    'other':      0,
    }
    
    def __init__(self, doc):
        self.doc = doc
        self.frames = None
        self.framerate = 24.0
        self.cleared = False
        self.using_legacy = False
        self.xdna = XDNA()

        # For reproduction, "play", "pause", "stop":
        self.player_state = None

        # For cut/copy/paste operations:
        self.edit_operation = None
        self.edit_frame = None

    def clear_xsheet(self, init=False):
        self.frames = FrameList(24, self.opacities)
        self.cleared = True
    
    def legacy_xsheet_as_str(self):
        """
        Return animation X-Sheet as data in json format.

        """
        data = []
        for f in self.frames:
            if f.cel is not None:
                layer_idx = self.doc.layers.index(f.cel)
            else:
                layer_idx = None
            data.append((f.is_key, f.description, layer_idx))
        str_data = json.dumps(data, sort_keys=True, indent=4)
        return str_data

    def xsheet_as_str(self):
        """
        Return animation X-Sheet as data in XDNA format.

        """
        x = self.xdna

        data = {
            'metadata': x.application_signature,
            'XDNA': x.xdna_signature,
            'xsheet': {
                'framerate': self.framerate,
                'raster_frame_lists': [[]]
            }
        }

        for f in self.frames:
            if f.cel is not None:
                layer_idx = self.doc.layers.index(f.cel)
            else:
                layer_idx = None
            data['xsheet']['raster_frame_lists'][0].append({
                'idx': layer_idx,
                'is_key': f.is_key,
                'description': f.description
            })

        str_data = json.dumps(data, sort_keys=True, indent=4)
        return str_data

    def _write_xsheet(self, xsheetfile):
        """
        Save FrameList to file.
        
        """
        str_data = self.xsheet_as_str()
        xsheetfile.write(str_data)

    def str_to_xsheet(self, ani_data):
        """
        Update FrameList from animation data.
    
        """

        data = json.loads(ani_data)

        # first check if it's in the legacy non-descriptive JSON or new XDNA format
        if type(data) is dict and data['XDNA']:
            print 'Loading using new file format'
            x = self.xdna

            # right now we only have one animatable layer, hence the first item
            raster_frames = data['xsheet']['raster_frame_lists'][0]

            self.frames = FrameList(len(raster_frames), self.opacities)
            self.framerate = data['xsheet']['framerate']
            self.cleared = True

            for i, d in enumerate(raster_frames):
                if d['idx'] is not None:
                    #cel = self.doc.layers[d['idx']] - this line exceptions with some files if the first frame is a key
                    
                    # cels appear to be numbered from 
                    # 0 in memory, but from 1 on disk...
                    cel = self.doc.layers[d['idx']-1] 
                else:
                    cel = None
                self.frames[i].is_key = d['is_key']
                self.frames[i].description = d['description']
                self.frames[i].cel = cel
                logger.info("loading cel #" + str(i))

        else:
            # load in legacy style
            print 'Loading using old format'
            self.using_legacy = True
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

    def _read_xsheet(self, xsheetfile):
        """
        Update FrameList from file.
    
        """
        ani_data = xsheetfile.read()
        self.str_to_xsheet(ani_data)
    
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
            cel._surface.save(filename, *doc_bbox, **kwargs)

    def save_avi(self, filename, vid_width=800, vid_fps=24, **kwargs):
        """
        Save video file with codec mpeg4.

        Requires command tools imagemagick and ffmpeg .

        """
        tempdir = tempfile.mkdtemp()
        jpgs_tempdir = os.path.join(tempdir, 'jpgs')
        os.mkdir(jpgs_tempdir)
        base_filename = os.path.basename(filename)
        prefix, ext = os.path.splitext(base_filename)
        out_filename = os.path.join(os.path.dirname(filename), prefix + '.avi')

        pngs_filename = os.path.join(tempdir, 'tempani.png')
        self.save_png(pngs_filename)

        # convert pngs to jpegs with imagemagick command:
        pngs_list = glob.glob(tempdir + os.path.sep + '*png')
        pngs_list.sort()
        for png_file in pngs_list:
            f_basename = os.path.basename(png_file)
            name, ext = os.path.splitext(f_basename)
            jpg_file = os.path.join(jpgs_tempdir, name + '.jpg')
            print "converting %s to %s..." % (png_file, jpg_file)
            call(["convert",
                  "-resize", str(vid_width),
                  "-quality", "100",
                  "-background", "white",
                  "-flatten",
                  png_file, jpg_file])

        # convert the previous jpgs to video with ffmpeg command:
        jpgs = jpgs_tempdir + os.path.sep + 'tempani-%03d.jpg'
        call(["ffmpeg",
              "-r", str(vid_fps),
              "-b", "1800",
              "-y", "-i",
              jpgs, out_filename])

    def _notify_canvas_observers(self, affected_layer):
        bbox = affected_layer._surface.get_bbox()
        for f in self.doc.canvas_observers:
            f(*bbox)

    def hide_all_frames(self):
        cels = []
        for cel in self.frames.get_all_cels():
            cel.visible = False
            self._notify_canvas_observers(cel)

    def change_visible_frame(self, prev_idx, cur_idx):
        prev_cel = self.frames.cel_at(prev_idx)
        cur_cel = self.frames.cel_at(cur_idx)
        if prev_cel == cur_cel:
            return
        if prev_cel != None:
            prev_cel.visible = False
            self._notify_canvas_observers(prev_cel)
        if cur_cel == None:
            return
        cur_cel.opacity = 1
        cur_cel.visible = True
        self._notify_canvas_observers(cur_cel)

    def update_opacities(self):
        opacities, visible = self.frames.get_opacities()

        for cel, opa in opacities.items():
            if cel is None:
                continue
            cel.opacity = opa
            self._notify_canvas_observers(cel)

        for cel, vis in visible.items():
            if cel is None:
                continue
            cel.visible = vis
            self._notify_canvas_observers(cel)

    def select_without_undo(self, idx):
        """Like the command but without undo/redo."""
        self.frames.select(idx)
        self.update_opacities()

    def play_animation(self):
        self.player_state = "play"
        self.doc.call_doc_observers()

    def pause_animation(self):
        self.player_state = "pause"

    def playpause_animation(self):
        if self.player_state != "play":
            self.player_state = "play"
        else:
            self.player_state = "pause"
        self.doc.call_doc_observers()

    def stop_animation(self):
        self.player_state = "stop"

    def player_next(self, use_lightbox=False):
        prev_idx = self.frames.idx
        if self.frames.has_next():
            self.frames.goto_next()
        else:
            self.frames.select(0)
        if use_lightbox:
            self.update_opacities()
        else:
            self.change_visible_frame(prev_idx, self.frames.idx)

    def toggle_key(self):
        frame = self.frames.get_selected()
        self.doc.do(anicommand.ToggleKey(self.doc, frame))

    def toggle_skip_visible(self):
        frame = self.frames.get_selected()
        self.doc.do(anicommand.ToggleSkipVisible(self.doc, frame))

    def previous_frame(self, with_cel=False):
        self.frames.goto_previous(with_cel)
        self.update_opacities()
        self.doc.call_doc_observers()

    def next_frame(self, with_cel=False):
        self.frames.goto_next(with_cel)
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
    
    def toggle_nextprev(self, nextprev, is_active):
        self.frames.setup_nextprev({nextprev: is_active})
        self.update_opacities()
    
    def insert_frames(self, ammount=1):
        self.doc.do(anicommand.InsertFrames(self.doc, ammount))

    def remove_frames(self, ammount=1):
        self.doc.do(anicommand.RemoveFrames(self.doc, ammount))

    def can_cutcopy(self):
        frame = self.frames.get_selected()
        return frame.cel is not None

    def cutcopy_cel(self, edit_operation):
        frame = self.frames.get_selected()
        self.doc.ani.edit_operation = edit_operation
        self.doc.ani.edit_frame = frame
        self.doc.call_doc_observers()

    def can_paste(self):
        frame = self.frames.get_selected()
        return self.edit_frame is not None and \
            self.edit_frame != frame and \
            frame.cel == None

    def paste_cel(self):
        frame = self.frames.get_selected()
        self.doc.do(anicommand.PasteCel(self.doc, frame))
