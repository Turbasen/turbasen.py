# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os

import turbasen

def test_configure():
    turbasen.configure(
        LIMIT=30,
    )
    assert turbasen.settings.Settings.LIMIT == 30

def test_api_key():
    assert turbasen.settings.Settings.API_KEY == os.environ.get('TURBASEN_API_KEY')
