Features
========
Below is a list of main features that any EVE-powered APIs can expose. Most of
these features can be experienced live by consuming the Demo API (see
:ref:`demo`).

Emphasis on REST
----------------
The Eve project aims to provide the best possible REST-compliant API
implementation. Fundamental REST_ principles like *separation of concerns*,
*stateless and layered system*, *cacheability*, *uniform interface* have been
kept into consideration while designing the core API.

Full range of CRUD operations
-----------------------------
APIs can support the full range of CRUD_ operations. Within the same API, you
can have a read-only resource accessible at one endpoint, along with a fully
editable resource at another endpoint. The following table shows Eve's
implementation of CRUD via REST:

======= ========= ===================
Action  HTTP Verb Context 
======= ========= ===================
Create  POST      Collection
Read    GET, HEAD Collection/Document
Update  PATCH     Document
Replace PUT       Document
Delete  DELETE    Collection/Document
======= ========= ===================

Overriding HTTP Methods
~~~~~~~~~~~~~~~~~~~~~~~
As a fallback for the odd client not supporting any of these methods, the API
will gladly honor ``X-HTTP-Method-Override`` requests. For example a client not
supporting the ``PATCH`` method could send a ``POST`` request with
a ``X-HTTP-Method-Override: PATCH`` header.  The API would then perform
a ``PATCH``, overriding the original request method.

Customizable resource endpoints
-------------------------------
By default, Eve will make known database collections available as resource
endpoints (persistent identifiers in REST idiom). So a database ``people``
collection will be avaliable at the ``example.com/people`` API endpoint.  You
can customize the URIs though, so the API endpoint could become, say,
``example.com/customers/overseas``. Consider the following request:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people
    HTTP/1.1 200 OK

The response payload will look something like this:

.. code-block:: javascript
    
    {
        "_items": [
            {
                "firstname": "Mark", 
                "lastname": "Green", 
                "born": "Sat, 23 Feb 1985 12:00:00 GMT", 
                "role": ["copy", "author"], 
                "location": {"city": "New York", "address": "4925 Lacross Road"}, 
                "_id": "50bf198338345b1c604faf31",
                "updated": "Wed, 05 Dec 2012 09:53:07 GMT", 
                "created": "Wed, 05 Dec 2012 09:53:07 GMT", 
                "etag": "ec5e8200b8fa0596afe9ca71a87f23e71ca30e2d", 
                "_links": {
                    "self": {"href": "eve-demo.herokuapp.com:5000/people/50bf198338345b1c604faf31", "title": "person"},
                },
            },
            ...
        ],
        "_links": {
            "self": {"href": "eve-demo.herokuapp.com:5000/people", "title": "people"}, 
            "parent": {"href": "eve-demo.herokuapp.com:5000", "title": "home"}
        }
    }


The ``_items`` list contains the requested data. Along with its own fields,
each item provides some important, additional fields:

=========== =================================================================
Field       Description
=========== =================================================================
``created`` item creation date.
``updated`` item last updated on.
``etag``    ETag, to be used for concurrency control and conditional requests. 
``_id``     unique item key, also needed to access the individual item endpoint.
=========== =================================================================

These additional fields are automatically handled by the API (clients don't
need to provide them when adding/editing resources).

The ``_links`` list provides HATEOAS_ directives.

.. _custom_item_endpoints:

Customizable, multiple item endpoints
-------------------------------------
Resources can or cannot expose individual item endpoints. API consumers could
get access to ``/people``, ``/people/<ObjectId>`` and ``/people/Doe``,
but only to ``/works``.  When you do grant access to item endpoints, you can
define up to two lookups, both defined with regexes. The first will be the
primary endpoint and will match your database primary key structure (i.e., an
``ObjectId`` in a MongoDB database).  

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/521d6840c437dc0002d1203c
    HTTP/1.1 200 OK
    Etag: 448a928514cbff5b0b516f60bcdf27cc75213280
    Last-Modified: Wed, 28 Aug 2013 03:02:24 GMT
    ... 

