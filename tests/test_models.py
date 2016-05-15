# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

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

        self.omrade = turbasen.Omrade(
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

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_get_empty_object_id(self):
        with self.assertRaises(turbasen.exceptions.DocumentNotFound):
            turbasen.Sted.get('')

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_post_get(self):
        # Assert that the fixture objects are not saved on the server
        self.assertIsNone(self.objects.bilde.object_id)
        self.assertIsNone(self.objects.sted.object_id)
        self.assertIsNone(self.objects.gruppe.object_id)
        self.assertIsNone(self.objects.omrade.object_id)
        self.assertIsNone(self.objects.tur.object_id)

        # POST our fixture objects
        self.objects.bilde.save()
        self.objects.sted.save()
        self.objects.gruppe.save()
        self.objects.omrade.save()
        self.objects.tur.save()

        self.assertIsNotNone(self.objects.bilde.object_id)
        self.assertIsNotNone(self.objects.sted.object_id)
        self.assertIsNotNone(self.objects.gruppe.object_id)
        self.assertIsNotNone(self.objects.omrade.object_id)
        self.assertIsNotNone(self.objects.tur.object_id)

        # GET the data back
        bilde = turbasen.Bilde.get(self.objects.bilde.object_id)
        sted = turbasen.Sted.get(self.objects.sted.object_id)
        gruppe = turbasen.Gruppe.get(self.objects.gruppe.object_id)
        omrade = turbasen.Omrade.get(self.objects.omrade.object_id)
        tur = turbasen.Tur.get(self.objects.tur.object_id)

        self.assertEqual(bilde.navn, self.objects.bilde.navn)
        self.assertEqual(sted.navn, self.objects.sted.navn)
        self.assertEqual(gruppe.navn, self.objects.gruppe.navn)
        self.assertEqual(omrade.navn, self.objects.omrade.navn)
        self.assertEqual(tur.navn, self.objects.tur.navn)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_put(self):
        self.objects.sted.save()

        # Change some data
        navn_original = self.objects.sted.navn
        navn_reversed = self.objects.sted.navn[::-1]
        self.assertNotEqual(navn_reversed, self.objects.sted.navn)

        # PUT the object with the new data
        self.objects.sted.navn = navn_reversed
        self.objects.sted.save()

        # See that we can retrieve our changed data
        sted = turbasen.Sted.get(self.objects.sted.object_id)
        self.assertNotEqual(navn_original, sted.navn)
        self.assertEqual(navn_reversed, sted.navn)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_delete(self):
        # POST the object
        self.objects.sted.save()

        # See that we can delete it
        object_id = self.objects.sted.object_id
        self.objects.sted.delete()
        self.assertIsNone(self.objects.sted.object_id)
        with self.assertRaises(turbasen.exceptions.DocumentNotFound):
            turbasen.Sted.get(object_id)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_refresh(self):
        self.objects.sted.save()

        etag = self.objects.sted._etag
        self.objects.sted._refresh()
        self.assertEqual(etag, self.objects.sted._etag)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_lookup(self):
        results = turbasen.Sted.lookup(pages=2)
        result_list = list(results)
        self.assertEqual(len(result_list), turbasen.settings.Settings.LIMIT * 2)
        self.assertNotEqual(result_list[0].object_id, '')

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_lookup_fields(self):
        results = turbasen.Sted.lookup(pages=1, params={
            'fields': ['betjeningsgrad'],
            'tags': 'Hytte',
            'betjeningsgrad': 'Betjent',
        })
        result = results[0]
        self.assertIn('Hytte', result.tags)
        self.assertEqual(result.betjeningsgrad, 'Betjent')
        # Ensure that the previous assertion did *not* fetch the entire document
        self.assertTrue(result._is_partial)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_lookup_single_field(self):
        results = turbasen.Sted.lookup(pages=1, params={
            'fields': 'betjeningsgrad', # Note that the string literal is not wrapped in a list
            'tags': 'Hytte',
            'betjeningsgrad': 'Betjent',
        })
        result = results[0]
        self.assertIn('Hytte', result.tags)
        self.assertEqual(result.betjeningsgrad, 'Betjent')
        # Ensure that the previous assertion did *not* fetch the entire document
        self.assertTrue(result._is_partial)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_extra(self):
        sted = turbasen.Sted(navn='Heia', foo_bar=42)
        self.assertTrue(hasattr(sted, 'navn'))
        self.assertFalse(hasattr(sted, 'foo_bar'))
        self.assertIn('foo_bar', sted._extra)
        self.assertIn('foo_bar', sted.get_data(include_extra=True))
        self.assertNotIn('foo_bar', sted.get_data(include_extra=False))

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_fetch_partial_object(self):
        self.objects.sted.save()
        sted = turbasen.Sted(
            _meta={
                'id': self.objects.sted.object_id,
                'is_partial': True,
            },
            navn='Partial',
        )
        self.assertTrue(sted._is_partial)
        sted._fetch()
        self.assertFalse(sted._is_partial)

    @unittest.skipIf(turbasen.settings.Settings.API_KEY is None, "API key not set")
    def test_equality(self):
        self.objects.sted.save()
        sted_retrieved = turbasen.Sted.get(self.objects.sted.object_id)
        sted_unsaved = turbasen.Sted(navn=self.objects.sted.navn)
        self.assertEqual(self.objects.sted, self.objects.sted)
        self.assertEqual(self.objects.sted, sted_retrieved)
        self.assertNotEqual(sted_retrieved, sted_unsaved)
