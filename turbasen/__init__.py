# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

VERSION = '1.0.1'

# Import the models we want directly available through the 'turbasen' module
from .models import \
    Omrade, \
    Sted

def configure(**settings):
    from .settings import Settings
    for key, value in settings.items():
        setattr(Settings, key, value)
