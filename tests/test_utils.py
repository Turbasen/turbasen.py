# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from turbasen.util import params_to_dotnotation

def test_params_to_dotnotation():
    test_dict = {
        'foo': 'bar',
        'bar': {
            'baz': {
                'abc': 42,
                'def': 43,
                'foo': {
                    'wat': ''
                },
            },
            'ghi': 44
        },
        'jkl': 'mno'
    }
    expected_result = {
        'foo': 'bar',
        'bar.baz.abc': 42,
        'bar.baz.def': 43,
        'bar.baz.foo.wat': '',
        'bar.ghi': 44,
        'jkl': 'mno',
    }
    assert params_to_dotnotation(test_dict) == expected_result
