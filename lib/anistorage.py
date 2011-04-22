# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

def save(frames, xsheetfile):
    """
    Save FrameList to file.
    
    """
    str_data = []
    for f in frames:
        if f.is_key:
            iskey = 'True\n'
        else:
            iskey = 'False\n'
        str_data.append(iskey)
    xsheetfile.writelines(str_data)

def load(frames, xsheetfile):
    """
    Update FrameList from file.
    
    """
    # TODO load X Sheet from file
    str_data = xsheetfile.readlines()
    for i, data in enumerate(str_data):
        if data == 'True\n':
            frames[i].is_key = True
        else:
            frames[i].is_key = False
