# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json

def save(frames, xsheetfile, doc):
    """
    Save FrameList to file.
    
    """
    data = []
    for f in frames:
        if f.cel is not None:
            layer_idx = doc.layers.index(f.cel)
        else:
            layer_idx = None
        data.append((f.is_key, f.description, layer_idx))
    str_data = json.dumps(data, sort_keys=True, indent=4)
    xsheetfile.write(str_data)

def load(frames, xsheetfile, doc):
    """
    Update FrameList from file.
    
    """
    # TODO load X Sheet from file
    str_data = xsheetfile.read()
    data = json.loads(str_data)
    for i, d in enumerate(data):
        is_key, description, layer_idx = d
        if layer_idx is not None:
            cel = doc.layers[layer_idx]
        else:
            cel = None
        frames[i].is_key = is_key
        frames[i].description = description
        frames[i].cel = cel
