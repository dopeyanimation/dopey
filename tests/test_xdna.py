# test XDNA file reading, writing
import sys
import unittest
import json

sys.path.insert(0, '..')

from lib.xdna import *

class TestXDNASignatureFunctions(unittest.TestCase):

    def setUp(self):
        self.xdna = XDNA()

        self.signature_base = {
            'application': 'mypaint-xsheet',
            'version_number': '0.1.0+git',
            'xsheet': {
                'framerate': 'float',
                'some_hash': {
                    'value1': 'somevalue'
                },
                'some_list': [1, 2, 3],
                'raster_frame_lists': [{
                    'raster_frame_list': [{
                        'idx': 'int',
                        'is_key': 'bool',
                        'description': 'string'
                    }]
                }]
            }
        }

        self.signature_addeditems = {
            'application': 'mypaint-xsheet',
            'version_number': '0.1.0+git',
            'added_item': 'somevalue',
            'xsheet': {
                'added_subitem': 'somevalue',
                'added_hash': {
                    'value1': 'somevalue',
                    'value2': 'somevalue'
                },
                'some_hash': {
                    'value1': 'somevalue'
                },
                'added_list': [1, 2, 3],
                'framerate': 'float',
                'raster_frame_lists': [{
                    'raster_frame_list': [{
                        'added_subsubitem': 'somevalue',
                        'idx': 'int',
                        'is_key': 'bool',
                        'description': 'string'
                    }]
                }]
            }
        }

        self.signature_removeditems = {
            'version_number': '0.1.0+git',
            'xsheet': {
                'raster_frame_lists': [{
                    'raster_frame_list': [{
                        'idx': 'int',
                        'is_key': 'bool'
                    }]
                }]
            }
        }

        self.signature_changedvalueitems = {
            'application': 'changed_value',
            'version_number': '0.1.0+git',
            'xsheet': {
                'framerate': 'int',
                'some_hash': {
                    'value1': 'somevalue'
                },
                'some_list': [1, 2, 3],
                'raster_frame_lists': [{
                    'raster_frame_list': [{
                        'idx': 'int',
                        'is_key': 'bool',
                        'description': 'blah blah'
                    }]
                }]
            }
        }

        self.signature_changedtypeitems = {
            'application': ['mypaint-xsheet'],
            'version_number': '0.1.0+git',
            'xsheet': {
                'framerate': {'float': 'test'},
                'some_hash': {
                    'value1': 'somevalue'
                },
                'some_list': [1, 2, 3],
                'raster_frame_lists': [{
                    'raster_frame_list': [{
                        'idx': 'int',
                        'is_key': 'bool',
                        'description': []
                    }]
                }]
            }
        }

    def test_serialization(self):
        x = self.xdna

        serialized = x.data_serialize(x.signature_skeleton)
        deserialized = x.data_deserialize(serialized)

        self.assertEqual(x.signature_skeleton, deserialized)

    def test_signature_comparison_added(self):
        x = self.xdna

        diff = x.signatures_diff(self.signature_base, self.signature_addeditems)

        self.assertTrue(['added_item'] in diff['added'])
        self.assertTrue(['xsheet', 'added_subitem'] in diff['added'])
        self.assertTrue(['xsheet', 'added_hash'] in diff['added'])
        self.assertTrue(['xsheet', 'added_list'] in diff['added'])
        self.assertTrue(['xsheet', 'raster_frame_lists', '0', 'raster_frame_list', '0', 'added_subsubitem'] in diff['added'])

    def test_signature_comparison_removed(self):
        x = self.xdna

        diff = x.signatures_diff(self.signature_base, self.signature_removeditems)

        self.assertTrue(['application'] in diff['removed'])
        self.assertTrue(['xsheet', 'framerate'] in diff['removed'])
        self.assertTrue(['xsheet', 'some_hash'] in diff['removed'])
        self.assertTrue(['xsheet', 'some_list'] in diff['removed'])
        self.assertTrue(['xsheet', 'raster_frame_lists', '0', 'raster_frame_list', '0', 'description'] in diff['removed'])

    def test_signature_comparison_changedvalue(self):
        x = self.xdna

        diff = x.signatures_diff(self.signature_base, self.signature_changedvalueitems)

        self.assertTrue(['application'] in diff['changed_value'])
        self.assertTrue(['xsheet', 'framerate'] in diff['changed_value'])
        self.assertTrue(['xsheet', 'raster_frame_lists', '0', 'raster_frame_list', '0', 'description'] in diff['changed_value'])

    def test_signature_comparison_changedtype(self):
        x = self.xdna

        diff = x.signatures_diff(self.signature_base, self.signature_changedtypeitems)

        self.assertTrue(['application'] in diff['changed_type'])
        self.assertTrue(['xsheet', 'framerate'] in diff['changed_type'])
        self.assertTrue(['xsheet', 'raster_frame_lists', '0', 'raster_frame_list', '0', 'description'] in diff['changed_type'])

if __name__ == '__main__':
    unittest.main()
