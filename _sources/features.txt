Features
========
Below is a list of main features that any EVE-powered APIs can expose. Most of
these features can be experienced live by consuming the Demo API (see
:ref:`demo`).

Emphasis on REST
----------------
The Eve project aims to provide the best possibile REST-compliant API
implementation. Fundamental REST_ principles like *separation of concerns*,
*stateless and layered system*, *cacheability*, *uniform interface* have been
kept into consideration while designing the core API.

Full range of CRUD operations
-----------------------------
APIs can support the full range of CRUD_ operations. Within the same API you
can have a read-only resource accessible at one endpoint, along with a fully
editable resource at another endpoint. The following table shows Eve's
implementation of CRUD via REST

====== ========= ===================
Action HTTP Verb Context 
====== ========= ===================
Create POST      Collection
Read   GET       Collection/Document
Update PATCH     Document
Delete DELETE    Collection/Document
====== ========= ===================

If you are wondering why PATCH and not PUT, check `this`_ out. Also, as
a fallback for the odd client not directly supporting PATCH, the API
will gladly honor a POST with the ``X-HTTP-Method-Override: PATCH`` header tag.

Customizable resource endpoints
-------------------------------
By default Eve will make known database collections available as resource
endpoints (persistent identifiers in REST idiom). So a database ``people`` collection 
will be avaliable at the ``example.com/people/`` API endpoint.
You can customize the URIs though, so the API endpoint could become, say,
``example.com/customers/``. Consider the following request:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/
    HTTP/1.0 200 OK

The response payload will look something like this:

