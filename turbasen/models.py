# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import requests

from .settings import Settings
from .exceptions import DocumentNotFound, Unauthorized

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
            variable_name = field.replace('æ', 'ae').replace('ø', 'o').replace('å', 'a')
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
        params = {}

        if Settings.API_KEY is not None:
            params['api_key'] = Settings.API_KEY

        request = requests.get('%s%s/%s/' % (Settings.ENDPOINT_URL, identifier, object_id), params=params)
        if request.status_code in [400, 404]:
            raise DocumentNotFound(
                "Document with identifier '%s' and object id '%s' wasn't found in Turbasen" % (identifier, object_id)
            )
        elif request.status_code in [401, 403]:
            raise Unauthorized(
                "Turbasen returned status code %s with the message: \"%s\"" % (
                    request.status_code,
                    request.json()['message'],
                )
            )
        return request.json()

    @classmethod
    def lookup(cls, pages=1):
        """Retrieve a complete list of these objects, partially fetched. Specify how many pages you want retrieved
        (result count in a page is configured with LIMIT), or set to None to retrieve all documents."""
        return NTBObject.NTBIterator(cls, pages)

    class NTBIterator:
        """Document iterator"""
        def __init__(self, cls, pages):
            self.cls = cls
            self.pages = pages

        def __iter__(self):
            self.bulk_index = 0
            self.document_index = 0
            self.document_list = []
            self.exhausted = False
            return self

        def __next__(self):
            if self.document_index >= len(self.document_list):
                if self.exhausted:
                    raise StopIteration
                else:
                    self.lookup_bulk()

            self.document_index += 1
            document = self.document_list[self.document_index - 1]
            return self.cls(document, _is_partial=True)

        def lookup_bulk(self):
            params = {
                'limit': Settings.LIMIT,
                'skip': self.bulk_index,
                'status': 'Offentlig',  # Ignore Kladd, Privat, og Slettet
                'tilbyder': 'DNT',      # Future proofing, there might be other objects
            }

            if Settings.API_KEY is not None:
                params['api_key'] = Settings.API_KEY

            request = requests.get('%s%s' % (Settings.ENDPOINT_URL, self.cls.identifier), params=params)
            if request.status_code in [401, 403]:
                raise Unauthorized(
                    "Turbasen returned status code %s with the message: \"%s\"" % (
                        request.status_code,
                        request.json()['message'],
                    )
                )

            response = request.json()
            self.document_list = response['documents']
            self.document_index = 0
            self.bulk_index += len(self.document_list)

            if self.bulk_index == response['total']:
                # All documents retrieved
                self.exhausted = True
            elif self.pages is not None and self.bulk_index >= self.pages * Settings.LIMIT:
                # Specified page limit reached
                self.exhausted = True

class Omrade(NTBObject):
    identifier = 'områder'
    LOOKUP_CACHE_PERIOD = 60 * 60 * 24
    FIELDS = [
        'navngiving',
        'status',
        'geojson',
        'kommuner',
        'fylker',
        'beskrivelse',
        'bilder',
    ]

    def __init__(self, document, *args, **kwargs):
        super(Omrade, self).__init__(document, *args, **kwargs)
        self.navn = document.get('navn')

    def __repr__(self):
        return 'Område: %s (%s)' % (self.object_id, self.navn)

class Sted(NTBObject):
    identifier = 'steder'
    LOOKUP_CACHE_PERIOD = 60 * 60 * 24
    FIELDS = [
        'navngiving',
        'status',
        'navn_alt',
        'ssr_id',
        'geojson',
        'områder',
        'kommune',
        'fylke',
        'beskrivelse',
        'adkomst',
        'tilrettelagt_for',
        'fasiliteter',
        'lenker',
        'byggeår',
        'besøksstatistikk',
        'betjeningsgrad',
        'tags',
        'grupper',
        'bilder',
        'steder',
        'url',
        'kart',
        'turkart',
    ]

    def __init__(self, document, *args, **kwargs):
        super(Sted, self).__init__(document, *args, **kwargs)
        self.navn = document.get('navn')

    def __repr__(self):
        return 'Sted: %s (%s)' % (self.object_id, self.navn)