The second, which is optional and read-only, will match a field with unique values since Eve
will retrieve only the first match anyway.

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/Doe
    HTTP/1.1 200 OK
    Etag: 28995829ee85d69c4c18d597a0f68ae606a266cc
    Last-Modified: Wed, 21 Nov 2012 16:04:56 GMT 
    ... 

Since we are accessing the same item, in both cases the response payload will
look something like this:

.. code-block:: javascript

    {
        "firstname": "John",
        "lastname": "Doe",
        "born": "Thu, 27 Aug 1970 14:37:13 GMT",
        "role": ["author"],
        "location": {"city": "Auburn", "address": "422 South Gay Street"},
        "_id": "50acfba938345b0978fccad7"
        "updated": "Wed, 21 Nov 2012 16:04:56 GMT",
        "created": "Wed, 21 Nov 2012 16:04:56 GMT",
        "etag": "28995829ee85d69c4c18d597a0f68ae606a266cc",
        "_links": {
            "self": {"href": "eve-demo.herokuapp.com/people/50acfba938345b0978fccad7", "title": "person"},
            "parent": {"href": "eve-demo.herokuapp.com", "title": "home"},
            "collection": {"href": "http://eve-demo.herokuapp.com/people", "title": "people"}
        }
    }

As you can see, item endpoints provide their own HATEOAS_ directives.

.. admonition:: Please Note

    According to REST principles resource items should have one unique
    identifier. Eve abides by providing one default endpoint per item. Adding
    a secondary convenience, endpoint is a decision that should pondered
    carefully.

    Consider our example above. Even without the ``/people/<lastname>``
    endpoint, a client could always retrieve a person by querying the resource
    endpoint by last name: ``/people/?where={"lastname": "Doe"}``. Actually the
    whole example is fubar as there could be multiple people sharing the same
    last name, but you get the idea.

.. _filters:

Filtering and Sorting
---------------------
Resource endpoints allow consumers to retrieve multiple documents. Query
strings are supported, allowing for filtering and sorting. Two query syntaxes
are supported. The mongo query syntax:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?where={"lastname": "Doe"}
    HTTP/1.1 200 OK

and the native Python syntax:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?where=lastname=="Doe"
    HTTP/1.1 200 OK

Both query formats allow for conditional and logical And/Or operators, however
nested and combined. Sorting is supported as well:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?sort=[("lastname", -1)]
    HTTP/1.1 200 OK

Currently sort directives use a pure MongoDB syntax; support for a more general
syntax (``sort=lastname``) is planned.

Filters are enabled by default on all document fields. However, the API
maintainer can choose to disable them all and/or whitelist allowed ones (see
``ALLOWED_FILTERS`` in :ref:`global`). If scraping, or fear of DB DoS attacks
by querying on non-indexed fields is a concern, then whitelisting allowed
filters is the way to go.

.. admonition:: Please note

    Always use double quotes to wrap field names and values. Using single
    quotes will result in ``400 Bad Request`` responses.

Pagination
----------
Resource pagination is enabled by default in order to improve performance and
preserve bandwith. When a consumer requests a resource, the first N items
matching the query are served, and links to subsequent/previous pages are
provided with the response. Default and maximum page size is customizable, and
consumers can request specific pages via the query string:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?max_results=20&page=2
    HTTP/1.1 200 OK

Of course you can mix all the available query parameters:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?where={"lastname": "Doe"}&sort=[("firstname", 1)]&page=5
    HTTP/1.1 200 OK

Pagination can be disabled.

.. _hateoas_feature:

HATEOAS
-------
*Hypermedia as the Engine of Application State* (HATEOAS_) is enabled by
default. Each GET response includes a ``_links`` section. Links provide details
on their ``relation`` relative to the resource being accessed, and a ``title``.
Relations and titles can then be used by clients to dynamically updated their
UI, or to navigate the API without knowing its structure beforehand. An example:

