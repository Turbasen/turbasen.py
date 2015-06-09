from .cache import DummyCache

class Settings:
    ENDPOINT_URL = u'http://api.nasjonalturbase.no/'
    LIMIT = 20
    CACHE = DummyCache()