.. code-block:: javascript
    
    {
        "_items": [
            {
                "firstname": "Mark", 
                "lastname": "Green", 
                "born": "Sat, 23 Feb 1985 12:00:00 UTC", 
                "role": ["copy", "author"], 
                "location": {"city": "New York", "address": "4925 Lacross Road"}, 
                "_id": "50bf198338345b1c604faf31",
                "updated": "Wed, 05 Dec 2012 09:53:07 UTC", 
                "created": "Wed, 05 Dec 2012 09:53:07 UTC", 
                "etag": "ec5e8200b8fa0596afe9ca71a87f23e71ca30e2d", 
                "_links": {
                    "self": {"href": "eve-demo.herokuapp.com:5000/people/50bf198338345b1c604faf31/", "title": "person"},
                },
            },
            ...
        ],
        "_links": {
            "self": {"href": "eve-demo.herokuapp.com:5000/people/", "title": "people"}, 
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
``_id``     unique item key, also needed to access the indivdual item endpoint.
=========== =================================================================

These additional fields are automatically handled by the API (clients don't
need to provide them when adding/editing resources).

The ``_links`` list provides HATEOAS_ directives.

.. _custom_item_endpoints:

Customizable, multiple item endpoints
-------------------------------------
Resources can or cannot expose individual item endpoints. API consumers could
get access to ``/people/``, ``/people/<ObjectId>/`` and ``/people/Doe/``,
but only to ``/works/``.  When you do grant access to item endpoints, you can
define up to two lookups, both defined via regex. The first will be the primary
endpoint and will match your database primary key structure (i.e. an
``ObjectId`` in a MongoDB database).  

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/50acfba938345b0978fccad7/
    HTTP/1.0 200 OK
    Etag: 28995829ee85d69c4c18d597a0f68ae606a266cc
    Last-Modified: Wed, 21 Nov 2012 16:04:56 UTC 
    ... 

The second, which is optional, will match a field with unique values since Eve
will retrieve only the first match anyway.

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/Doe/
    HTTP/1.0 200 OK
    Etag: 28995829ee85d69c4c18d597a0f68ae606a266cc
    Last-Modified: Wed, 21 Nov 2012 16:04:56 UTC 
    ... 

Since we are accessing the same item, in both cases the response payload will
look something like this:

.. code-block:: javascript

    {
        "firstname": "John",
        "lastname": "Doe",
        "born": "Thu, 27 Aug 1970 14:37:13 UTC",
        "role": ["author"],
        "location": {"city": "Auburn", "address": "422 South Gay Street"},
        "_id": "50acfba938345b0978fccad7"
        "updated": "Wed, 21 Nov 2012 16:04:56 UTC",
        "created": "Wed, 21 Nov 2012 16:04:56 UTC",
        "_links": {
            "self": {"href": "eve-demo.herokuapp.com/people/50acfba938345b0978fccad7/", "title": "person"},
            "parent": {"href": "eve-demo.herokuapp.com/", "title": "home"},
            "collection": {"href": "http://eve-demo.herokuapp.com/people/", "title": "people"}
        }
    }

As you can see, item endpoints provide their own HATEOAS_ directives.

.. _filters:

Filtering and Sorting
---------------------
Resource endpoints allow consumers to retrieve multiple documents. Query
strings are supported, allowing for filtering and sorting. Two query syntaxes
are supported. The mongo query syntax:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/?where={"lastname": "Doe"}
    HTTP/1.0 200 OK

and the native Python syntax:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/?where=lastname=="Doe"
    HTTP/1.0 200 OK

Both query formats allow for conditional and logical And/Or operators, however
nested and combined. Sorting is supported as well:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/?sort={"lastname": -1}
    HTTP/1.0 200 OK

Currently sort directives use a pure MongoDB syntax; support for a more general
syntax (``sort=lastname``) is planned.

Pagination
----------
Resource pagination is enabled by default in order to improve performance and
preserve bandwith. When a consumer requests a resource, the first N items
matching the query are serverd, and links to subsequent/previous pages are
provided with the response. Default and maximum page size is customizable, and
consumers can request specific pages via the query string:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/?max_results=20&page=2
    HTTP/1.0 200 OK

Of course you can mix all the available query parameters:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people/?where={"lastaname": "Doe"}&sort={"firstname"}&page=5
    HTTP/1.0 200 OK

Pagination can be disabled.

.. _hateoas_feature:

HATEOAS
-------
*Hypermedia as the Engine of Application State* (HATEOAS_) is enabled by default. Each GET
response includes a ``_links`` section. Links provide details on their
``relation`` relative to the resource being accessed, and a ``title``.
Relations and titles can then be used by clients to dynamically updated their
UI, or to navigate the API without knowing it structure beforehand. An
example:

::

    {
        "_links": { 
            "self": { 
                "href": "localhost:5000/people/", 
                "title": "people" 
            }, 
            "parent": { 
                "href": "localhost:5000", 
                "title": "home" 
            }, 
            "next": {
                "href": "localhost:5000/people/?page=2", 
                "title": "next page" 
            } 
        } 
    }

A GET request to the API home page (the API entry point) will be served with
a list of links to accessible resources. From there, any client could navigate
the API just by following the links provided with every response.

JSON and XML Rendering
----------------------
Eve responses are automatically rendered as JSON (the default) or XML,
depending on the request ``Accept`` header. Inbound documents (for inserts and
edits) are in JSON format. 

.. code-block:: console

    $ curl -H "Accept: application/xml" -i http://eve-demo.herokuapp.com/
    HTTP/1.0 200 OK
    Content-Type: application/xml; charset=utf-8
    ...

.. code-block:: html

    <resource>
        <link rel="child" href="eve-demo.herokuapp.com/works/" title="works" />
        <link rel="child" href="eve-demo.herokuapp.com/people/" title="people" />
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

    $ curl -H "If-Modified-Since: Wed, 05 Dec 2012 09:53:07 UTC" -i http://eve-demo.herokuapp.com:5000/people/
    HTTP/1.0 200 OK

or the ``If-None-Match`` header:

.. code-block:: console

    $ curl -H "If-None-Match: 1234567890123456789012345678901234567890" -i http://eve-demo.herokuapp.com:5000/people/
    HTTP/1.0 200 OK


Data Integrity and Concurrency Control
--------------------------------------
API responses include a ``ETag`` header which also allows for proper
concurrency control. An ``ETag`` is an hash value representing the current
state of the resource on the server. Consumers are not allowed to edit or
delete a resource unless they provide an up-to-date ``ETag`` for the resource
they are attempting to edit. This prevents overwriting items with obsolete
versions. 

Consider the following workflow:

.. code-block:: console

    $ curl -X PATCH -i http://eve-demo.herokuapp.com/people/50adfa4038345b1049c88a37/ -d 'data={"firstname": "ronald"}'
    HTTP/1.0 403 FORBIDDEN

We attempted an edit, but we did not provide an ETag for the item, so we got
a not-so-nice ``403 FORBIDDEN``. Let's try again:

.. code-block:: console

    $ curl -H "If-Match: 1234567890123456789012345678901234567890" -X PATCH -i http://eve-demo.herokuapp.com/people/50adfa4038345b1049c88a37/ -d 'data={"firstname": "ronald"}'
    HTTP/1.0 412 PRECONDITION FAILED

What went wrong this time? We provided the mandatory ``If-Match`` header, but
it's value did not match the ETag computed on the representation of the item
currently stored on the server, so we got a ``402 PRECONDITION FAILED``. Again!

.. code-block:: console

    $ curl -H "If-Match: 80b81f314712932a4d4ea75ab0b76a4eea613012" -X PATCH -i http://eve-demo.herokuapp.com/people/50adfa4038345b1049c88a37/ -d 'data={"firstname": "ronald"}'
    HTTP/1.0 200 OK

It's a win, and the response payload looks something like this:

.. code-block:: javascript

    {
        "data": {
            "status": "OK",
            "updated": "Fri, 23 Nov 2012 08:11:19 UTC",
            "_id": "50adfa4038345b1049c88a37",
            "etag": "372fbbebf54dfe61742556f17a8461ca9a6f5a11"
            "_links": {"self": "..."}
        }
    }

This time we got our patch in, and the server returned the new ETag.  We also
get the new ``updated`` value, which eventually will allow us to perform
subsequent `conditional requests`_.

Multiple Insertions
-------------------
Clients can send a stream of multiple documents to be inserted at once. 

.. code-block:: console

    $ curl -d 'item1={"firstname": "barack", "lastname": "obama"}' -d 'item2={"firstname": "mitt", "lastname": "romney"}' http://eve-demo.herokuapp.com/people/
    HTTP/1.0 200 OK

The response will provide detailed state information about each document
inserted (creation date, link to the item endpoint, primary key/id, etc.).
Errors on one document won't prevent the insertion of other documents in the
data stream.

.. code-block:: javascript

    {
        "item2": {
            "status": "OK",
            "updated": "Thu, 22 Nov 2012 15:22:27 UTC",
            "_id": "50ae43339fa12500024def5b",
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae43339fa12500024def5b/", "title": "person"}}
        },
        "item1": {
            "status": "OK",
            "updated": "Thu, 22 Nov 2012 15:22:27 UTC",
            "_id": "50ae43339fa12500024def5c",
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae43339fa12500024def5c/", "title": "person"}}
        }
    }

Data Validation
---------------
Data validation is provided out-of-the-box. Your configuration includes
a schema definition for every resource managed by the API. Data sent to the API
for insertion or edition will be validated against the schema, and a resource
will be updated only if validation is passed. 

.. code-block:: console

    $ curl -d 'item1={"firstname": "bill", "lastname": "clinton"}' -d 'item2={"firstname": "mitt", "lastname": "romney"}' http://eve-demo.herokuapp.com/people/
    HTTP/1.0 200 OK

The response will contain a success/error state for each item provided with the
request:

.. code-block:: javascript

      {
        "item2": {
            "status": "ERR",
            "issues": [
                "value 'romney' for field 'lastname' not unique"
            ]
        },
        "item1": {
            "status": "OK",
            "updated": "Thu, 22 Nov 2012 15:29:08 UTC",
            "_id": "50ae44c49fa12500024def5d",
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae44c49fa12500024def5d/", "title": "person"}}
        }
    }

In the example above, ``item2`` did not validate and was rejected, while
``item1`` was successfully created. API maintainer has complete control on
data validation. For more informations see :ref:`validation`.

Extensible Data Validation
--------------------------
Data validation is based on the Cerberus_ validation system and therefore it is
extensible so you can adapt it to your specific use case. Say that your API can
only accept odd numbers for a certain field value: you can extend the
validation class to validate that. Or say you want to make sure that a VAT
field actually matches your own country VAT algorithm: you can do that too. As
a matter of fact, Eve's MongoDB data-layer itself is extending Cerberus
validation implementing the ``unique`` schema field constraint. For more
informations see :ref:`validation`

.. _cache_control:

Resource-level Cache Control
----------------------------
You can set global and individual cache-control directives for each resource.

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/
    HTTP/1.0 200 OK
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
users. Role-based access control is supported as well. For more informations
see :ref:`auth`.

CORS Cross-Origin Resource Sharing
----------------------------------
Disabled by default, CORS_ allows web pages to work with REST APIs, something
that is usually restricted by most broswers 'same domain' security policy.
Eve-powered API can be accesed by the JavaScript contained in web pages.

Read-only by default
--------------------
If all you need is a read-only API, then you can have it up and running in
a matter of minutes.

Default Values
--------------
It is possibile to set default values for fields. When serving POST
(create) requests, missing fields will be assigned the configured default
values.

Predefined Database Filters
---------------------------
Resource endpoints will only expose (and update) documents that match
a predefined filter. This allows for multiple resource endpoints to seamlessy
target the same database collection. A typical use-case would be an
hypothetical ``people`` collection on the database being used by both the
``/admins/`` and ``/users/`` API endpoints.

MongoDB Support
---------------
Support for MongoDB comes out of the box. Extensions for other SQL/NoSQL
backends can be developed with relative ease (a `PostgreSQL effort`_ is
ongoing, maybe you can lend a hand?)

Powered by Flask
----------------
Eve is based on the Flask_ micro web framework. Actually, Eve itself is
a Flask subclass, which means that Eve exposes all of Flask functionalities and
niceties, like a buil-in development server and debugger_, integrated support
for unittesting_ and an `extensive documentation`_.

.. _HATEOAS: http://en.wikipedia.org/wiki/HATEOAS
.. _Cerberus: http://cerberus.readthedocs.org/
.. _REST: http://en.wikipedia.org/wiki/Representational_state_transfer
.. _CRUD: http://en.wikipedia.org/wiki/Create,_read,_update_and_delete
.. _`CORS`: http://en.wikipedia.org/wiki/Cross-origin_resource_sharing
.. _`PostgreSQL effort`: https://github.com/nicolaiarocci/eve/issues/17
.. _Flask: http://flask.pocoo.org
.. _debugger: http://flask.pocoo.org/docs/quickstart/#debug-mode
.. _unittesting: http://flask.pocoo.org/docs/testing/
.. _`extensive documentation`: http://flask.pocoo.org/docs/
.. _`this`: https://speakerdeck.com/nicola/developing-restful-web-apis-with-python-flask-and-mongodb?slide=113
