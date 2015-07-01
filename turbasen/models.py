# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta
import json
import logging
import sys

import requests

from .settings import Settings
from .exceptions import DocumentNotFound, Unauthorized, InvalidDocument
from . import events

logger = logging.getLogger('turbasen')

class NTBObject(object):
    COMMON_FIELDS = [
        'tilbyder',
        'endret',
        'lisens',
        'navngiving',
        'status',
        'navn',
    ]

    def __init__(self, id=None, etag=None, is_partial=False, **fields):
        self.object_id = id
        self._is_partial = is_partial
        self._extra = {}
        self.set_data(etag, **fields)

    def __repr__(self):
        # Since repr may be called during an AttributeError, we have to avoid __getattr__ when seeing if object_id and
        # navn are available, or we might end up in an infinite loop. It's not catchable, because fetch would raise an
        # AttributeError, which would try to build a representation, which would try to get an unavailable attribute,
        # and so on.
        try:
            object_id = self.__getattribute__('object_id')
        except AttributeError:
            object_id = '?'

        try:
            navn = self.__getattribute__('navn')
        except AttributeError:
            navn = '?'

        repr = '<%s: %s (%s)>' % (self.__class__.__name__, object_id, navn)

        # Custom py2/3 compatibility handling. We're avoiding the 'six' library for now because YAGNI, but if these
        # explicit checks grow out of hand, consider replacing them with six.
        if sys.version_info.major == 2:
            return repr.encode('utf-8')
        else:
            return repr

    #
    # Attribute manipulation
    # - Partial objects have not all attributes assigned; when one is accessed, retrieve the entire document first
    #

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
            raise AttributeError("'%s' object has no attribute '%s'" % (self, name))

    #
    # Internal data handling
    #

    def set_data(self, etag, **fields):
        """Save the given data on this object"""
        self._etag = etag
        self._saved = datetime.now()

        for key, value in fields.items():
            if key in self.FIELDS:
                # Expected data fields
                setattr(self, self.FIELD_MAP_UNICODE.get(key, key), value)
            elif key in NTBObject.COMMON_FIELDS:
                # Expected common metadata
                setattr(self, key, value)
            else:
                # Unexpected extra attributes - group in the 'extra' dictionary
                self._extra[key] = value

        Settings.CACHE.set('turbasen.object.%s' % self.object_id, self, Settings.CACHE_GET_PERIOD)
        logger.debug("[set %s/%s]: Saved and cached with ETag: %s" % (self.identifier, self.object_id, self._etag))

    #
    # Data retrieval from Turbasen
    #

    def fetch(self):
        """Retrieve this object's entire document unconditionally (does not use ETag)"""
        headers, document = NTBObject.get_document(self.identifier, self.object_id)
        self.set_data(headers['etag'], **document)

    def refresh(self):
        """If the object is expired, refetch it (using the local ETag)"""
        if self._etag is not None and self._saved + timedelta(seconds=Settings.ETAG_CACHE_PERIOD) > datetime.now():
            logger.debug("[refresh %s]: Object is younger than ETag cache period (%s), skipping ETag check" % (
                self.object_id,
                Settings.ETAG_CACHE_PERIOD,
            ))
            return

        logger.debug("[refresh %s]: ETag cache period expired, performing request..." % self.object_id)
        result = NTBObject.get_document(self.identifier, self.object_id, self._etag)
        if result is None:
            # Document is not modified, reset the etag check timeout
            logger.debug("[refresh %s]: Document was not modified" % self.object_id)
            self._saved = datetime.now()
            Settings.CACHE.set('turbasen.object.%s' % self.object_id, self, Settings.CACHE_GET_PERIOD)
        else:
            logger.debug("[refresh %s]: Document was modified, resetting fields..." % self.object_id)
            headers, document = result
            self.set_data(headers['etag'], **document)

    #
    # Data push to Turbasen
    #

    def save(self):
        if self.object_id:
            headers, document = self.put()
        else:
            headers, document = self.post()
            self.object_id = document['_id']

        # Note that we're resetting all fields here. The main reason is to reset the etag and update metadata fields,
        # and although all other fields are reset, they should return as they were.
        self.set_data(etag=document.pop('checksum'), **document)

    def post(self):
        params = {}
        if Settings.API_KEY is not None:
            params['api_key'] = Settings.API_KEY

        data = {field: getattr(self, self.FIELD_MAP_UNICODE[field]) for field in self.FIELDS}

        events.trigger('api.post_object')
        request = requests.post(
            '%s%s' % (Settings.ENDPOINT_URL, self.identifier),
            headers={'Content-Type': 'application/json; charset=utf-8'},
            params=params,
            data=json.dumps(data),
        )
        if request.status_code in [400, 422]:
            raise InvalidDocument(
                "Turbasen returned status code %s with the message: \"%s\" and the following errors: \"%s\"" % (
                    request.status_code,
                    request.json()['message'],
                    request.json().get('errors', ''),
                )
            )
        elif request.status_code in [401, 403]:
            raise Unauthorized(
                "Turbasen returned status code %s with the message: \"%s\"" % (
                    request.status_code,
                    request.json()['message'],
                )
            )

        for warning in request.json().get('warnings', []):
            logger.warning("Turbasen POST warning: %s" % warning)

        return request.headers, request.json()['document']

    #
    # Public static data retrieval methods
    #

    @classmethod
    def get(cls, object_id):
        """Retrieve a single object from Turbasen by its object id"""
        object = Settings.CACHE.get('turbasen.object.%s' % object_id)
        if object is None:
            logger.debug("[get %s/%s]: Not in local cache, performing GET request..." % (cls.identifier, object_id))
            headers, document = NTBObject.get_document(cls.identifier, object_id)
            return cls(id=document.pop('_id'), etag=headers['etag'], **document)
        else:
            logger.debug("[get %s/%s]: Retrieved cached object, refreshing..." % (cls.identifier, object_id))
            object.refresh()
            return object

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

    #
    # Internal static data retrieval methods
    #

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
            '%s%s/%s' % (Settings.ENDPOINT_URL, identifier, object_id),
            headers=headers,
            params=params,
        )
        if request.status_code == 304 and etag is not None:
            return None
        elif request.status_code in [400, 404]:
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

        return request.headers, request.json()

    #
    # Internal utilities
    #

    @staticmethod
    def _map_fieldnames(fields):
        """Returns a tuple of dict mapping of field names unicode -> ascii, and ascii -> unicode"""
        return (
            {f: f.replace('æ', 'ae').replace('ø', 'o').replace('å', 'a') for f in fields},
            {f.replace('æ', 'ae').replace('ø', 'o').replace('å', 'a'): f for f in fields},
        )

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
            return self.cls(id=document.pop('_id'), etag=document['checksum'], is_partial=True, **document)

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

class Gruppe(NTBObject):
    identifier = 'grupper'
    FIELDS = [
        'geojson',
        'områder',
        'kommuner',
        'fylker',
        'organisasjonsnr',
        'beskrivelse',
        'logo',
        'ansatte',
        'lenker',
        'kontaktinfo',
        'tags',
        'foreldregruppe',
        'privat',
        'grupper'
        'bilder',
        'steder',
        'url',
    ]
    FIELD_MAP_UNICODE, FIELD_MAP_ASCII = NTBObject._map_fieldnames(FIELDS)

class Omrade(NTBObject):
    identifier = 'områder'
    FIELDS = [
        'geojson',
        'kommuner',
        'fylker',
        'beskrivelse',
        'bilder',
    ]
    FIELD_MAP_UNICODE, FIELD_MAP_ASCII = NTBObject._map_fieldnames(FIELDS)

class Sted(NTBObject):
    identifier = 'steder'
    FIELDS = [
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
    FIELD_MAP_UNICODE, FIELD_MAP_ASCII = NTBObject._map_fieldnames(FIELDS)