::

    {
        "_links": { 
            "self": { 
                "href": "localhost:5000/people", 
                "title": "people" 
            }, 
            "parent": { 
                "href": "localhost:5000", 
                "title": "home" 
            }, 
            "next": {
                "href": "localhost:5000/people?page=2", 
                "title": "next page" 
            },
            "last": {
                "href": "localhost:5000/people?page=10", 
                "title": "last page" 
            } 
        } 
    }

A GET request to the API home page (the API entry point) will be served with
a list of links to accessible resources. From there, any client could navigate
the API just by following the links provided with every response.

Please note that ``next``, ``previous`` and ``last`` items will only be
included when appropriate. 

Disabling HATEOAS
~~~~~~~~~~~~~~~~~
HATEOAS can be disabled both at the API and/or resource level. When HATEOAS is
disabled, response payloads have a different structure. The resource payload is
a simple list of items:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people
    HTTP/1.1 200 OK

.. code-block:: javascript
    
    [
        {
            "firstname": "Mark", 
            "lastname": "Green", 
            "born": "Sat, 23 Feb 1985 12:00:00 GMT", 
            "role": ["copy", "author"], 
            "location": {"city": "New York", "address": "4925 Lacross Road"}, 
            "_id": "50bf198338345b1c604faf31",
            "updated": "Wed, 05 Dec 2012 09:53:07 GMT", 
            "created": "Wed, 05 Dec 2012 09:53:07 GMT", 
            "etag": "ec5e8200b8fa0596afe9ca71a87f23e71ca30e2d", 
        },
        {
            "firstname": "John", 
            ...
        },
    ]

As you can see, the ``_links`` element is also missing from list items. The
same happens to individual item payloads:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/522f01dc15b4fc00028e6d98
    HTTP/1.1 200 OK

.. code-block:: javascript

    {
        "lastname": "obama",
        "_id": "522f01dc15b4fc00028e6d98",
        "firstname": "barack",
        "created": "Tue, 10 Sep 2013 11:26:20 GMT",
        "etag": "206fb4a39815cc0ebf48b2b52d709777a55333de",
        "updated": "Tue, 10 Sep 2013 11:26:20 GMT"
    }

Why would you want to turn HATEOAS off? Well, if you know that your client
application is not going to use the feature, then you might want to save on
both bandwidth and performance. Also, some REST client libraries out there
might have issues when parsing something other than a simple list of items.

.. admonition:: Please note

    When HATEOAS is disabled, the API entry point (the home page) will return
    a ``404 Not Found``, since its only usefulness would be to return a list of
    available resources, which is the standard behavior when HATEOAS is
    enabled.

JSON and XML Rendering
----------------------
Eve responses are automatically rendered as JSON (the default) or XML,
depending on the request ``Accept`` header. Inbound documents (for inserts and
edits) are in JSON format. 

.. code-block:: console

    $ curl -H "Accept: application/xml" -i http://eve-demo.herokuapp.com
    HTTP/1.1 200 OK
    Content-Type: application/xml; charset=utf-8
    ...

.. code-block:: html

    <resource>
        <link rel="child" href="eve-demo.herokuapp.com/people" title="people" />
        <link rel="child" href="eve-demo.herokuapp.com/works" title="works" />
    </resource>

.. _conditional_requests:

Conditional Requests
--------------------
Each resource representation provides information on the last time it was
updated (``Last-Modified``), along with an hash value computed on the
representation itself (``ETag``). These headers allow clients to perform
conditional requests, only retrieving new or modified data, by using the
``If-Modified-Since`` header: 

.. code-block:: console

    $ curl -H "If-Modified-Since: Wed, 05 Dec 2012 09:53:07 GMT" -i http://eve-demo.herokuapp.com/people
    HTTP/1.1 200 OK

or the ``If-None-Match`` header:

.. code-block:: console

    $ curl -H "If-None-Match: 1234567890123456789012345678901234567890" -i http://eve-demo.herokuapp.com/people
    HTTP/1.1 200 OK


