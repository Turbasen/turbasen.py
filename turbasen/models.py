# encoding: utf-8
import requests

from .settings import Settings
from .exceptions import DocumentNotFound

class NTBObject(object):
    def __init__(self, document, _is_partial=False):
        self.object_id = document['_id']
        self.tilbyder = document['tilbyder']
        self.endret = document['endret']
        self.lisens = document['lisens']
        self.status = document['status']
        self._is_partial = _is_partial

    def __getattr__(self, name):
        """On attribute lookup failure, if the object is only partially retrieved, get the rest of its data and try
        again"""
        if not name.startswith('_') and self._is_partial:
            # Note that we're ignoring internal non-existing attributes, which can occur in various situations, e.g.
            # when serializing for caching.
            self.fetch()
            return getattr(self, name)
        else:
            # Default behavior - no such attribute
            raise AttributeError

    def fetch(self):
        """If this object is only partially fetched, this method will retrieve the rest of its fields"""
        if not self._is_partial:
            return
        document = NTBObject.get_document(self.identifier, self.object_id)
        for field in self.FIELDS:
            variable_name = field.replace(u'æ', u'ae').replace(u'ø', u'o').replace(u'å', u'a')
            setattr(self, variable_name, document.get(field))
        self._is_partial = False

    #
    # Lookup static methods
    #

    @classmethod
    def get(cls, object_id):
        """Retrieve a single object from NTB by its object id"""
        return cls(NTBObject.get_document(cls.identifier, object_id), _is_partial=True)

    @staticmethod
    def get_document(identifier, object_id):
        request = requests.get(
            '%s%s/%s/' % (Settings.ENDPOINT_URL, identifier, object_id),
            params={'api_key': Settings.API_KEY}
        )
        if request.status_code in [400, 404]:
            raise DocumentNotFound(
                "Document with identifier '%s' and object id '%s' wasn't found in Turbasen" % (identifier, object_id)
            )
        return request.json()

    @classmethod
    def lookup(cls):
        """Retrieve a complete list of these objects, partially fetched"""
        objects = Settings.CACHE.get('turbasen.%s.lookup' % cls.__name__)
        if objects is None:
            objects = [
                cls(document, _is_partial=True)
                for document in NTBObject._lookup_recursively(cls.identifier, skip=0, previous_results=[])
            ]
            Settings.CACHE.set('turbasen.%s.lookup' % cls.__name__, objects, cls.LOOKUP_CACHE_PERIOD)
        return objects

    #
    # Private static methods
    #

    @staticmethod
    def _lookup_recursively(identifier, skip, previous_results):
        response = requests.get(
            '%s%s' % (Settings.ENDPOINT_URL, identifier),
            params={
                'api_key': Settings.TURBASEN_API_KEY,
                'limit': Settings.LIMIT,
                'skip': skip,
                'status': u'Offentlig',  # Ignore Kladd, Privat, og Slettet
                'tilbyder': u'DNT',      # Future proofing, there might be other objects
            }
        ).json()

        for document in response['documents']:
            previous_results.append(document)

        if len(previous_results) == response['total']:
            return previous_results
        else:
            return NTBObject._lookup_recursively(
                identifier,
                skip=(skip + response['count']),
                previous_results=previous_results,
            )

class Omrade(NTBObject):
    identifier = u'områder'
    LOOKUP_CACHE_PERIOD = 60 * 60 * 24
    FIELDS = [
        u'navngiving',
        u'status',
        u'geojson',
        u'kommuner',
        u'fylker',
        u'beskrivelse',
        u'bilder',
    ]

    def __init__(self, document, *args, **kwargs):
        super(Omrade, self).__init__(document, *args, **kwargs)
        self.navn = document.get('navn')

    def __repr__(self):
        return (u'Område: %s (%s)' % (self.object_id, self.navn)).encode('utf-8')

class Sted(NTBObject):
    identifier = u'steder'
    LOOKUP_CACHE_PERIOD = 60 * 60 * 24
    FIELDS = [
        u'navngiving',
        u'status',
        u'navn_alt',
        u'ssr_id',
        u'geojson',
        u'områder',
        u'kommune',
        u'fylke',
        u'beskrivelse',
        u'adkomst',
        u'tilrettelagt_for',
        u'fasiliteter',
        u'lenker',
        u'byggeår',
        u'besøksstatistikk',
        u'betjeningsgrad',
        u'tags',
        u'grupper',
        u'bilder',
        u'steder',
        u'url',
        u'kart',
        u'turkart',
    ]

    def __init__(self, document, *args, **kwargs):
        super(Sted, self).__init__(document, *args, **kwargs)
        self.navn = document.get('navn')

    def __repr__(self):
        return (u'Sted: %s (%s)' % (self.object_id, self.navn)).encode('utf-8')
