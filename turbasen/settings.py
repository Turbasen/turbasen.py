# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os

from .cache import DummyCache

class Settings:
    ENDPOINT_URL = 'http://api.nasjonalturbase.no/'
    LIMIT = 20
    CACHE = DummyCache()
    API_KEY = os.environ.get('TURBASEN_API_KEY')
