# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
import os

import turbasen

class TestClass(unittest.TestCase):
    def test_configure(self):
        turbasen.configure(
            LIMIT=30,
        )
        self.assertEqual(turbasen.settings.Settings.LIMIT, 30)

    def test_api_key(self):
        self.assertEqual(turbasen.settings.Settings.API_KEY, os.environ.get('API_KEY'))
