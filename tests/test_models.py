# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

import turbasen

@pytest.fixture
def configure_dev():
    turbasen.configure(ENDPOINT_URL='http://dev.nasjonalturbase.no')

@pytest.fixture
def no_etag_cache():
    turbasen.configure(ETAG_CACHE_PERIOD=0)

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_get_sted(configure_dev):
    sted = turbasen.Sted.get('52407fb375049e561500004e')
    assert sted.navn == 'Tjørnbrotbu'
    assert sted.ssr_id == 382116

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_get_gruppe(configure_dev):
    gruppe = turbasen.Gruppe.get('52407f3c4ec4a13815000173')
    assert gruppe.navn == 'Alta og omegn turlag'

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_get_omrade(configure_dev):
    omrade = turbasen.Omrade.get('52408144e7926dcf15000004')
    assert omrade.navn == 'Sørlandet'

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_post(configure_dev):
    sted = turbasen.Sted(
        lisens='Privat',
        status='Kladd',
        navn='Testhytta',
        geojson={
            'properties': {'altitude': -999}, 'type': 'Point', 'coordinates': [12.18104163626816, 60.368712513406365]
        },
        fylke='Testfylket',
        beskrivelse='Testhytta er en opplevelse for seg selv',
        tags=[],
        bilder=[],
    )
    assert sted.object_id is None

    # POST the object and see that we've now defined its object_id
    sted.save()
    assert sted.object_id is not None

    # See that we can retrieve our POSTed data
    assert sted.beskrivelse == turbasen.Sted.get(sted.object_id).beskrivelse

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_put(configure_dev):
    sted = turbasen.Sted.get('52407fb375049e561500004e')

    # Change some data
    navn_original = sted.navn
    navn_reversed = sted.navn[::-1]
    assert navn_reversed != sted.navn

    # PUT the object with the new data
    sted.navn = navn_reversed
    sted.save()

    # See that we can retrieve our changed data
    sted = turbasen.Sted.get('52407fb375049e561500004e')
    assert navn_original != sted.navn
    assert navn_reversed == sted.navn

    # Reset the name, just in case
    sted.navn = navn_original
    sted.save()

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_delete(configure_dev):
    sted = turbasen.Sted(
        lisens='Privat',
        status='Kladd',
        navn='Testhytta',
        geojson={
            'properties': {'altitude': -999}, 'type': 'Point', 'coordinates': [12.18104163626816, 60.368712513406365]
        },
        fylke='Testfylket',
        beskrivelse='Testhytta er en opplevelse for seg selv',
        tags=[],
        bilder=[],
    )
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
def test_refresh(configure_dev, no_etag_cache):
    sted = turbasen.Sted.get('52407fb375049e561500004e')
    etag = sted._etag
    sted._refresh()
    assert etag == sted._etag

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_lookup(configure_dev):
    results = turbasen.Sted.lookup(pages=2)
    result_list = list(results)
    assert len(result_list) == turbasen.settings.Settings.LIMIT * 2
    assert result_list[0].object_id != ''
