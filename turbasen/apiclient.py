from datetime import datetime, timedelta
import json
import logging

import requests

from .exceptions import DocumentNotFound, Unauthorized, InvalidDocument
from .settings import Settings
from .util import params_to_dotnotation
from . import events

logger = logging.getLogger('turbasen')

class NTBObject(object):
    def __init__(self, _is_partial=False, _etag=None, **fields):
        self._is_partial = _is_partial
        self._fields = {}
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

    def __len__(self):
        return len(self._fields)

    def __getitem__(self, key):
        """Return the field with the given key. If the key is missing and this is a partial object,
        fetch remaining fields and retry."""
        try:
            return self._fields[key]
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

    def __setitem__(self, key, value):
        self._fields[key] = value

    def __delitem__(self, key):
        del self._fields[key]

    def __contains__(self, item):
        return item in self._fields

    def __iter__(self):
        return iter(self._fields)

    def clear(self, *args, **kwargs):
        return self._fields.clear(*args, **kwargs)

    def copy(self, *args, **kwargs):
        return self._fields.copy(*args, **kwargs)

    def get_field(self, *args, **kwargs):
        return self._fields.get(*args, **kwargs)

    def items(self, *args, **kwargs):
        return self._fields.items(*args, **kwargs)

    def keys(self, *args, **kwargs):
        return self._fields.keys(*args, **kwargs)

    def pop(self, *args, **kwargs):
        return self._fields.pop(*args, **kwargs)

    def popitem(self, *args, **kwargs):
        return self._fields.popitem(*args, **kwargs)

    def setdefault(self, *args, **kwargs):
        return self._fields.setdefault(*args, **kwargs)

    def update(self, *args, **kwargs):
        return self._fields.update(*args, **kwargs)

    def values(self, *args, **kwargs):
        return self._fields.values(*args, **kwargs)

    def _set_fields(self, etag, fields):
        """Assign a dict of fields on this object, along with an optional etag"""
        self._etag = etag
        self._saved = datetime.now()
        self.update(fields)

        if '_id' in self and self._etag is not None and not self._is_partial:
            Settings.CACHE.set('turbasen.object.%s' % self['_id'], self, Settings.CACHE_GET_PERIOD)
            logger.debug("[set %s/%s]: Saved and cached with ETag: %s" % (self.identifier, self['_id'], self._etag))

    #
    # Object instance handling
    #

    def _fetch(self):
        """For partial objects: Retrieve and set all document fields"""
        assert '_id' in self
        assert self._is_partial

        object = Settings.CACHE.get('turbasen.object.%s' % self['_id'])
        if object is None:
            logger.debug("[_fetch %s/%s]: Not in local cache, performing GET request..." % (self.identifier, self['_id']))
            headers, document = NTBObject._get_document(self.identifier, self['_id'])
            self._is_partial = False
            self._set_fields(etag=headers['etag'], fields=document)
        else:
            logger.debug("[_fetch %s/%s]: Retrieved cached object, updating and refreshing..." % (self.identifier, self['_id']))
            self._is_partial = False
            self._set_fields(etag=object._etag, fields=object.items())
            self._refresh()

    def _refresh(self):
        """Based on object age, perform an ETag check, re-retrieving fields if object is modified"""
        assert '_id' in self
        assert not self._is_partial

        if self._etag is not None and self._saved + timedelta(seconds=Settings.ETAG_CACHE_PERIOD) > datetime.now():
            logger.debug("[_refresh %s]: Object is younger than ETag cache period (%s), skipping ETag check" % (
                self['_id'],
                Settings.ETAG_CACHE_PERIOD,
            ))
            return

        logger.debug("[_refresh %s]: ETag cache period expired, performing request..." % self['_id'])
        result = NTBObject._get_document(self.identifier, self['_id'], self._etag)
        if result is None:
            # Document is not modified, reset the etag check timeout
            logger.debug("[_refresh %s]: Document was not modified" % self['_id'])
            self._saved = datetime.now()
            Settings.CACHE.set('turbasen.object.%s' % self['_id'], self, Settings.CACHE_GET_PERIOD)
        else:
            # Document was modified, set new etag and fields
            logger.debug("[_refresh %s]: Document was modified, resetting fields..." % self['_id'])
            headers, document = result
            self._set_fields(etag=headers['etag'], fields=document)

    def save(self):
        assert not self._is_partial

        if '_id' in self:
            headers, document = self._put()
        else:
            headers, document = self._post()

        # Note that we're resetting all fields here. The main reason is to reset the etag and update metadata fields,
        # and although all other fields are reset, they should return as they were.
        self._set_fields(etag="\"%s\"" % document['checksum'], fields=document)

    def delete(self):
        assert '_id' in self

        params = {'api_key': Settings.API_KEY}
        events.trigger('api.delete_object')
        request = requests.delete(
            '%s/%s/%s' % (Settings.ENDPOINT_URL, self.identifier, self['_id']),
            params=params,
        )
        if request.status_code in [400, 404]:
            raise DocumentNotFound(
                "Document with identifier '%s' and object id '%s' wasn't found in Turbasen" % (
                    self.identifier,
                    self['_id'],
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
            # Note that we're not validating required fields, let the API handle that
            data=json.dumps(self._fields),
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

    def _put(self):
        assert '_id' in self
        assert not self._is_partial

        params = {'api_key': Settings.API_KEY}
        events.trigger('api.put_object')
        request = requests.put(
            '%s/%s/%s' % (Settings.ENDPOINT_URL, self.identifier, self['_id']),
            headers={'Content-Type': 'application/json; charset=utf-8'},
            params=params,
            # Note that we're not validating required fields, let the API handle that
            data=json.dumps(self._fields),
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
                    self['_id'],
                )
            )

        if request.status_code != 200:
            logger.warning("Turbasen returned status code %s on PUT; expected 200" % request.status_code)

        for warning in request.json().get('warnings', []):
            logger.warning("Turbasen PUT warning: %s" % warning)

        return request.headers, request.json()['document']

    #
    # Single document lookup
    #

    @classmethod
    def get(cls, object_id):
        """Retrieve a single object from Turbasen by its object id"""
        object = Settings.CACHE.get('turbasen.object.%s' % object_id)
        if object is None:
            logger.debug("[get %s/%s]: Not in local cache, performing GET request..." % (cls.identifier, object_id))
            headers, document = NTBObject._get_document(cls.identifier, object_id)
            return cls(_etag=headers['etag'], **document)
        else:
            logger.debug("[get %s/%s]: Retrieved cached object, refreshing..." % (cls.identifier, object_id))
            object._refresh()
            return object

    @staticmethod
    def _get_document(identifier, object_id, etag=None):
        # Handle the special case of empty object_id provided; the resulting request would have returned a list lookup
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
    # List lookup
    #

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
            the partial objects. The following params are reserved for internal pagination:
            'limit', 'skip'
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

        def __next__(self):
            if self.document_index >= len(self.document_list):
                if self.exhausted:
                    raise StopIteration
                else:
                    self.lookup_bulk()

            self.document_index += 1
            document = self.document_list[self.document_index - 1]
            return self.cls(
                _etag="\"%s\"" % document['checksum'],
                _is_partial=True,
                **document,
            )

        def lookup_bulk(self):
            params = self.params

            # API key
            params['api_key'] = Settings.API_KEY

            # Set pagination parameters
            params['limit'] = Settings.LIMIT
            params['skip'] = self.bulk_index

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
