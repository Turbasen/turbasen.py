import unittest

import turbasen

class ObjectsFixture:
    def __init__(self):
        self.bilde = turbasen.Bilde(
            lisens='Privat',
            status='Kladd',
            navn='Testbilde',
            navngiving='Testdata',
            fotograf={'navn': 'Test Testesen'},
            eier={'navn': 'Test Testesen'},
            img=[{'url': 'https://test'}],
        )

        self.gruppe = turbasen.Gruppe(
            lisens='Privat',
            status='Kladd',
            navn='Testgruppe',
            navngiving='Testdata',
        )

        self.omrade = turbasen.Område(
            lisens='Privat',
            status='Kladd',
            navn='Testområde',
            navngiving='Testdata',
        )

        self.sted = turbasen.Sted(
            lisens='Privat',
            status='Kladd',
            navn='Testhytta',
            beskrivelse='Testhytta er en opplevelse for seg selv',
            navngiving='Testdata',
        )

        self.tur = turbasen.Tur(
            lisens='Privat',
            navngiving='Testdata',
            status='Kladd',
            navn='Testtur',
            fylker=['Testfylket'],
            beskrivelse='Testturen er en opplevelse for seg selv',
            gradering='Enkel',
            sesong=['1'],
        )

class TestClass(unittest.TestCase):
    def setUp(self):
        turbasen.configure(ENDPOINT_URL='https://dev.nasjonalturbase.no')
        self.objects = ObjectsFixture()

    def test_get_empty_object_id(self):
        with self.assertRaises(turbasen.exceptions.DocumentNotFound):
            turbasen.Sted.get('')

    @unittest.skipIf(turbasen.settings.Settings.API_KEY == '', "API key not set")
    def test_post_get(self):
        # Assert that the fixture objects are not saved on the server
        self.assertNotIn('_id', self.objects.bilde)
        self.assertNotIn('_id', self.objects.sted)
        self.assertNotIn('_id', self.objects.gruppe)
        self.assertNotIn('_id', self.objects.omrade)
        self.assertNotIn('_id', self.objects.tur)

        # POST our fixture objects
        self.objects.bilde.save()
        self.objects.sted.save()
        self.objects.gruppe.save()
        self.objects.omrade.save()
        self.objects.tur.save()

        self.assertIn('_id', self.objects.bilde)
        self.assertIn('_id', self.objects.sted)
        self.assertIn('_id', self.objects.gruppe)
        self.assertIn('_id', self.objects.omrade)
        self.assertIn('_id', self.objects.tur)

        # GET the data back
        bilde = turbasen.Bilde.get(self.objects.bilde['_id'])
        sted = turbasen.Sted.get(self.objects.sted['_id'])
        gruppe = turbasen.Gruppe.get(self.objects.gruppe['_id'])
        omrade = turbasen.Område.get(self.objects.omrade['_id'])
        tur = turbasen.Tur.get(self.objects.tur['_id'])

        self.assertEqual(bilde['navn'], self.objects.bilde['navn'])
        self.assertEqual(sted['navn'], self.objects.sted['navn'])
        self.assertEqual(gruppe['navn'], self.objects.gruppe['navn'])
        self.assertEqual(omrade['navn'], self.objects.omrade['navn'])
        self.assertEqual(tur['navn'], self.objects.tur['navn'])

    @unittest.skipIf(turbasen.settings.Settings.API_KEY == '', "API key not set")
    def test_put(self):
        self.objects.sted.save()

        # Change some data
        navn_original = self.objects.sted['navn']
        navn_reversed = self.objects.sted['navn'][::-1]
        self.assertNotEqual(navn_reversed, self.objects.sted['navn'])

        # PUT the object with the new data
        self.objects.sted['navn'] = navn_reversed
        self.objects.sted.save()

        # See that we can retrieve our changed data
        sted = turbasen.Sted.get(self.objects.sted['_id'])
        self.assertNotEqual(navn_original, sted['navn'])
        self.assertEqual(navn_reversed, sted['navn'])

    @unittest.skipIf(turbasen.settings.Settings.API_KEY == '', "API key not set")
    def test_delete(self):
        # POST the object
        self.objects.sted.save()

        # See that we can delete it
        object_id = self.objects.sted['_id']
        self.objects.sted.delete()
        self.assertFalse('_id' in self.objects.sted)
        with self.assertRaises(turbasen.exceptions.DocumentNotFound):
            turbasen.Sted.get(object_id)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY == '', "API key not set")
    def test_refresh(self):
        self.objects.sted.save()

        etag = self.objects.sted._etag
        self.objects.sted._refresh()
        self.assertEqual(etag, self.objects.sted._etag)

    def test_list(self):
        results = turbasen.Sted.list(pages=2)
        self.assertEqual(len(results), turbasen.settings.Settings.LIMIT * 2)
        self.assertNotEqual(results[0]['_id'], '')

    def test_list_empty(self):
        results = turbasen.Sted.list(params={'foo': 404})
        self.assertEqual(len(results), 0)

    def test_list_fields(self):
        results = turbasen.Sted.list(pages=1, params={
            'fields': ['betjeningsgrad'],
            'tags': 'Hytte',
            'betjeningsgrad': 'Betjent',
        })
        result = results[0]
        self.assertIn('Hytte', result['tags'])
        self.assertEqual(result['betjeningsgrad'], 'Betjent')
        # Ensure that the previous assertion did *not* fetch the entire document
        self.assertTrue(result._is_partial)

    def test_list_single_field(self):
        results = turbasen.Sted.list(pages=1, params={
            'fields': 'betjeningsgrad', # Note that the string literal is not wrapped in a list
            'tags': 'Hytte',
            'betjeningsgrad': 'Betjent',
        })
        result = results[0]
        self.assertIn('Hytte', result['tags'])
        self.assertEqual(result['betjeningsgrad'], 'Betjent')
        # Ensure that the previous assertion did *not* fetch the entire document
        self.assertTrue(result._is_partial)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY == '', "API key not set")
    def test_fetch_partial_object(self):
        self.objects.sted.save()
        sted = turbasen.Sted(
            _is_partial=True,
            _id=self.objects.sted['_id'],
            navn='Partial',
        )
        self.assertTrue(sted._is_partial)
        sted._fetch()
        self.assertFalse(sted._is_partial)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY == '', "API key not set")
    def test_equality(self):
        self.objects.sted.save()
        sted_retrieved = turbasen.Sted.get(self.objects.sted['_id'])
        sted_unsaved = turbasen.Sted(navn=self.objects.sted['navn'])
        self.assertEqual(self.objects.sted, self.objects.sted)
        self.assertEqual(self.objects.sted, sted_retrieved)
        self.assertNotEqual(sted_retrieved, sted_unsaved)
