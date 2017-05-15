from collections import UserDict
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
import json
import logging

import requests

from .exceptions import DocumentNotFound, Unauthorized, InvalidDocument, ServerError
from .settings import Settings
from .util import params_to_dotnotation
from . import events

logger = logging.getLogger('turbasen')

class NTBObject(UserDict):
    """Base class for Turbasen datatypes. Subclasses must define the `identifier` attribute.
    NTBObject subclasses UserDict in order to act as a collection for document fields."""
    def __init__(self, _is_partial=False, _etag=None, **fields):
        super().__init__(self)
        self._is_partial = _is_partial
        self._set_fields(_etag, fields)

    def __repr__(self):
        return '<%s: %s%s: %s>' % (
            self.__class__.__name__,
            self.get_field('_id', '?'),
            ' (partial)' if self._is_partial else '',
            self.get_field('navn', '?'),
        )

    def __eq__(self, other):
        """Object equality relies on the object id being defined, and equal"""
        if type(self) != type(other):
            return False

        if '_id' not in self or '_id' not in other:
            return False

        return self['_id'] == other['_id']

    #
    # Fields container API
    #

    def __getitem__(self, key):
        """Return the field with the given key. If the key is missing and this is a partial object,
        fetch remaining fields and retry."""
        try:
            return self.data[key]
        except KeyError:
            # If the key is missing on a partial object; fetch all fields and retry
            if self._is_partial and '_id' in self:
                logger.debug("[getitem %r.%s]: KeyError on partial object; fetching document" % (
                    self,
                    key,
                ))
                self._fetch()
                return self[key]
            else:
                raise

    def get_field(self, *args, **kwargs):
        """Renamed accessor for `dict.get`, because `get` is already in use in our subclass"""
        return self.data.get(*args, **kwargs)

    def _set_fields(self, etag, fields):
        """Assign a dict of fields on this object, along with an optional etag"""
        self._etag = etag
        self._saved = datetime.now()
        self.update(fields)

        if '_id' in self and self._etag is not None and not self._is_partial:
            Settings.CACHE.set('turbasen.object.%s' % self['_id'], self, Settings.CACHE_GET_PERIOD)
            logger.debug("[_set_fields %r]: Saved and cached with ETag: %s" % (self, self._etag))

    #
    # Object instance handling
    #

    def _fetch(self):
        """For partial objects: Retrieve and set all document fields"""
        assert '_id' in self
        assert self._is_partial

        object = Settings.CACHE.get('turbasen.object.%s' % self['_id'])
        if object is None:
            logger.debug("[_fetch %r]: Not in local cache, retrieving document" % self)
            headers, document = NTBObject._get_document(self.identifier, self['_id'])
            self._is_partial = False
            self._set_fields(etag=headers['etag'], fields=document)
        else:
            logger.debug("[_fetch %r]: Retrieved cached object, updating and refreshing" % self)
            self._is_partial = False
            self._set_fields(etag=object._etag, fields=object.items())
            self._refresh()

    def _refresh(self):
        """Based on object age, perform an ETag check, re-retrieving fields if object is modified"""
        assert '_id' in self
        assert not self._is_partial

        object_age = datetime.now() - self._saved
        etag_expiry = timedelta(seconds=Settings.ETAG_CACHE_PERIOD)
        if self._etag is not None and object_age < etag_expiry:
            logger.debug(
                "[_refresh %r]: Object age (%s) is less than ETag cache period (%s), skipping ETag "
                "check" % (
                    self,
                    object_age,
                    etag_expiry,
                )
            )
            return

        logger.debug("[_refresh %r]: ETag cache expired, retrieving document" % self)
        result = NTBObject._get_document(self.identifier, self['_id'], self._etag)
        if result is None:
            # Document is not modified, reset the etag check timeout
            logger.debug("[_refresh %r]: Document was not modified" % self)
            self._saved = datetime.now()
            Settings.CACHE.set('turbasen.object.%s' % self['_id'], self, Settings.CACHE_GET_PERIOD)
        else:
            # Document was modified, set new etag and fields
            logger.debug("[_refresh %r]: Document was modified, resetting fields" % self)
            headers, document = result
            self._set_fields(etag=headers['etag'], fields=document)

    def save(self):
        if '_id' not in self:
            # Create new object
            headers, document = self._post()
        elif not self._is_partial:
            # Not partial, PUT entire document
            headers, document = self._put()
        else:
            # Partial object - PATCH the fields that were changed
            headers, document = self._patch()
            self._is_partial = False

        # Note that we're resetting all fields here. The main reason is to reset the etag and update
        # metadata fields, and although all other fields are reset, they should return as they were.
        self._set_fields(etag="\"%s\"" % document['checksum'], fields=document)

    def delete(self):
        assert '_id' in self

        params = {'api_key': Settings.API_KEY}
        events.trigger('api.delete_object')
        request = requests.delete(
            '%s/%s/%s' % (Settings.ENDPOINT_URL, self.identifier, self['_id']),
            params=params,
        )
        NTBObject._handle_response(request, 'DELETE')
        Settings.CACHE.delete('turbasen.object.%s' % self['_id'])
        del self['_id']
        return request.headers

    def _post(self):
        assert not self._is_partial

        params = {'api_key': Settings.API_KEY}
        events.trigger('api.post_object')
        request = requests.post(
            '%s/%s' % (Settings.ENDPOINT_URL, self.identifier),
            headers={'Content-Type': 'application/json; charset=utf-8'},
            params=params,
            data=json.dumps(self.data),
        )
        NTBObject._handle_response(request, 'POST')
        return request.headers, request.json()['document']

    def _put(self):
        assert '_id' in self
        assert not self._is_partial

        params = {'api_key': Settings.API_KEY}
        events.trigger('api.put_object')
        request = requests.put(
            '%s/%s/%s' % (Settings.ENDPOINT_URL, self.identifier, self['_id']),
            headers={'Content-Type': 'application/json; charset=utf-8'},
            params=params,
            data=json.dumps(self.data),
        )
        NTBObject._handle_response(request, 'PUT')
        return request.headers, request.json()['document']

    def _patch(self):
        assert '_id' in self

        params = {'api_key': Settings.API_KEY}
        events.trigger('api.patch_object')
        request = requests.patch(
            '%s/%s/%s' % (Settings.ENDPOINT_URL, self.identifier, self['_id']),
            headers={'Content-Type': 'application/json; charset=utf-8'},
            params=params,
            data=json.dumps(self.data),
        )
        NTBObject._handle_response(request, 'PATCH')
        return request.headers, request.json()['document']

    #
    # Single document lookup
    #

    @classmethod
    def get(cls, object_id):
        """Retrieve a single object from Turbasen by its object id"""
        object = Settings.CACHE.get('turbasen.object.%s' % object_id)
        if object is None:
            logger.debug("[get %s/%s]: Not in local cache, performing GET request..." % (
                cls.identifier,
                object_id,
            ))
            headers, document = NTBObject._get_document(cls.identifier, object_id)
            return cls(_etag=headers['etag'], **document)
        else:
            logger.debug("[get %s/%s]: Retrieved cached object, refreshing..." % (
                cls.identifier,
                object_id,
            ))
            object._refresh()
            return object

    @staticmethod
    def _get_document(identifier, object_id, etag=None):
        # Handle the special case of empty object_id provided; the resulting request would have
        # returned a list lookup
        if object_id == '':
            raise DocumentNotFound("No documents have an empty object id")

        params = {'api_key': Settings.API_KEY}

        headers = {}
        if etag is not None:
            headers['if-none-match'] = etag

        events.trigger('api.get_object')
        request = requests.get(
            '%s/%s/%s' % (Settings.ENDPOINT_URL, identifier, object_id),
            headers=headers,
            params=params,
        )
        NTBObject._handle_response(request, 'GET')
        if request.status_code == 304 and etag is not None:
            return None
        else:
            return request.headers, request.json()

    #
    # List lookup
    #

    @classmethod
    def list(cls, pages=None, params=dict()):
        """
        Retrieve a complete list of these objects, partially fetched.
        Arguments:
        - pages: Positive integer
            Optionally set to positive integer to limit the amount of pages iterated.
            `settings.LIMIT` decides the amount of objects per page.
        - params: Dictionary
            Add API filter parameters. Note the special parameter 'fields' which can be used to
            include more fields in the partial objects. The following params are reserved for
            internal pagination: 'limit', 'skip'
        """
        params = params_to_dotnotation(params.copy())

        # If the 'fields' parameter contains a single value, wrap it in a list
        if 'fields' in params and type(params['fields']) != list:
            params['fields'] = [params['fields']]

        # Create a cache key with the dict's hash. Ensure the 'fields' iterable is a tuple, which is
        # hashable. Use a copy to avoid mutating the original dict, where we prefer to keep the
        # unhashable list.
        params_copy = params.copy()
        if 'fields' in params_copy:
            params_copy['fields'] = tuple(params_copy['fields'])
        params_key = hash(frozenset(params_copy.items()))
        cache_key = 'turbasen.objects.%s.%s.%s' % (cls.identifier, pages, params_key)

        objects = Settings.CACHE.get(cache_key)
        if objects is None:
            logger.debug("[list %s (pages=%s)]: Not cached, performing GET request(s)..." % (
                cls.identifier,
                pages,
            ))
            objects = list(NTBObject.NTBIterator(cls, pages, params))
            Settings.CACHE.set(cache_key, objects, Settings.CACHE_LOOKUP_PERIOD)
        else:
            logger.debug("[list %s (pages=%s)]: Retrieved from cache" % (cls.identifier, pages))
        return objects

    class NTBIterator:
        """Iterates a paginated document resultset from Turbasen"""
        DEFAULT_FIELDS = [
            # Add some reasonable default fields
            'navn',
            'endret',
            'status',
            # Add the checksum as well, for internal ETag handling
            'checksum',
        ]

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

        def __next__(self):
            if self.document_index >= len(self.document_list):
                if self.exhausted:
                    raise StopIteration
                else:
                    self.list_bulk()

            self.document_index += 1
            document = self.document_list[self.document_index - 1]
            return self.cls(
                _etag="\"%s\"" % document['checksum'],
                _is_partial=True,
                **document,
            )

        def list_bulk(self):
            params = self.params

            # API key
            params['api_key'] = Settings.API_KEY

            # Set pagination parameters
            params['limit'] = Settings.LIMIT
            params['skip'] = self.bulk_index

            events.trigger('api.get_objects')
            request = requests.get(
                '%s/%s' % (Settings.ENDPOINT_URL, self.cls.identifier),
                params=params,
            )
            NTBObject._handle_response(request, 'GET')
            response = request.json()
            self.document_list = response['documents']
            self.document_index = 0
            self.bulk_index += len(self.document_list)

            # If the very first bulk has no documents, stop the iteration instantly
            if not self.document_list:
                raise StopIteration

            if self.bulk_index == response['total']:
                # All documents retrieved
                self.exhausted = True
            elif self.pages is not None and self.bulk_index >= self.pages * Settings.LIMIT:
                # Specified page limit reached
                self.exhausted = True

    @staticmethod
    def _handle_response(request, method):
        """Handle responses from the API, logging warnings and raising any appropriate exception
        according to the HTTP status code"""
        try:
            response = request.json()
        except JSONDecodeError:
            response = {}

        for warning in response.get('warnings', []):
            logger.warning("API warning: %s" % warning)

        if request.status_code in [401, 403]:
            raise Unauthorized("HTTP %s: %s" % (request.status_code, response))

        elif request.status_code in [400, 404]:
            raise DocumentNotFound("HTTP %s: %s" % (request.status_code, response))

        elif request.status_code == 422:
            raise InvalidDocument("HTTP %s: %s" % (request.status_code, response))

        elif request.status_code in range(500, 512):
            raise ServerError("HTTP %s: %s" % (request.status_code, response))

        expected_response = {
            'GET': 200,
            'POST': 201,
            'PUT': 200,
            'PATCH': 200,
            'DELETE': 204,
        }

        if method in expected_response and expected_response[method] != request.status_code:
            logger.warning("HTTP %s: Expected status code %s; received %s" % (
                method,
                expected_response[method],
                request.status_code,
            ))
