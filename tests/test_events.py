import unittest

from turbasen.events import trigger
import turbasen

class TestClass(unittest.TestCase):
    def test_custom_event(self):
        global mutable_list
        mutable_list = []

        def add_value_to_list():
            mutable_list.append(1)

        trigger('foo')
        turbasen.handle_event('foo', add_value_to_list)
        trigger('foo')
        trigger('bar')

        self.assertEqual(len(mutable_list), 1)

    def test_get_event(self):
        global mutable_list
        mutable_list = []

        def add_value_to_list():
            mutable_list.append(1)

        turbasen.handle_event('api.get_object', add_value_to_list)
        turbasen.Sted.get('52407fb375049e561500004e')

        self.assertEqual(len(mutable_list), 1)
