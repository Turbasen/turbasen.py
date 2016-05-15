import contextlib
import unittest

import turbasen

class PermanentDictCache:
    """Simple dict cache which counts hits and misses"""
    keys = {}
    hits = 0
    misses = 0

    def get(self, key):
        if key in self.keys:
            self.hits += 1
        else:
            self.misses += 1
        return self.keys.get(key)

    def set(self, key, value, retainment):
        self.keys[key] = value

    def clear(self):
        self.keys = {}
        self.hits = 0
        self.misses = 0

class TestClass(unittest.TestCase):
    def setUp(self):
        turbasen.configure(ENDPOINT_URL='https://dev.nasjonalturbase.no')
        self.sted = turbasen.Sted(
            lisens='Privat',
            status='Kladd',
            navn='Testhytta',
            beskrivelse='Testhytta er en opplevelse for seg selv',
            navngiving='Testdata',
        )
        self.cache = PermanentDictCache()

    @contextlib.contextmanager
    def configure_cache(self):
        """Yield the local cache instance, clearing it on exit"""
        try:
            turbasen.configure(CACHE=self.cache)
            yield self.cache
        finally:
            turbasen.configure(CACHE=turbasen.cache.DummyCache())
            self.cache.clear()

    def test_dummy_cache(self):
        cache = turbasen.cache.DummyCache()
        cache.set('foo', 42, 3600)
        self.assertIsNone(cache.get('foo'))

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_cache_on_get(self):
        with self.configure_cache() as cache:
            # Save the object and assert that the cache has been set
            self.sted.save()
            self.assertIsNotNone(turbasen.settings.Settings.CACHE.get('turbasen.object.%s' % self.sted.object_id))
            self.assertEqual(cache.hits, 1)
            self.assertEqual(cache.misses, 0)

            # Now get it back, and asser that it was retrieved from cache
            sted = turbasen.Sted.get(self.sted.object_id)
            self.assertEqual(cache.hits, 2)
            self.assertEqual(cache.misses, 0)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_cache_on_fetch(self):
        # Save the object on test before configuring the test cache
        self.sted.save()
        with self.configure_cache() as cache:
            # Prepare a partial object, fetch it, and assert that the cache is set
            partial_sted = turbasen.Sted(_meta={'id': self.sted.object_id, 'is_partial': True})
            self.assertIsNone(turbasen.settings.Settings.CACHE.get('turbasen.object.%s' % partial_sted.object_id))
            self.assertEqual(cache.hits, 0)
            self.assertEqual(cache.misses, 1)
            partial_sted._fetch() # triggers another cache miss
            self.assertIsNotNone(turbasen.settings.Settings.CACHE.get('turbasen.object.%s' % partial_sted.object_id))
            self.assertEqual(cache.hits, 1)
            self.assertEqual(cache.misses, 2)

            # Now fetch it again, and assert that this time it was retrieved from cache
            partial_sted._fetch()
            self.assertEqual(cache.hits, 2)
            self.assertEqual(cache.misses, 2)
