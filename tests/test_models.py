# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

import turbasen

class ObjectManager:
    def __init__(self):
        self.sted = turbasen.Sted(
            lisens='Privat',
            status='Kladd',
            navn='Testhytta',
            beskrivelse='Testhytta er en opplevelse for seg selv',
        )

        self.gruppe = turbasen.Gruppe(
            lisens='Privat',
            status='Kladd',
            navn='Testgruppe',
        )

        self.omrade = turbasen.Omrade(
            lisens='Privat',
            status='Kladd',
            navn='Testområde',
        )

@pytest.fixture
def object_manager():
    return ObjectManager()

@pytest.fixture
def configure_dev():
    turbasen.configure(ENDPOINT_URL='http://dev.nasjonalturbase.no')

@pytest.fixture
def no_etag_cache():
    turbasen.configure(ETAG_CACHE_PERIOD=0)

class TestClass:

    #
    # Fixtures to POST sample data before running tests
    #

    @pytest.fixture
    def post_managed_sted(self, request, object_manager):
        object_manager.sted.save()
        request.addfinalizer(object_manager.sted.delete)

    @pytest.fixture
    def post_managed_gruppe(self, request, object_manager):
        object_manager.gruppe.save()
        request.addfinalizer(object_manager.gruppe.delete)

    @pytest.fixture
    def post_managed_omrade(self, request, object_manager):
        object_manager.omrade.save()
        request.addfinalizer(object_manager.omrade.delete)

    #
    # Tests
    #

    @pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
    def test_get_sted(self, configure_dev, object_manager, post_managed_sted):
        sted = turbasen.Sted.get(object_manager.sted.object_id)
        assert sted.navn == object_manager.sted.navn

    @pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
    def test_get_gruppe(self, configure_dev, object_manager, post_managed_gruppe):
        gruppe = turbasen.Gruppe.get(object_manager.gruppe.object_id)
        assert gruppe.navn == 'Testgruppe'

    @pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
    def test_get_omrade(self, configure_dev, object_manager, post_managed_omrade):
        omrade = turbasen.Omrade.get(object_manager.omrade.object_id)
        assert omrade.navn == 'Testområde'

    @pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
    def test_post(self, configure_dev, object_manager):
        sted = object_manager.sted
        assert sted.object_id is None

        # POST the object and see that we've now defined its object_id
        sted.save()
        assert sted.object_id is not None

        # See that we can retrieve our POSTed data
        assert sted.beskrivelse == turbasen.Sted.get(sted.object_id).beskrivelse

    @pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
    def test_put(self, configure_dev, object_manager, post_managed_sted):
        sted = object_manager.sted

        # Change some data
        navn_original = sted.navn
        navn_reversed = sted.navn[::-1]
        assert navn_reversed != sted.navn

        # PUT the object with the new data
        sted.navn = navn_reversed
        sted.save()

        # See that we can retrieve our changed data
        sted = turbasen.Sted.get(sted.object_id)
        assert navn_original != sted.navn
        assert navn_reversed == sted.navn

    @pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
    def test_delete(self, configure_dev, object_manager):
        sted = object_manager.sted
        assert sted.object_id is None

        # POST the object and see that we've now defined its object_id
        sted.save()
        object_id = sted.object_id
        assert sted.object_id is not None

        # See that we can delete it
        sted.delete()
        assert sted.object_id is None
        with pytest.raises(turbasen.exceptions.DocumentNotFound):
            turbasen.Sted.get(object_id)

    @pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
    def test_refresh(self, configure_dev, object_manager, post_managed_sted):
        sted = object_manager.sted
        etag = sted._etag
        sted._refresh()
        assert etag == sted._etag

    @pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
    def test_lookup(self, configure_dev):
        results = turbasen.Sted.lookup(pages=2)
        result_list = list(results)
        assert len(result_list) == turbasen.settings.Settings.LIMIT * 2
        assert result_list[0].object_id != ''

    @pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
    def test_extra(self, configure_dev):
        sted = turbasen.Sted(navn='Heia', foo_bar=42)
        assert hasattr(sted, 'navn')
        assert not hasattr(sted, 'foo_bar')
        assert 'foo_bar' in sted._extra
        assert 'foo_bar' in sted.get_data(include_extra=True)
        assert 'foo_bar' not in sted.get_data(include_extra=False)
