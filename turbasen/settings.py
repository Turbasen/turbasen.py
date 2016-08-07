import os

from .cache import DummyCache

class MetaSettings(type):
    """Implements reprentation for the Settings singleton, displaying all settings and values"""
    def __repr__(cls):
        settings = [
            '%s=%s' % (name, getattr(cls, name))
            for name in dir(cls)
            if not name.startswith('_')
        ]
        return '<%s: %s>' % (cls.__name__, ', '.join(settings))

class Settings(metaclass=MetaSettings):
    ENDPOINT_URL = os.environ.get('ENDPOINT_URL', 'https://api.nasjonalturbase.no')
    LIMIT = 20
    CACHE = DummyCache()
    CACHE_LOOKUP_PERIOD = 60 * 60 * 24
    CACHE_GET_PERIOD = 60 * 60 * 24 * 30
    ETAG_CACHE_PERIOD = 60 * 60
    API_KEY = os.environ.get('API_KEY', '')

def configure(**settings):
    for key, value in settings.items():
        # Strip any trailing slash in ENDPOINT_URL
        if key == 'ENDPOINT_URL':
            value = value.rstrip('/')

        setattr(Settings, key, value)
