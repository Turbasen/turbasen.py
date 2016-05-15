.. turbasen.py documentation master file, created by
   sphinx-quickstart on Fri Jan 29 07:26:30 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

turbasen.py
=============================

Python client for `Nasjonal Turbase <http://www.nasjonalturbase.no/>`_.

This client is opinionated about data fields and unrecognized fields require
explicit handling if wanted.

Installation
-----------------------------

.. code-block:: bash

  pip install turbasen


Datatypes
-----------------------------

.. py:class:: turbasen.Bilde

  `Images <http://www.nasjonalturbase.no/data/bilder.html>`_

.. py:class:: turbasen.Gruppe

  `Groups <http://www.nasjonalturbase.no/data/grupper.html>`_

.. py:class:: turbasen.Omrade

  `Areas <http://www.nasjonalturbase.no/data/omrader.html>`_

.. py:class:: turbasen.Sted

  `Places <http://www.nasjonalturbase.no/data/steder.html>`_

.. py:class:: turbasen.Tur

  `Trips <http://www.nasjonalturbase.no/data/turer.html>`_

  .. warning::

    Not yet implemented.

Environment variables
-----------------------------

``API_KEY``
  Your API key. Can also be specified via the ``API_KEY`` setting.

``ENDPOINT_URL``
  API endpoint. See the ``ENDPOINT_URL`` setting.

Settings
-----------------------------

``ENDPOINT_URL = https://api.nasjonalturbase.no``
  API endpoint. Set to ``https://dev.nasjonalturbase.no`` for development.

``LIMIT = 20``
  Objects returned per page. API hard max limit is currently 50. Note that
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
  Number of seconds to ignore ``Etag`` checks and use local cache blindly.

``API_KEY = os.environ.get('API_KEY')``
  API key is currently required for access.



Usage
-----------------------------

.. code-block:: python

  # Initialization
  import turbasen
  turbasen.configure(LIMIT=3, ENDPOINT='https://dev.nasjonalturbase.no')

  # Lookup partial documents
  turbasen.Sted.lookup(pages=1)
  # [<Sted: 546b36a511f41a9c00c0d4d9 (partial): En liten hytte>,
  #  <Sted: 546a051011f41a9c00c0d4cc (partial): Snøhulen>,
  #  <Sted: 555f1f4206b9ce06003405c5 (partial): Strømfoss>]

  # Add filter parameters
  turbasen.Sted.lookup(pages=1, params={'tags': 'Hytte'})
  # [<Sted: 52407fb375049e561500027d (partial): Øvre Grue>,
  #  <Sted: 52407fb375049e561500035a (partial): Ravnastua fjellstue>,
  #  <Sted: 52407fb375049e5615000356 (partial): Lahpoluoppal>]

  # Get single document
  sted = turbasen.Sted.get('546b36a511f41a9c00c0d4d9')
  # <Sted: 546b36a511f41a9c00c0d4d9: En liten hytte>
  sted.geojson
  # {
  #  'coordinates': [8.2912015914917, 60.12502756386393],
  #  'type': 'Point'
  # }
  len(sted.get_data().keys())
  # 12

  # Save document
  sted.save()

  # Unrecognized fields are discarded by default and require
  # explicit handling explicitly if wanted
  len(sted.get_data(include_extra=True).keys())
  # 13
  {
      k: v
      for k, v in s.get_data(include_extra=True).items()
      if k not in s.get_data()
  }
  # {'unknown_key': 'foo'}
  sted.save(include_extra=True)

  # Create and delete document
  sted = turbasen.Sted(
      lisens='Privat',
      status='Kladd',
      navn='Testcabin',
      beskrivelse='Testcabin',
      tags=['Hytte'],
  )
  sted.save()
  # Turbasen POST warning: {
  #   'resource': 'Document',
  #   'field': 'navngiving',
  #   'code': 'missing_field',
  # }
  sted.delete()


API
-----------------------------

Static methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. py:function:: lookup(pages=None, params=dict())

   Return an iterator yielding all objects of this class object type. Limit the
   number of objects to the number of ``pages`` wanted where each page contains
   ``LIMIT`` objects from the settings.

   Parameters passed in the ``params`` dict are forwarded to the API. These may
   be used to filter the query, or specify which ``fields`` should be returned
   to increase performance, avoiding extra fetches for
   :ref:`partial objects <partial-objects>`.

.. py:function:: get(object_id)

  Retrieve a document of this class object type. Raises
  ``turbasen.exceptions.DocumentNotFound`` if the document doesn't exist.

Instance methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. py:function:: get_data(self, include_common=True, include_extra=False)

  Return a dictionary of all data in this document.

  Set ``include_common`` to ``False`` to exclude fields that are common for all
  objects, returning only fields specific to the current object type.

  Set ``include_extra`` to ``True`` to include unrecognized fields.

.. py:function:: delete()

  Delete the current object. It must be saved (ie. have an ``object_id``).

Exceptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. py:class:: turbasen.exceptions.DocumentNotFound

  Thrown when a ``GET`` request for a document with a given object id isn't
  found

.. py:class:: turbasen.exceptions.Unauthorized

  Thrown when a request returns a HTTP 401 Unathorized or 403 Forbidden status
  code.

.. py:class:: turbasen.exceptions.InvalidDocument

  Thrown when updating or creating a document with invalid data.

.. _partial-objects:

Partial objects
-----------------------------

When using ``lookup``, not all document data is retrieved. The objects returned
are classified as *partial*. On attribute lookup, if the attribute doesn't
exist, a ``GET`` request is automatically performed under the hood to request
the entire document, and if the attribute is found on the complete object, it is
returned as normal.

If you know you only need a few fields from a lookup, it may be a good idea to
specify those in the params field like this:
``params={'fields': ['field1', 'field2']}`` to avoid performing a ``GET``
request for each of the objects in your list.

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
