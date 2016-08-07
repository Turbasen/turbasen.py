import unittest

from turbasen.util import params_to_dotnotation

class TestClass(unittest.TestCase):
    def test_params_to_dotnotation(self):
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
        self.assertEqual(params_to_dotnotation(test_dict), expected_result)
