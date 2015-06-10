# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os

from .cache import DummyCache

class Settings:
    ENDPOINT_URL = 'http://api.nasjonalturbase.no/'
    LIMIT = 20
    CACHE = DummyCache()
    CACHE_LOOKUP_PERIOD = 60 * 60 * 24
    CACHE_GET_PERIOD = 60 * 60 * 24 * 30
    ETAG_CACHE_PERIOD = 60 * 60
    API_KEY = os.environ.get('TURBASEN_API_KEY')

def configure(**settings):
    for key, value in settings.items():
        setattr(Settings, key, value)
