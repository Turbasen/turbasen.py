import turbasen

def test_cache():
    cache = turbasen.cache.DummyCache()
    cache.set('foo', 42, 3600)
    assert cache.get('foo') is None
