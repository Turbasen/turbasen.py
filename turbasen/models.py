# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta
import json
import logging
import sys

import requests

from .decorators import requires_object_id, requires_not_partial
from .exceptions import DocumentNotFound, Unauthorized, InvalidDocument
from .settings import Settings
from .util import params_to_dotnotation
from . import events

logger = logging.getLogger('turbasen')

class NTBObject(object):
    COMMON_FIELDS = [
        'lisens',
        'navngiving',
        'status',
        'navn',
        'privat',
    ]

    COMMON_FIELDS_READONLY = [
        'tilbyder',
        'endret',
        'checksum',
    ]

    def __init__(self, _meta={}, **fields):
        self.object_id = _meta.get('id')
        self._is_partial = _meta.get('is_partial', False)
        self._extra = {}
        self._set_data(_meta.get('etag'), fields)

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

        repr = '<%s: %s%s: %s>' % (self.__class__.__name__, object_id, ' (partial)' if self._is_partial else '', navn)

        # Custom py2/3 compatibility handling. We're avoiding the 'six' library for now because YAGNI, but if these
        # explicit checks grow out of hand, consider replacing them with six.
        if sys.version_info.major == 2:
            return repr.encode('utf-8')
        else:
            return repr

    def __eq__(self, other):
        """Object equality relies on the object id being defined, and equal"""
        if type(self) != type(other):
            return False

        if not self.object_id:
            return False

        return self.object_id == other.object_id

    #
    # Attribute manipulation
    # - Partial objects have not all attributes assigned; when one is accessed, retrieve the entire document first
    #

    def __getattr__(self, name):
        """
        On attribute lookup failure, if the object is only partially retrieved, get the rest of its data and try again.
        Note that this method is only called whenever an attribute lookup *fails*.
        """

        # Verify that _is_partial (which is always set in __init__) actually is set. If not, we might be in some
        # low-level cache serialization state, in which case we don't want to apply our custom logic but just raise
        # the AttributeError.
        try:
            self.__getattribute__('_is_partial')
        except AttributeError:
            raise

        if self._is_partial and self.object_id is not None and not name.startswith('_'):
            # Note that we're ignoring internal non-existing attributes, which can occur in various situations, e.g.
            # when serializing for caching.
            logger.debug("[getattr %s.%s]: Accessed non-existing attribute on partial object; fetching document..." % (
                self.object_id,
                name,
            ))
            self._fetch()
            return getattr(self, name)
        else:
            # Default behavior - no such attribute
            # Manual py2/3 compatibility handling for encoding exception message
            if sys.version_info.major == 2:
                error_message = ("'%s' object has no attribute '%s'" % (
                    repr(self).decode('utf-8'),
                    name,
                )).encode('utf-8')
            else:
                error_message = "'%s' object has no attribute '%s'" % (self, name)
            raise AttributeError(error_message)

    #
    # Internal data handling
    #

    def get_data(self, include_common=True, include_extra=False):
        """
        Returns a dict of all data fields on this object. Set include_common to False to only return fields specific
        to this datatype. Set include_extra to False to exclude fields not recognized in our data model.
        """
        field_names = [self.FIELD_MAP_UNICODE[f] for f in self.FIELDS]
        if include_common:
            field_names += NTBObject.COMMON_FIELDS
        data = {
            field: getattr(self, field)
            for field in field_names
            if hasattr(self, field) and getattr(self, field) is not None
        }
        if include_extra:
            data.update(self._extra)
        return data

    def _set_data(self, etag, fields):
        """Save the given data on this object"""
        self._etag = etag
        self._saved = datetime.now()

        if '_id' in fields:
            new_object_id = fields.pop('_id')
            if self.object_id is not None and self.object_id != new_object_id:
                logger.warning("Replacing old object id '%s' with new object id '%s'" % (self.object_id, new_object_id))
            self.object_id = new_object_id

        for key, value in fields.items():
            if key in self.FIELDS:
                # Expected data fields
                setattr(self, self.FIELD_MAP_UNICODE.get(key, key), value)
            elif key in NTBObject.COMMON_FIELDS + NTBObject.COMMON_FIELDS_READONLY:
                # Expected common metadata
                setattr(self, key, value)
            else:
                # Unexpected extra attributes - group in the 'extra' dictionary
                self._extra[key] = value

        if self.object_id is not None and etag is not None and not self._is_partial:
            Settings.CACHE.set('turbasen.object.%s' % self.object_id, self, Settings.CACHE_GET_PERIOD)
            logger.debug("[set %s/%s]: Saved and cached with ETag: %s" % (self.identifier, self.object_id, self._etag))

    #
    # Data retrieval from Turbasen
    #

    @requires_object_id
    def _fetch(self):
        """For partial objects: Retrieve and set all document fields"""
        object = Settings.CACHE.get('turbasen.object.%s' % self.object_id)
        if object is None:
            logger.debug("[_fetch %s/%s]: Not in local cache, performing GET request..." % (self.identifier, self.object_id))
            headers, document = NTBObject._get_document(self.identifier, self.object_id)
            self._is_partial = False
            self._set_data(etag=headers['etag'], fields=document)
        else:
            logger.debug("[_fetch %s/%s]: Retrieved cached object, updating and refreshing..." % (self.identifier, self.object_id))
            self._is_partial = False
            self._set_data(etag=object._etag, fields=object.get_data())
            self._refresh()

    @requires_object_id
    @requires_not_partial
    def _refresh(self):
        """Refreshes the object if the ETag cache period is expired and the object is modified"""
        if self._etag is not None and self._saved + timedelta(seconds=Settings.ETAG_CACHE_PERIOD) > datetime.now():
            logger.debug("[refresh %s]: Object is younger than ETag cache period (%s), skipping ETag check" % (
                self.object_id,
                Settings.ETAG_CACHE_PERIOD,
            ))
            return

        logger.debug("[refresh %s]: ETag cache period expired, performing request..." % self.object_id)
        result = NTBObject._get_document(self.identifier, self.object_id, self._etag)
        if result is None:
            # Document is not modified, reset the etag check timeout
            logger.debug("[refresh %s]: Document was not modified" % self.object_id)
            self._saved = datetime.now()
            Settings.CACHE.set('turbasen.object.%s' % self.object_id, self, Settings.CACHE_GET_PERIOD)
        else:
            logger.debug("[refresh %s]: Document was modified, resetting fields..." % self.object_id)
            headers, document = result
            self._set_data(etag=headers['etag'], fields=document)

    #
    # Data push to Turbasen
    #

    @requires_not_partial
    def save(self, include_extra=False):
        if self.object_id:
            headers, document = self._put(include_extra=include_extra)
        else:
            headers, document = self._post(include_extra=include_extra)
            self.object_id = document.pop('_id')

        # Note that we're resetting all fields here. The main reason is to reset the etag and update metadata fields,
        # and although all other fields are reset, they should return as they were.
        self._set_data(etag="\"%s\"" % document['checksum'], fields=document)

    @requires_object_id
    def delete(self):
        params = {}
        if Settings.API_KEY is not None:
            params['api_key'] = Settings.API_KEY

        events.trigger('api.delete_object')
        request = requests.delete(
            '%s/%s/%s' % (Settings.ENDPOINT_URL, self.identifier, self.object_id),
            params=params,
        )
        if request.status_code in [400, 404]:
            raise DocumentNotFound(
                "Document with identifier '%s' and object id '%s' wasn't found in Turbasen" % (
                    self.identifier,
                    self.object_id,
                )
            )
        elif request.status_code in [401, 403]:
            raise Unauthorized(
                "Turbasen returned status code %s with the message: \"%s\"" % (
                    request.status_code,
                    request.json()['message'],
                )
            )

        if request.status_code != 204:
            logger.warning("Turbasen returned status code %s on DELETE; expected 204" % request.status_code)

        Settings.CACHE.delete('turbasen.object.%s' % self.object_id)
        self.object_id = None
        return request.headers

    @requires_not_partial
    def _post(self, include_extra=False):
        params = {}
        if Settings.API_KEY is not None:
            params['api_key'] = Settings.API_KEY

        events.trigger('api.post_object')
        request = requests.post(
            '%s/%s' % (Settings.ENDPOINT_URL, self.identifier),
            headers={'Content-Type': 'application/json; charset=utf-8'},
            params=params,
            # Note that we're not validating required fields, let the API handle that
            data=json.dumps(self.get_data(include_extra=include_extra)),
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

        if request.status_code != 201:
            logger.warning("Turbasen returned status code %s on POST; expected 201" % request.status_code)

        for warning in request.json().get('warnings', []):
            logger.warning("Turbasen POST warning: %s" % warning)

        return request.headers, request.json()['document']

    @requires_object_id
    @requires_not_partial
    def _put(self, include_extra=False):
        params = {}
        if Settings.API_KEY is not None:
            params['api_key'] = Settings.API_KEY

        events.trigger('api.put_object')
        request = requests.put(
            '%s/%s/%s' % (Settings.ENDPOINT_URL, self.identifier, self.object_id),
            headers={'Content-Type': 'application/json; charset=utf-8'},
            params=params,
            # Note that we're not validating required fields, let the API handle that
            data=json.dumps(self.get_data(include_extra=include_extra)),
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
        elif request.status_code == 404:
            raise DocumentNotFound(
                "Document with identifier '%s' and object id '%s' wasn't found in Turbasen" % (
                    self.identifier,
                    self.object_id,
                )
            )

        if request.status_code != 200:
            logger.warning("Turbasen returned status code %s on PUT; expected 200" % request.status_code)

        for warning in request.json().get('warnings', []):
            logger.warning("Turbasen PUT warning: %s" % warning)

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
            headers, document = NTBObject._get_document(cls.identifier, object_id)
            return cls(_meta={'id': document.pop('_id'), 'etag': headers['etag']}, **document)
        else:
            logger.debug("[get %s/%s]: Retrieved cached object, refreshing..." % (cls.identifier, object_id))
            object._refresh()
            return object

    @classmethod
    def lookup(cls, pages=None, params=dict()):
        """
        Retrieve a complete list of these objects, partially fetched.
        Arguments:
        - pages: Positive integer
            Optionally set to positive integer to limit the amount of pages iterated. `settings.LIMIT` decides the
            amount of objects per page.
        - params: Dictionary
            Add API filter parameters. Note the special parameter 'fields' which can be used to include more fields in
            the partial objects. Note also that the following params will not be included: 'limit', 'status', 'tilbyder'
        """
        params = params_to_dotnotation(params.copy())

        # If the 'fields' parameter contains a single value, wrap it in a list
        if 'fields' in params and type(params['fields']) != list:
            params['fields'] = [params['fields']]

        # Create a cache key with the dict's hash. Ensure the 'fields' iterable is a tuple, which is hashable. Use a
        # copy to avoid mutating the original dict, where we prefer to keep the unhashable list.
        params_copy = params.copy()
        if 'fields' in params_copy:
            params_copy['fields'] = tuple(params_copy['fields'])
        params_key = hash(frozenset(params_copy.items()))
        cache_key = 'turbasen.objects.%s.%s.%s' % (cls.identifier, pages, params_key)

        objects = Settings.CACHE.get(cache_key)
        if objects is None:
            logger.debug("[lookup %s (pages=%s)]: Not cached, performing GET request(s)..." % (cls.identifier, pages))
            objects = list(NTBObject.NTBIterator(cls, pages, params))
            Settings.CACHE.set(cache_key, objects, Settings.CACHE_LOOKUP_PERIOD)
        else:
            logger.debug("[lookup %s (pages=%s)]: Retrieved from cache" % (cls.identifier, pages))
        return objects

    #
    # Internal static data retrieval methods
    #

    @staticmethod
    def _get_document(identifier, object_id, etag=None):
        # Handle the special case of empty object_id provided; the resulting request would have returned a list lookup
        if object_id == '':
            raise DocumentNotFound("No documents have an empty object id")

        params = {}
        if Settings.API_KEY is not None:
            params['api_key'] = Settings.API_KEY

        headers = {}
        if etag is not None:
            headers['if-none-match'] = etag

        events.trigger('api.get_object')
        request = requests.get(
            '%s/%s/%s' % (Settings.ENDPOINT_URL, identifier, object_id),
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

        if request.status_code != 200:
            logger.warning("Turbasen returned status code %s on GET; expected 200" % request.status_code)

        return request.headers, request.json()

    #
    # Internal utilities
    #

    @staticmethod
    def _map_fieldnames(fields):
        """Returns a dict mapping of field names from unicode to ascii"""
        return {f: f.replace('æ', 'ae').replace('ø', 'o').replace('å', 'a') for f in fields}

    class NTBIterator:
        """Document iterator"""
        DEFAULT_FIELDS = ['navn', 'checksum', 'endret', 'status'] # Include checksum (etag)

        def __init__(self, cls, pages, params):
            self.cls = cls
            self.pages = pages
            self.params = params

            # Combine and add user-specified and default fields
            fields = set(self.DEFAULT_FIELDS + self.params.get('fields', []))
            self.params['fields'] = ','.join(fields)

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
            return self.cls(
                _meta={'id': document.pop('_id'), 'etag': "\"%s\"" % document['checksum'], 'is_partial': True},
                **document
            )

        def lookup_bulk(self):
            params = self.params

            # Set our default params, overwriting any duplicates
            params['limit'] = Settings.LIMIT
            params['status'] = 'Offentlig'  # Ignore Kladd, Privat, og Slettet
            params['tilbyder'] = 'DNT'      # Future proofing, there might be other objects
            params['skip'] = self.bulk_index

            if Settings.API_KEY is not None:
                params['api_key'] = Settings.API_KEY

            events.trigger('api.get_objects')
            request = requests.get('%s/%s' % (Settings.ENDPOINT_URL, self.cls.identifier), params=params)
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

class Bilde(NTBObject):
    identifier = 'bilder'
    FIELDS = [
        'geojson',
        'beskrivelse',
        'fotograf',
        'eier',
        'tags',
        'grupper',
        'img',
    ]
    FIELD_MAP_UNICODE = NTBObject._map_fieldnames(FIELDS)

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
        'grupper',
        'bilder',
        'steder',
        'url',
    ]
    FIELD_MAP_UNICODE = NTBObject._map_fieldnames(FIELDS)

class Omrade(NTBObject):
    identifier = 'områder'
    FIELDS = [
        'geojson',
        'kommuner',
        'fylker',
        'beskrivelse',
        'bilder',
    ]
    FIELD_MAP_UNICODE = NTBObject._map_fieldnames(FIELDS)

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
    FIELD_MAP_UNICODE = NTBObject._map_fieldnames(FIELDS)

class Tur(NTBObject):
    identifier = 'turer'
    FIELDS = [
        'geojson',
        'distanse',
        'retning',
        'områder',
        'fylker',
        'beskrivelse',
        'adkomst',
        'lenker',
        'gradering',
        'passer_for',
        'tilrettelagt_for',
        'sesong',
        'tidsbruk',
        'tags',
        'grupper',
        'bilder',
        'steder',
        'url',
    ]
    FIELD_MAP_UNICODE = NTBObject._map_fieldnames(FIELDS)
