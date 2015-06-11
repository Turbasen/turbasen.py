# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from turbasen.events import trigger
import turbasen

def test_custom_event():
    global mutable_list
    mutable_list = []

    def add_value_to_list():
        mutable_list.append(1)

    trigger('foo')
    turbasen.handle_event('foo', add_value_to_list)
    trigger('foo')
    trigger('bar')

    assert len(mutable_list) == 1

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_get_event():
    global mutable_list
    mutable_list = []

    def add_value_to_list():
        mutable_list.append(1)

    turbasen.handle_event('api.get_object', add_value_to_list)
    turbasen.Sted.get('52407fb375049e561500004e')

    assert len(mutable_list) == 1
