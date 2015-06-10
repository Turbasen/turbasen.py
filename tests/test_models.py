# encoding: utf-8
from __future__ import unicode_literals

import pytest

import turbasen

@pytest.fixture
def configure_dev():
    turbasen.configure(ENDPOINT_URL='http://dev.nasjonalturbase.no/')

@pytest.fixture
def no_etag_cache():
    turbasen.configure(ETAG_CACHE_PERIOD=0)

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_get(configure_dev):
    sted = turbasen.Sted.get('52407fb375049e561500004e')
    assert sted.navn == u'Tjørnbrotbu'
    assert sted.ssr_id == 382116

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_refresh(configure_dev, no_etag_cache):
    sted = turbasen.Sted.get('52407fb375049e561500004e')
    etag = sted._etag
    sted.refresh()
    assert etag == sted._etag

@pytest.mark.skipif(turbasen.settings.Settings.API_KEY is None, reason="API key not set")
def test_lookup(configure_dev):
    results = turbasen.Sted.lookup(pages=2)
    result_list = list(results)
    assert len(result_list) == turbasen.settings.Settings.LIMIT * 2
    assert result_list[0].object_id != ''
