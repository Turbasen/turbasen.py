# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

class DummyCache:
    """
    A dummy cache implementation which stores nothing and always returns None
    """

    def set(self, key, value, duration):
        pass

    def get(self, key):
        return None

    def delete(self, key):
        pass
