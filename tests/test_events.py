from turbasen.events import trigger
import turbasen

def test_events():
    global mutable_list
    mutable_list = []

    def add_value_to_list():
        mutable_list.append(1)

    trigger('foo')
    turbasen.handle_event('foo', add_value_to_list)
    trigger('foo')
    trigger('bar')

    assert len(mutable_list) == 1
