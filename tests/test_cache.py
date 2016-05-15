# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

import turbasen

class TestClass(unittest.TestCase):
    def test_dummy_cache(self):
        cache = turbasen.cache.DummyCache()
        cache.set('foo', 42, 3600)
        self.assertIsNone(cache.get('foo'))