Data Integrity and Concurrency Control
--------------------------------------
API responses include a ``ETag`` header which also allows for proper
concurrency control. An ``ETag`` is a hash value representing the current
state of the resource on the server. Consumers are not allowed to edit or
delete a resource unless they provide an up-to-date ``ETag`` for the resource
they are attempting to edit. This prevents overwriting items with obsolete
versions. 

Consider the following workflow:

.. code-block:: console

    $ curl -X PATCH -i http://eve-demo.herokuapp.com/people/521d6840c437dc0002d1203c -d 'data={"firstname": "ronald"}'
    HTTP/1.1 403 FORBIDDEN

We attempted an edit, but we did not provide an ``ETag`` for the item, so we got
a not-so-nice ``403 FORBIDDEN``. Let's try again:

.. code-block:: console

    $ curl -H "If-Match: 1234567890123456789012345678901234567890" -X PATCH -i http://eve-demo.herokuapp.com/people/521d6840c437dc0002d1203c -d 'data={"firstname": "ronald"}'
    HTTP/1.1 412 PRECONDITION FAILED

What went wrong this time? We provided the mandatory ``If-Match`` header, but
it's value did not match the ``ETag`` computed on the representation of the item
currently stored on the server, so we got a ``402 PRECONDITION FAILED`` again!

.. code-block:: console

    $ curl -H "If-Match: 80b81f314712932a4d4ea75ab0b76a4eea613012" -X PATCH -i http://eve-demo.herokuapp.com/people/50adfa4038345b1049c88a37 -d 'data={"firstname": "ronald"}'
    HTTP/1.1 200 OK

It's a win, and the response payload looks something like this:

.. code-block:: javascript

    {
        "status": "OK",
        "updated": "Fri, 23 Nov 2012 08:11:19 GMT",
        "_id": "50adfa4038345b1049c88a37",
        "etag": "372fbbebf54dfe61742556f17a8461ca9a6f5a11"
        "_links": {"self": "..."}
    }

This time we got our patch in, and the server returned the new ``ETag``.  We
also get the new ``updated`` value, which eventually will allow us to perform
subsequent `conditional requests`_.

Concurrency control applies to all document edition methods: ``PATCH`` (edit),
``PUT`` (replace), ``DELETE`` (delete).

Bulk Inserts
------------
A client may submit a single document for insertion:

.. code-block:: console

    $ curl -d '{"firstname": "barack", "lastname": "obama"}' -H 'Content-Type: application/json' http://eve-demo.herokuapp.com/people
    HTTP/1.1 200 OK

In this case the response payload will just contain the relevant document
metadata:

.. code-block:: javascript

    {
        "status": "OK",
        "updated": "Thu, 22 Nov 2012 15:22:27 GMT",
        "_id": "50ae43339fa12500024def5b",
        "etag": "749093d334ebd05cf7f2b7dbfb7868605578db2c"
        "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae43339fa12500024def5b", "title": "person"}}
    }

However, in order to reduce the number of loopbacks, a client might also submit
multiple documents with a single request. All if needs to do is enclose the
documents in a JSON list: 

.. code-block:: console

    $ curl -d '[{"firstname": "barack", "lastname": "obama"}, {"firstname": "mitt", "lastname": "romney"}]' -H 'Content-Type: application/json' http://eve-demo.herokuapp.com/people
    HTTP/1.1 200 OK

The response will be a list itself, with the state of each document:

.. code-block:: javascript

    [
        {
            "status": "OK",
            "updated": "Thu, 22 Nov 2012 15:22:27 GMT",
            "_id": "50ae43339fa12500024def5b",
            "etag": "749093d334ebd05cf7f2b7dbfb7868605578db2c"
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae43339fa12500024def5b", "title": "person"}}
        },
        {
            "status": "OK",
            "updated": "Thu, 22 Nov 2012 15:22:27 GMT",
            "_id": "50ae43339fa12500024def5c",
            "etag": "62d356f623c7d9dc864ffa5facc47dced4ba6907"
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae43339fa12500024def5c", "title": "person"}}
        }
    ]

