# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta
import logging
import sys

import requests

from .settings import Settings
from .exceptions import DocumentNotFound, Unauthorized
from . import events

logger = logging.getLogger('turbasen')

class NTBObject(object):
    def __init__(self, etag, document, _is_partial=False):
        self._etag = etag
        self._saved = datetime.now()

        self.object_id = document['_id']
        self.tilbyder = document['tilbyder']
        self.endret = document['endret']
        self.lisens = document['lisens']
        self.status = document['status']
        self._is_partial = _is_partial

        # The 'navn' field may or may not be defined
        self.navn = document.get('navn')

    def __getattr__(self, name):
        """On attribute lookup failure, if the object is only partially retrieved, get the rest of its data and try
        again"""
        if not name.startswith('_') and self._is_partial:
            # Note that we're ignoring internal non-existing attributes, which can occur in various situations, e.g.
            # when serializing for caching.
            logger.debug("[getattr %s.%s]: Accessed non-existing attribute on partial object; fetching document..." % (
                self.object_id,
                name,
            ))
            self.fetch()
            self._is_partial = False
            return getattr(self, name)
        else:
            # Default behavior - no such attribute
            raise AttributeError

    def fetch(self):
        """Retrieve this object's entire document"""
        headers, document = NTBObject.get_document(self.identifier, self.object_id)
        self.set_document(headers, document)

    def refresh(self):
        """Check if the object is modified, and if so, reset its data"""
        if self._saved + timedelta(seconds=Settings.ETAG_CACHE_PERIOD) > datetime.now():
            logger.debug("[refresh %s]: Object is younger than ETag cache period (%s), skipping ETag check" % (
                self.object_id,
                Settings.ETAG_CACHE_PERIOD,
            ))
            return

        logger.debug("[refresh %s]: ETag cache period expired, performing request..." % self.object_id)
        result = NTBObject.get_document(self.identifier, self.object_id, self._etag)
        if result is None:
            # Document is not modified
            logger.debug("[refresh %s]: Document was not modified" % self.object_id)
            return
        else:
            logger.debug("[refresh %s]: Document was modified, resetting fields..." % self.object_id)
            headers, document = result
            self.set_document(headers, document)

    def set_document(self, headers, document):
        self._etag = headers['etag']
        self._saved = datetime.now()
        for field in self.FIELDS:
            variable_name = field.replace('æ', 'ae').replace('ø', 'o').replace('å', 'a')
            setattr(self, variable_name, document.get(field))
        Settings.CACHE.set('turbasen.object.%s' % self.object_id, self, Settings.CACHE_GET_PERIOD)
        logger.debug("[set %s/%s]: Saved and cached with ETag: %s" % (self.identifier, self.object_id, self._etag))

    #
    # Lookup static methods
    #

    @classmethod
    def get(cls, object_id):
        """Retrieve a single object from NTB by its object id"""
        object = Settings.CACHE.get('turbasen.object.%s' % object_id)
        if object is None:
            logger.debug("[get %s/%s]: Not in local cache, performing GET request..." % (cls.identifier, object_id))
            headers, document = NTBObject.get_document(cls.identifier, object_id)
            object = cls(headers['etag'], document)
            object.set_document(headers, document)
            return object
        else:
            logger.debug("[get %s/%s]: Retrieved cached object, refreshing..." % (cls.identifier, object_id))
            object.refresh()
            return object

    @staticmethod
    def get_document(identifier, object_id, etag=None):
        params = {}
        if Settings.API_KEY is not None:
            params['api_key'] = Settings.API_KEY

        headers = {}
        if etag is not None:
            headers['if-none-match'] = etag

        events.trigger('api.get_object')
        request = requests.get(
            '%s%s/%s/' % (Settings.ENDPOINT_URL, identifier, object_id),
            headers=headers,
            params=params,
        )
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
        elif request.status_code == 304 and etag is not None:
            return None

        return request.headers, request.json()

    @classmethod
    def lookup(cls, pages=1):
        """Retrieve a complete list of these objects, partially fetched. Specify how many pages you want retrieved
        (result count in a page is configured with LIMIT), or set to None to retrieve all documents."""
        objects = Settings.CACHE.get('turbasen.objects.%s.%s' % (cls.identifier, pages))
        if objects is None:
            logger.debug("[lookup %s (pages=%s)]: Not cached, performing GET request(s)..." % (cls.identifier, pages))
            objects = list(NTBObject.NTBIterator(cls, pages))
            Settings.CACHE.set(
                'turbasen.objects.%s.%s' % (cls.identifier, pages),
                objects,
                Settings.CACHE_LOOKUP_PERIOD,
            )
        else:
            logger.debug("[lookup %s (pages=%s)]: Retrieved from cache" % (cls.identifier, pages))
        return objects

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

        def next(self):
            """For python2 compatibility"""
            return self.__next__()

        def __next__(self):
            if self.document_index >= len(self.document_list):
                if self.exhausted:
                    raise StopIteration
                else:
                    self.lookup_bulk()

            self.document_index += 1
            document = self.document_list[self.document_index - 1]
            return self.cls(document['checksum'], document, _is_partial=True)

        def lookup_bulk(self):
            params = {
                'limit': Settings.LIMIT,
                'skip': self.bulk_index,
                'status': 'Offentlig',  # Ignore Kladd, Privat, og Slettet
                'tilbyder': 'DNT',      # Future proofing, there might be other objects
                'fields': ','.join(['navn', 'checksum', 'endret', 'status']), # Include checksum (etag)
            }

            if Settings.API_KEY is not None:
                params['api_key'] = Settings.API_KEY

            events.trigger('api.get_objects')
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
    FIELDS = [
        'navngiving',
        'status',
        'geojson',
        'kommuner',
        'fylker',
        'beskrivelse',
        'bilder',
    ]

    def __repr__(self):
        repr = '<Område: %s (%s)>' % (self.object_id, self.navn)
        # Custom py2/3 compatibility handling. We're avoiding the 'six' library for now because YAGNI, but if these
        # explicit checks grow out of hand, consider replacing them with six.
        if sys.version_info.major == 2:
            return repr.encode('utf-8')
        else:
            return repr

class Sted(NTBObject):
    identifier = 'steder'
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

    def __repr__(self):
        repr = '<Sted: %s (%s)>' % (self.object_id, self.navn)
        # Custom py2/3 compatibility handling. We're avoiding the 'six' library for now because YAGNI, but if these
        # explicit checks grow out of hand, consider replacing them with six.
        if sys.version_info.major == 2:
            return repr.encode('utf-8')
        else:
            return repr
