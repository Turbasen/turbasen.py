.. turbasen.py documentation master file, created by
   sphinx-quickstart on Fri Jan 29 07:26:30 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

turbasen.py
=============================

Python client for `Nasjonal Turbase <http://www.nasjonalturbase.no/>`_,
featuring:

- :ref:`Object model for all datatypes <datatypes>`
- :ref:`Container API on instances to access document fields (dict-like)
  <document-fields>`
- :ref:`Exceptions abstract away HTTP status codes <exceptions>`
- :ref:`Automatic iteration over paginated list queries <static-methods>`
- :ref:`Handling partial documents returned from list queries
  <partial-documents>`
- :ref:`ETag handling with refresh on expiry <settings>`
- :ref:`Client caching <settings>`
- :ref:`Event triggers <events>`

Installation
-----------------------------

.. code-block:: bash

  pip install turbasen

.. _datatypes:

Datatypes
-----------------------------

.. py:class:: turbasen.Bilde

  `Images <http://www.nasjonalturbase.no/data/bilder/>`_

.. py:class:: turbasen.Gruppe

  `Groups <http://www.nasjonalturbase.no/data/grupper/>`_

.. py:class:: turbasen.Område

  `Areas <http://www.nasjonalturbase.no/data/omrader/>`_

.. py:class:: turbasen.Sted

  `Places <http://www.nasjonalturbase.no/data/steder/>`_

.. py:class:: turbasen.Tur

  `Trips <http://www.nasjonalturbase.no/data/turer/>`_

Environment variables
-----------------------------

``API_KEY``
  Your API key. Can also be specified via the ``API_KEY`` setting.

``ENDPOINT_URL``
  API endpoint. See the ``ENDPOINT_URL`` setting.

.. _settings:

Settings
-----------------------------

``ENDPOINT_URL = https://api.nasjonalturbase.no``
  API endpoint. Set to ``https://dev.nasjonalturbase.no`` for development.

``LIMIT = 20``
  Documents returned per page. API hard max limit is currently 50. Note that
  setting this to a low number when the use case is to retrieve all documents is
  inefficient.

``CACHE = DummyCache()``
  Can be set to a cache engine implementing a small subset of the Django cache
  API to enable caching.

``CACHE_LOOKUP_PERIOD = 60 * 60 * 24``
  Number of seconds a *list* cache is retained

``CACHE_GET_PERIOD = 60 * 60 * 24 * 30``
  Number of seconds an *object* cache is retained. Note that *ETag* may be
  checked and used to expire the cache if applicable, so this value should
  normally be high.

``ETAG_CACHE_PERIOD = 60 * 60``
  Number of seconds to ignore ``ETag`` checks and use local cache blindly.

``API_KEY = os.environ.get('API_KEY', '')``
  Get your API key at
  `Nasjonal Turbase Developer <https://developer.nasjonalturbase.no/>`_.



Example usage
-----------------------------

Initialization:

.. code-block:: python

  import turbasen
  turbasen.configure(LIMIT=3, ENDPOINT='https://dev.nasjonalturbase.no')

List documents, with some parameter filters:

.. code-block:: python

  turbasen.Sted.list(pages=1, params={
    'tilbyder': 'DNT',
    'status': 'Offentlig',
    'tags': 'Hytte',
  })

  # [<Sted: 52407fb375049e561500027d (partial): Øvre Grue>,
  #  <Sted: 52407fb375049e561500035a (partial): Ravnastua fjellstue>,
  #  <Sted: 52407fb375049e5615000356 (partial): Lahpoluoppal>]

Get single document:

.. code-block:: python

  sted = turbasen.Sted.get('546b36a511f41a9c00c0d4d9')
  # <Sted: 546b36a511f41a9c00c0d4d9: En liten hytte>

  sted['navn']
  # En liten hytte

  len(sted)
  # 17

Create and delete document:

.. code-block:: python

  sted = turbasen.Sted(
      lisens='Privat',
      status='Kladd',
      navn='Testcabin',
      beskrivelse='Testcabin',
      tags=['Hytte'],
  )

  sted.save()
  # API warning: {
  #   'code': 'missing_field',
  #   'field': 'navngiving',
  #   'resource': 'Document'
  # }

  sted.delete()


API
-----------------------------

.. _static-methods:

Static methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. py:function:: list(pages=None, params=dict())

   Return a list of documents. If ``pages`` is not ``None``, limits the results
   to ``pages`` pages with ``LIMIT`` documents on each page.

   Filter results with ``params``, or specify which ``fields`` should be
   returned to increase performance, avoiding extra fetches for
   :ref:`partial documents <partial-documents>`. See
   `the API documentation <http://www.nasjonalturbase.no/api/>`_.

.. py:function:: get(object_id)

  Retrieve a document of this datatype with the given object id.

.. _instance-methods:

Instance methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. py:function:: save()

  Save this document. If the document doesn't have an ``_id`` field, it will be
  assigned. Saving a :ref:`partial document <partial-documents>` will perform
  a ``PATCH`` request, only overwriting fields that are defined locally.

.. py:function:: delete()

  Delete this document. It must be saved (ie. have an ``_id`` field).

.. py:function:: get_field(key[, default])

  See `dict.get <https://docs.python.org/3/library/stdtypes.html?#dict.get>`_

.. _document-fields:

Document fields
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Instances are
`collections <https://docs.python.org/3/library/collections.html>`_, so document
fields are accessed as keys on a regular ``dict``. All
`dict methods <https://docs.python.org/3/library/stdtypes.html?#dict>`_ are
implemented, except for
`dict.get <https://docs.python.org/3/library/stdtypes.html?#dict.get>`_ which is
renamed to ``get_field``, see :ref:`instance methods <instance-methods>`.

.. _exceptions:

Exceptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. py:class:: turbasen.exceptions.DocumentNotFound

  Thrown when a request references to a document with an object id that doesn't
  exist.

.. py:class:: turbasen.exceptions.Unauthorized

  Thrown when a request returns a HTTP 401 Unathorized or 403 Forbidden status
  code.

.. py:class:: turbasen.exceptions.InvalidDocument

  Thrown when updating or creating a document with invalid data.

.. py:class:: turbasen.exceptions.ServerError

  Thrown when a request results in a 5xx server error response.

.. _partial-documents:

Partial documents
-----------------------------

Documents returned from calling ``list`` are not complete, but classified as
*partial*. When accessing a field on a partial document which does not exist,
a ``GET`` request is automatically performed under the hood to request the
entire document. If the accessed field now exists, it is returned as normal.

If you know you only need a few fields from a ``list`` call, it may be a good
idea to specify those in the params field like this:
``params={'fields': ['field1', 'field2']}`` to avoid performing a ``GET``
request for each of the documents in your list.

.. _events:

Events
-----------------------------


.. code-block:: python

  def handle_get_request():
      logger.debug("turbasen.py performed a GET request.")

  turbasen.handle_event('api.get_object', handle_get_request)

``api.get_object``
  GET request made for a single object

``api.get_objects``
  GET request for a new page with list of objects - called once for each new
  page

``api.post_object``
  POST request made with a new object

``api.put_object``
  PUT request made for an existing object

``api.delete_object``
  DELETE request made for an existing object
