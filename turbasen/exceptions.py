# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

class DocumentNotFound(Exception):
    """Thrown when a request for a document with a given object id isn't found in Turbasen"""
    pass

class Unauthorized(Exception):
    """Thrown when a request returns a HTTP 401 Unathorized or 403 Forbidden status code"""
    pass
