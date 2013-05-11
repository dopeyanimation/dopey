# This file is part of an as-of-yet unnamed animation program based
# on MyPaint and xsheet-mypaint
# Copyright (C) 2013 Davis Sorenon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import json

# adaptive file-format reader/writer inspired by Blender's SDNA system
# the format works like this:
# * dicts contain indices that are unique
# * arrays contain repeated objects
# an XDNA signature is equivalent to an empty xsheet with datatypes
# instead of data

class XDNA(object):

    def __init__(self):
        self.DEBUG = True

        self.application_signature = {
            'application': 'xsheet-mypaint',    # temporary!
            'version_number': '0.0.1+git'       # @TODO: automatically set this
        }

        # the XDNA signature of this version of the program
        self.xdna_signature = {
            # actual document starts here
            'xsheet': {
                # document information
                'framerate': 'float',

                # raster frame lists
                'raster_frame_lists': [
                    [{
                        'idx': 'int',
                        'is_key': 'bool',
                        'description': 'string'
                    }]
                ]
            }
        }

    def data_serialize(self, data):
        """
        Standardized way of converting data to json (or other formats if necessary)

        """
        return json.dumps(data, sort_keys=False, indent=2)

    def data_deserialize(self, data):
        """
        Standardized way of converting data from json

        """
        return json.loads(data)

    def signatures_diff(self, d1, d2, ctx='', path=[], difflog={'added': [], 'removed': [], 'changed_value': [], 'changed_type': []}):
        """
        Calculates, in high-level terms, the difference betweent two XDNA signatures

        """
        for k in d1:
            if k not in d2:
                difflog['removed'].append(path + [k])
        for k in d2:
            if k not in d1:
                difflog['added'].append(path + [k])
                continue
            if d2[k] != d1[k]:
                if type(d2[k]) not in (dict, list):
                    difflog['changed_value'].append(path + [k])
                else:
                    if type(d1[k]) != type(d2[k]):
                        difflog['changed_type'].append(path + [k])
                        continue
                    else:
                        if type(d2[k]) == dict:
                            self.signatures_diff(d1[k], d2[k], k, path + [k], difflog)
                            continue
                        elif type(d2[k]) == list:
                            self.signatures_diff(self.list_to_dict(d1[k]), self.list_to_dict(d2[k]), k, path + [k], difflog)
        return difflog

    def list_to_dict(self, l):
        return dict(zip(map(str, range(len(l))), l))