Evenutal validation errors on one document won't prevent the insertion of other
submitted documents. 

When multiple documents are submitted the API takes advantage of MongoDB *bulk
insert* capabilities which means that not only there's just one single request
traveling from the client to the remote API, but also that only one loopback is
performed between the API server and the database.

Data Validation
---------------
Data validation is provided out-of-the-box. Your configuration includes
a schema definition for every resource managed by the API. Data sent to the API
to be inserted/updated will be validated against the schema, and a resource
will only be updated if validation passes. 

.. code-block:: console

    $ curl -d '[{"firstname": "bill", "lastname": "clinton"}, {"firstname": "mitt", "lastname": "romney"}]' -H 'Content-Type: application/json' http://eve-demo.herokuapp.com/people
    HTTP/1.1 200 OK

The response will contain a success/error state for each item provided in the
request:

.. code-block:: javascript

    [
        {
            "status": "ERR",
            "issues": [
                "value 'romney' for field 'lastname' not unique"
            ]
        },
        {
            "status": "OK",
            "updated": "Thu, 22 Nov 2012 15:29:08 GMT",
            "_id": "50ae44c49fa12500024def5d",
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae44c49fa12500024def5d", "title": "person"}}
        }
    ]

In the example above, the first document did not validate and was rejected,
while the second was successfully created. The API maintainer has complete
control on data validation. Optionally, you can decide to allow for unknown
fields to be inserted/updated on one or more endpoints. For more information
see :ref:`validation`.

Extensible Data Validation
--------------------------
Data validation is based on the Cerberus_ validation system and therefore it is
extensible, so you can adapt it to your specific use case. Say that your API can
only accept odd numbers for a certain field value; you can extend the
validation class to validate that. Or say you want to make sure that a VAT
field actually matches your own country VAT algorithm; you can do that too. As
a matter of fact, Eve's MongoDB data-layer itself extends Cerberus
validation by implementing the ``unique`` schema field constraint. For more
information see :ref:`validation`

.. _cache_control:

Resource-level Cache Control
----------------------------
You can set global and individual cache-control directives for each resource.

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Length: 131
    Cache-Control: max-age=20
    Expires: Tue, 22 Jan 2013 09:34:34 GMT
    Server: Eve/0.0.3 Werkzeug/0.8.3 Python/2.7.3
    Date: Tue, 22 Jan 2013 09:34:14 GMT

The response above includes both ``Cache-Control`` and ``Expires`` headers.
These will minimize load on the server since cache-enbaled consumers will
perform resource-intensive request only when really needed.

Versioning
----------
I'm not too fond of API versioning. I believe that clients should be
intelligent enough to deal with API updates transparently, especially since
Eve-powered API support HATEOAS_. When versioning is a necessity, different API
versions should be isolated instances since so many things could be different
between versions: caching, URIs, schemas, validation, and so on. URI versioning
(http://api.example.com/v1/...) is supported.

Authentication
--------------
Customizable Basic Authentication (RFC-2617), Token-based authentication and
HMAC-based Authentication are supported. You can lockdown the whole API, or
just some endpoints. You can also restrict CRUD commands, like allowing open
read-only access while restricting edits, inserts and deletes to authorized
users. Role-based access control is supported as well. For more information
see :ref:`auth`.

CORS Cross-Origin Resource Sharing
----------------------------------
Disabled by default, CORS_ allows web pages to work with REST APIs, something
that is usually restricted by most broswers 'same domain' security policy.
Eve-powered APIs can be accesed by the JavaScript contained in web pages.

Read-only by default
--------------------
If all you need is a read-only API, then you can have it up and running in
a matter of minutes.

Default Values
--------------
It is possible to set default values for fields. When serving POST
(create) requests, missing fields will be assigned the configured default
values.

Predefined Database Filters
---------------------------
Resource endpoints will only expose (and update) documents that match
a predefined filter. This allows for multiple resource endpoints to seamlessy
target the same database collection. A typical use-case would be a
hypothetical ``people`` collection on the database being used by both the
``/admins`` and ``/users`` API endpoints.

.. _projections:

Projections
-----------
This feature allows you to create dynamic *views* of collections, or more precisely,
to decide what fields should or should not be returned, using a 'projection'.
Put another way, Projections are conditional queries where the client
dictates which fields should be returned by the API.

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?projection={"lastname": 1, "born": 1}
    HTTP/1.1 200 OK

The query above will only return *lastname* and *born* out of all the fields
available in the 'people' resource. Please note that key fields such as
ID_FIELD, DATE_CREATED, DATE_UPDATED etc.  will still be included with the
payload.

.. _embedded_docs:

Embedded Resource Serialization
-------------------------------
If a document field is referencing a document in another resource, clients can
request the referenced document to be embedded within the requested document.

Clients have the power to activate document embedding on per-request basis by
means of a query parameter. Suppose you have a ``emails`` resource configured
like this:

.. code-block:: python
   :emphasize-lines: 9

    DOMAIN = {
        'emails': {
            'schema': {
                'author:' {
                    'type': 'objectid', 
                    'data_relation': {
                        'resource': 'users', 
                        'field': '_id', 
                        'embeddable': True
                    },
                },
                'subject:' {'type': 'string'},
                'body:' {'type': 'string'}, 
            }
        }

A GET like this: ``/emails?embedded={"author":1}`` would return a fully
embedded users document, whereas the same request without the ``embedded``
argument would just return the user ``ObjectId``. Embedded resource
serialization is available at both resource and item
(``/emails/<id>/?embedded={"author":1}``) endpoints.

Embedding can be enabled or disabled both at global level (by setting
``EMBEDDING`` to either ``True`` or ``False``) and at resource level (by
toggling the ``embedding`` value). Furthermore, only fields with the
``embeddable`` value explicitly set to ``True`` will allow the embedding of
referenced documents.

Limitations: currenly we only support a single layer of embedding, i.e.
``/emails?embedded={"author": 1}`` but *not* ``/emails?embedded={"author.friends": 1}``. This
feature is about serialization on GET requests. There's no support for POST,
PUT or PATCH of embedded documents.

Document embedding is enabled by default.

.. _eventhooks:

Event Hooks
-----------
Each time a GET, POST, PATCH, DELETE method has been executed, both global
``on_<method>`` and resource-level ``on_<method>_<resource>`` events will be
raised. You can subscribe to these events with multiple callback functions.
Callbacks will receive the original `flask.request` object and the response
payload as arguments.

.. code-block:: pycon

    >>> def general_callback(resource, request, payload):
    ...  print 'A GET on the "%s" endpoint was just performed!' % resource

    >>> def contacts_callback(request, payload):
    ... print 'A get on "contacts" was just performed!'

    >>> app = Eve()
    >>> app.on_GET += general_callback
    >>> app.on_GET_contacts += contacts_callback

    >>> app.run()

Manipulating inbound documents 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
There is also support for ``on_insert(resource, documents)`` and
``on_insert_<resource>(documents)`` event hooks, raised when documents are
about to be stored in the database.  Callback functions could hook into these
events to arbitrarily add new fields, or edit existing ones.

.. code-block:: pycon

    >>> def before_insert(resource, documents):
    ...  print 'About to store documents to "%s" ' % resource

    >>> def before_insert_contacts(documents):
    ...  print 'About to store contacts'

    >>> app = Eve()
    >>> app.on_insert += before_insert
    >>> app.on_insert_contacts += before_insert_contacts

    >>> app.run()

``on_insert`` is raised on every resource being updated, while
``on_insert_<resource>`` is raised when the `<resource>` endpoint has been hit
with a POST request. In both circumstances, the event will be raised only if at
least one document passed validation and is going to be inserted. `documents`
is a list and only contains documents ready for insertion (payload documents
that did not pass validation are not included).

To provide seamless event handling features, Eve relies on the Events_ package.

Manipulating outbound documents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The following events:

- ``on_fetch_resource(resource, documents)``
- ``on_fetch_resource_<resource>(documents)`` 
- ``on_fetch_item(resource, _id, document)`` 
- ``on_fetch_item_<item_title>(_id, document)`` 
  
are raised when documents have just been read from the database and are about
to be sent to the client. Registered callback functions can manipulate the
documents as needed before they are returned to the client.

.. code-block:: pycon

    >>> def before_returning_items(resource, documents):
    ...  print 'About to return items from "%s" ' % resource

    >>> def before_returning_contacts(documents):
    ...  print 'About to return contacts'

    >>> def before_returning_item(resource, _id, document):
    ...  print 'About to return an item from "%s" ' % resource

    >>> def before_returning_contact(_id, document):
    ...  print 'About to return a contact' 

    >>> app = Eve()
    >>> app.on_fetch_resource += before_returning_items
    >>> app.on_fetch_resource_contacts += before_returning_contacts
    >>> app.on_fetch_item += before_returning_item
    >>> app.on_fetch_item_contact += before_returning_contact

    >>> app.run()

Please be aware that ``last_modified`` and ``etag`` headers will always be
consistent with the state of the documents on the database (they  won't be
updated to reflect changes eventually applied by the callback functions).


.. _ratelimiting:

Rate Limiting
-------------
API rate limiting is supported on a per-user/method basis. You can set the
number of requests and the time window for each HTTP method. If the requests
limit is hit within the time window, the API will respond with ``429 Request
limit exceeded`` until the timer resets. Users are identified by the
Authentication header or (when missing) by the client IP. When rate limiting
is enabled, appropriate ``X-RateLimit-`` headers are provided with every API
response.  Suppose that the rate limit has been set to 300 requests every 15
minutes, this is what a user would get after hitting a endpoint with a single
request:

::

    X-RateLimit-Remaining: 299
    X-RateLimit-Limit: 300
    X-RateLimit-Reset: 1370940300

You can set different limits for each one of the supported methods (GET, POST,
PATCH, DELETE). 

.. admonition:: Please Note

   Rate Limiting is disabled by default, and needs a Redis server running when
   enabled. A tutorial on Rate Limiting is forthcoming.

MongoDB Support
---------------
Support for MongoDB comes out of the box. Extensions for other SQL/NoSQL
backends can be developed with relative ease (a `PostgreSQL effort`_ is
ongoing, maybe you can lend a hand?)

Powered by Flask
----------------
Eve is based on the Flask_ micro web framework. Actually, Eve itself is
a Flask subclass, which means that Eve exposes all of Flask functionalities and
niceties, like a built-in development server and debugger_, integrated support
for unittesting_ and an `extensive documentation`_.

.. _HATEOAS: http://en.wikipedia.org/wiki/HATEOAS
.. _Cerberus: https://github.com/nicolaiarocci/cerberus
.. _REST: http://en.wikipedia.org/wiki/Representational_state_transfer
.. _CRUD: http://en.wikipedia.org/wiki/Create,_read,_update_and_delete
.. _`CORS`: http://en.wikipedia.org/wiki/Cross-origin_resource_sharing
.. _`PostgreSQL effort`: https://github.com/nicolaiarocci/eve/issues/17
.. _Flask: http://flask.pocoo.org
.. _debugger: http://flask.pocoo.org/docs/quickstart/#debug-mode
.. _unittesting: http://flask.pocoo.org/docs/testing/
.. _`extensive documentation`: http://flask.pocoo.org/docs/
.. _`this`: https://speakerdeck.com/nicola/developing-restful-web-apis-with-python-flask-and-mongodb?slide=113
.. _Events: https://github.com/nicolaiarocci/events
