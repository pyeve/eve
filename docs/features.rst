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

.. _resource_endpoints:

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
                "_updated": "Wed, 05 Dec 2012 09:53:07 GMT",
                "_created": "Wed, 05 Dec 2012 09:53:07 GMT",
                "_etag": "ec5e8200b8fa0596afe9ca71a87f23e71ca30e2d",
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

============ =================================================================
Field        Description
============ =================================================================
``_created`` item creation date.
``_updated`` item last updated on.
``_etag``    ETag, to be used for concurrency control and conditional requests.
``_id``      unique item key, also needed to access the individual item endpoint.
============ =================================================================

These additional fields are automatically handled by the API (clients don't
need to provide them when adding/editing resources).

The ``_links`` list provides HATEOAS_ directives.

.. _subresources:

Sub Resources
~~~~~~~~~~~~~
Endpoints support sub-resources so you could have something like:
``/people/<contact_id>/invoices``. When setting the ``url`` rule for such and
endpoint you would use a regex and assign a field name to it:

.. code-block:: python

    invoices = {
        'url': 'people/<regex("[a-f0-9]{24}"):contact_id>/invoices'
        ...

Then this GET to the endpoint, which would roughly translate to *give
me all the invoices by <contact_id>*:

::

    people/51f63e0838345b6dcd7eabff/invoices

Would cause the underlying database collection invoices to be queried this way:

::

    {'contact_id': '51f63e0838345b6dcd7eabff'}

And this one:

::

    people/51f63e0838345b6dcd7eabff/invoices?where={"number": 10}

would be queried like:

::

    {'contact_id': '51f63e0838345b6dcd7eabff', "number": 10}

Please note that when designing your API, most of the time you can get away
without resorting to sub-resources. In the example above the same result would
be achieved by simply exposing a ``invoices`` endpoint that clients could query
this way:

::

    invoices?where={"contact_id": 51f63e0838345b6dcd7eabff}

or

::

    invoices?where={"contact_id": 51f63e0838345b6dcd7eabff, "number": 10}

It's mostly a design choice, but keep in mind that when it comes to enabling
individual documment endpoints you might occur in performance hits. This
otherwise legit GET request:

::

    people/<contact_id>/invoices/<invoice_id>

would cause a two fields lookup on the database. This is not ideal and also not
really needed, as ``<invoice_id>`` is a unique field. By contrast, if you had
a simple resource endpoint the document lookup would happen on a single field:

::

    invoices/<invoice_id>

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
    Etag: 28995829ee85d69c4c18d597a0f68ae606a266cc
    Last-Modified: Wed, 21 Nov 2012 16:04:56 GMT
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
        "_updated": "Wed, 21 Nov 2012 16:04:56 GMT",
        "_created": "Wed, 21 Nov 2012 16:04:56 GMT",
        "_etag": "28995829ee85d69c4c18d597a0f68ae606a266cc",
        "_links": {
            "self": {"href": "eve-demo.herokuapp.com/people/50acfba938345b0978fccad7", "title": "person"},
            "parent": {"href": "eve-demo.herokuapp.com", "title": "home"},
            "collection": {"href": "http://eve-demo.herokuapp.com/people", "title": "people"}
        }
    }

As you can see, item endpoints provide their own HATEOAS_ directives.

.. admonition:: Please Note

    According to REST principles resource items should only have one unique
    identifier. Eve abides by providing one default endpoint per item. Adding
    a secondary endpoint is a decision that should pondered carefully.

    Consider our example above. Even without the ``/people/<lastname>``
    endpoint, a client could always retrieve a person by querying the resource
    endpoint by last name: ``/people/?where={"lastname": "Doe"}``. Actually the
    whole example is fubar, as there could be multiple people sharing the same
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
nested and combined.

Filters are enabled by default on all document fields. However, the API
maintainer can choose to disable them all and/or whitelist allowed ones (see
``ALLOWED_FILTERS`` in :ref:`global`). If scraping, or fear of DB DoS attacks
by querying on non-indexed fields is a concern, then whitelisting allowed
filters is the way to go.

Sorting is supported as well:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?sort=[("lastname", -1)]
    HTTP/1.1 200 OK

Sorting is enabled by default and can be disabled both globally and/or at
resource level (see ``SORTING`` in :ref:`global` and ``sorting`` in
:ref:`domain`). It is also possible to set the default sort at every API
endpoints (see ``default_sort`` in :ref:`domain`). Currently, sort directives
use a pure MongoDB syntax; support for a more general syntax
(``sort=lastname``) is planned.

.. admonition:: Please note

    Always use double quotes to wrap field names and values. Using single
    quotes will result in ``400 Bad Request`` responses.

Pagination
----------
Resource pagination is enabled by default in order to improve performance and
preserve bandwidth. When a consumer requests a resource, the first N items
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
            "_updated": "Wed, 05 Dec 2012 09:53:07 GMT",
            "_created": "Wed, 05 Dec 2012 09:53:07 GMT",
            "_etag": "ec5e8200b8fa0596afe9ca71a87f23e71ca30e2d",
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
        "_created": "Tue, 10 Sep 2013 11:26:20 GMT",
        "_etag": "206fb4a39815cc0ebf48b2b52d709777a55333de",
        "_updated": "Tue, 10 Sep 2013 11:26:20 GMT"
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

.. _jsonxml:

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

XML support can be disabled by setting ``XML`` to ``False`` in the settings
file. JSON support can be disabled by setting ``JSON`` to ``False``.  Please
note that at least one mime type must always be enabled, either implicitly or
explicitly. By default, both are supported.

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


.. _concurrency:

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

    $ curl -X PATCH -i http://eve-demo.herokuapp.com/people/521d6840c437dc0002d1203c -d '{"firstname": "ronald"}'
    HTTP/1.1 403 FORBIDDEN

We attempted an edit (``PATCH``), but we did not provide an ``ETag`` for the
item so we got a ``403 FORBIDDEN`` back. Let's try again:

.. code-block:: console

    $ curl -H "If-Match: 1234567890123456789012345678901234567890" -X PATCH -i http://eve-demo.herokuapp.com/people/521d6840c437dc0002d1203c -d '{"firstname": "ronald"}'
    HTTP/1.1 412 PRECONDITION FAILED

What went wrong this time? We provided the mandatory ``If-Match`` header, but
it's value did not match the ``ETag`` computed on the representation of the item
currently stored on the server, so we got a ``412 PRECONDITION FAILED``. Again!

.. code-block:: console

    $ curl -H "If-Match: 80b81f314712932a4d4ea75ab0b76a4eea613012" -X PATCH -i http://eve-demo.herokuapp.com/people/50adfa4038345b1049c88a37 -d '{"firstname": "ronald"}'
    HTTP/1.1 200 OK

Finally! And the response payload looks something like this:

.. code-block:: javascript

    {
        "_status": "OK",
        "_updated": "Fri, 23 Nov 2012 08:11:19 GMT",
        "_id": "50adfa4038345b1049c88a37",
        "_etag": "372fbbebf54dfe61742556f17a8461ca9a6f5a11"
        "_links": {"self": "..."}
    }

This time we got our patch in, and the server returned the new ``ETag``.  We
also get the new ``_updated`` value, which eventually will allow us to perform
subsequent `conditional requests`_.

Concurrency control applies to all edition methods: ``PATCH`` (edit), ``PUT``
(replace), ``DELETE`` (delete).

Disabling concurrency control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If your use case requires, you can opt to completely disable concurrency
control. ETag match checks can be disabled by setting the ``IF_MATCH``
configuration variable to ``False`` (see :ref:`global`). When concurrency
control is disabled no etag is provided with responses. You should be careful
about disabling this feature, as you would effectively open your API to the
risk of older versions replacing your documents.

Bulk Inserts
------------
A client may submit a single document for insertion:

.. code-block:: console

    $ curl -d '{"firstname": "barack", "lastname": "obama"}' -H 'Content-Type: application/json' http://eve-demo.herokuapp.com/people
    HTTP/1.1 201 OK

In this case the response payload will just contain the relevant document
metadata:

.. code-block:: javascript

    {
        "_status": "OK",
        "_updated": "Thu, 22 Nov 2012 15:22:27 GMT",
        "_id": "50ae43339fa12500024def5b",
        "_etag": "749093d334ebd05cf7f2b7dbfb7868605578db2c"
        "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae43339fa12500024def5b", "title": "person"}}
    }

However, in order to reduce the number of loopbacks, a client might also submit
multiple documents with a single request. All it needs to do is enclose the
documents in a JSON list:

.. code-block:: console

    $ curl -d '[{"firstname": "barack", "lastname": "obama"}, {"firstname": "mitt", "lastname": "romney"}]' -H 'Content-Type: application/json' http://eve-demo.herokuapp.com/people
    HTTP/1.1 201 OK

The response will be a list itself, with the state of each document:

.. code-block:: javascript

    [
        {
            "_status": "OK",
            "_updated": "Thu, 22 Nov 2012 15:22:27 GMT",
            "_id": "50ae43339fa12500024def5b",
            "_etag": "749093d334ebd05cf7f2b7dbfb7868605578db2c"
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae43339fa12500024def5b", "title": "person"}}
        },
        {
            "_status": "OK",
            "_updated": "Thu, 22 Nov 2012 15:22:27 GMT",
            "_id": "50ae43339fa12500024def5c",
            "_etag": "62d356f623c7d9dc864ffa5facc47dced4ba6907"
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae43339fa12500024def5c", "title": "person"}}
        }
    ]

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
    HTTP/1.1 201 OK

The response will contain a success/error state for each item provided in the
request:

.. code-block:: javascript

    [
        {
            "_status": "ERR",
            "_issues": {"lastname": "value 'clinton' not unique"}
        },
        {
            "_status": "OK",
            "_updated": "Thu, 22 Nov 2012 15:29:08 GMT",
            "_id": "50ae44c49fa12500024def5d",
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae44c49fa12500024def5d", "title": "person"}}
        }
    ]

In the example above, the first document did not validate and was rejected,
while the second was successfully created. The API maintainer has complete
control on data validation. Optionally, you can decide to allow for unknown
fields to be inserted/updated on one or more endpoints. For more information
see :ref:`validation`.

.. admonition:: Please Note

    Eventual validation errors on one or more document won't prevent the
    insertion of valid documents. The response status code will be ``201
    Created`` if *at least one document* passed validation and has actually
    been stored. If no document passed validation the status code will be ``200
    OK``, meaning that the request was accepted and processed. It is still
    client's responsability to parse the response payload and make sure that
    all documents passed validation.

Extensible Data Validation
--------------------------
Data validation is based on the Cerberus_ validation system and therefore it is
extensible, so you can adapt it to your specific use case. Say that your API can
only accept odd numbers for a certain field value; you can extend the
validation class to validate that. Or say you want to make sure that a VAT
field actually matches your own country VAT algorithm; you can do that too. As
a matter of fact, Eve's MongoDB data-layer itself extends Cerberus
validation by implementing the ``unique`` schema field constraint. For more
information see :ref:`validation`.

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
These will minimize load on the server since cache-enabled consumers will
perform resource-intensive request only when really needed.

API Versioning
--------------
I'm not too fond of API versioning. I believe that clients should be
intelligent enough to deal with API updates transparently, especially since
Eve-powered API support HATEOAS_. When versioning is a necessity, different API
versions should be isolated instances since so many things could be different
between versions: caching, URIs, schemas, validation, and so on. URI versioning
(http://api.example.com/v1/...) is supported.

.. _document_versioning:

Document Versioning
-------------------
Eve supports automatic version control of documents. By default, this setting
is turned off, but it can be turned globally or configured individually for
each resource. When enabled, Eve begins automatically tracking changes to
documents and adds the fields ``_version`` and ``_latest_version`` when
retrieving documents.

Behind the scenes, Eve stores document versions in shadow collections that
parallels the collection of each primary resource that Eve defines. New
document versions are automatically added to this collection during normal
POST, PUT, and PATCH operations. A special new query parameter is available
when GETing an item that provides access to the document versions. Access a
specific version with ``?version=VERSION``, access all versions with
``?version=all``, and access diffs of all versions with ``?version=diffs``.
Collection query features like projections, pagination, and sorting work with
``all`` and ``diff`` except for sorting which does not work on ``diff``.

It is important to note that there are a few non-standard scenarios which could
produce unexpected results when versioning is turned on. In particular, document
history will not be saved when modifying collections outside of the Eve
generated API. Also, if at anytime the ``VERSION`` field gets removed from the
primary document (which cannot happen through the API when versioning is turned
on), a subsequent write will re-initialize the ``VERSION`` number with
``VERSION`` = 1. At this time there will be multiple versions of the document
with the same version number. In normal practice, ``VERSIONING`` can be enable
without worry for any new collection or even an existing collection which has
not previously had versioning enabled.

For more information see and :ref:`global` and :ref:`domain`.


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
Eve-powered APIs can be accessed by the JavaScript contained in web pages.

Read-only by default
--------------------
If all you need is a read-only API, then you can have it up and running in
a matter of minutes.

Default and Nullable Values
---------------------------
Fields can have default values and nullable types. When serving POST (create)
requests, missing fields will be assigned the configured default values. See
``default`` and ``nullable`` keywords in :ref:`schema` for more informations.

Predefined Database Filters
---------------------------
Resource endpoints will only expose (and update) documents that match
a predefined filter. This allows for multiple resource endpoints to seamlessly
target the same database collection. A typical use-case would be a
hypothetical ``people`` collection on the database being used by both the
``/admins`` and ``/users`` API endpoints.

.. admonition:: See also

    - :ref:`datasource`
    - :ref:`filter`

.. _projections:

Projections
-----------
This feature allows you to create dynamic views of collections and documents,
or more precisely, to decide what fields should or should not be returned,
using a 'projection'. Put another way, Projections are conditional queries
where the client dictates which fields should be returned by the API.

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?projection={"lastname": 1, "born": 1}
    HTTP/1.1 200 OK

The query above will only return *lastname* and *born* out of all the fields
available in the 'people' resource. You can also exclude fields:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?projection={"born": 0}
    HTTP/1.1 200 OK

The above will return all fields but *born*. Please note that key fields such
as ID_FIELD, DATE_CREATED, DATE_UPDATED etc.  will still be included with the
payload. Also keep in mind that some database engines, Mongo included, do not
allow for mixing of inclusive and exclusive selections.

.. admonition:: See also

    - :ref:`projection`
    - :ref:`projection_filestorage`

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
                'author': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'users',
                        'field': '_id',
                        'embeddable': True
                    },
                },
                'subject': {'type': 'string'},
                'body': {'type': 'string'},
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

Embedding also works with a data_relation to a specific version of a document,
but the schema looks a little bit different. To enable the data_relation to a
specific version, add ``'version': True`` to the data_relation block. You'll
also want to change the ``type`` to ``dict`` and add the ``schema`` definition
shown below.

.. code-block:: python
   :emphasize-lines: 5, 6, 11

    DOMAIN = {
        'emails': {
            'schema': {
                'author': {
                    'type': 'dict',
                    'schema': {
                        '_id': {'type': 'objectid'},
                        '_version': {'type': 'integer'}
                    },
                    'data_relation': {
                        'resource': 'users',
                        'field': '_id',
                        'embeddable': True,
                        'version': True,
                    },
                },
                'subject': {'type': 'string'},
                'body': {'type': 'string'},
            }
        }

As you can see, ``'version': True`` changes the expected value of a
data_relation field to a dictionary with fields names ``data_relation['field']``
and ``VERSION``. With ``'field': '_id'`` in the data_relation definition above
and ``VERSION = '_version'`` in the Eve config, the value of the data_relation
in this scenario would be a dictionary with fields ``_id`` and ``_version``.

Predefined Resource Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It is also possible to elect some fields for predefined resource
serialization. The ``embedded_fields`` option accepts a list of fields. If the
listed fields are embeddable and they are actually referencing documents in other
resources (and embedding is enbaled for the resource), then the referenced
documents will be embedded by default.

Limitations
~~~~~~~~~~~
Currenly we only support a single layer of embedding, i.e.
``/emails?embedded={"author": 1}`` but *not*
``/emails?embedded={"author.friends": 1}``. This feature is about serialization
on GET requests. There's no support for POST, PUT or PATCH of embedded
documents.

Document embedding is enabled by default.

.. admonition:: Please note

    When it comes to MongoDB, what embedded resource serialization deals with
    is *document references* (linked documents), something different from
    *embedded documents*, also supported by Eve (see `MongoDB Data Model
    Design`_). Embedded resource serialization is a nice feature that can
    really help with normalizing your data model for the client.  However, when
    deciding whether to enable it or not, especially by default, keep in mind
    that each embedded resource being looked up will require a database lookup,
    which can easily lead to performance issues.

.. _eventhooks:

Event Hooks
-----------
Pre-Request Event Hooks
~~~~~~~~~~~~~~~~~~~~~~~
When a GET, POST, PATCH, PUT, DELETE request is received, both
a ``on_pre_<method>`` and a ``on_pre_<method>_<resource>`` event is raised.
You can subscribe to these events with multiple callback functions. 

.. code-block:: pycon

    >>> def pre_get_callback(resource, request, lookup):
    ...  print 'A GET request on the "%s" endpoint has just been received!' % resource

    >>> def pre_contacts_get_callback(request, lookup):
    ...  print 'A GET request on the contacts endpoint has just been received!'

    >>> app = Eve()

    >>> app.on_pre_GET += pre_get_callback
    >>> app.on_pre_GET_contacts += pre_contacts_get_callback

    >>> app.run()

Callbacks will receive the resource being requested, the original
``flask.request`` object and the current lookup dictionary as arguments (only
exception being the ``on_pre_POST`` hook which does not provide a ``lookup``
argument). 

Dynamic Lookup Filters
^^^^^^^^^^^^^^^^^^^^^^
Since the ``lookup`` dictionary will be used by the data layer to retrieve
resource documents, developers may choose to alter it in order to add custom
logic to the lookup query. 

.. code-block:: python

    def pre_GET(resource, request, lookup):
        # only return documents that have a 'username' field.
        lookup["username"] = {'$exists': True}

    app = Eve()

    app.on_pre_GET += pre_GET
    app.run()

Altering the lookup dictionary at runtime would have similar effects to
applying :ref:`filter` via configuration. However, you can only set static
filters via configuration whereas by hooking to the ``on_pre_<METHOD>`` events
you are allowed to set dynamic filters instead, which allows for additional
flexibility. 

Post-Request Event Hooks
~~~~~~~~~~~~~~~~~~~~~~~~
When a GET, POST, PATCH, PUT, DELETE method has been executed, both
a ``on_post_<method>`` and ``on_post_<method>_<resource>`` event is raised. You
can subscribe to these events with multiple callback functions. Callbacks will
receive the resource accessed, original `flask.request` object and the response
payload.

.. code-block:: pycon

    >>> def post_get_callback(resource, request, payload):
    ...  print 'A GET on the "%s" endpoint was just performed!' % resource

    >>> def post_contacts_get_callback(request, payload):
    ... print 'A get on "contacts" was just performed!'

    >>> app = Eve()

    >>> app.on_post_GET += post_get_callback
    >>> app.on_post_GET_contacts += post_contacts_get_callback

    >>> app.run()

Database event hooks
~~~~~~~~~~~~~~~~~~~~

Database event hooks work like request event hooks. These events are fired
before and after a database action. Here is an example of how events are
configured:

.. code-block:: pycon

   >>> def add_signature(resource, response):
   ...     response['SIGNATURE'] = "A %s from eve" % resource

   >>> app = Eve()
   >>> app.on_fetched_item += add_signature

The events are fired for resources and items if the action is available for
both. And for each action two events will be fired:

- Generic: ``on_<action_name>``
- With the name of the resource: ``on_<action_name>_<resource_name>``

Let's see an overview of what events are available:

+-------+--------+------+-------------------------------------------------+
|Action |What    |When  |Event name / method signature                    |
+=======+========+======+=================================================+
|Fetch  |Resource|After || ``on_fetched_resource``                        |
|       |        |      || ``def event(resource_name, response)``         |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_fetched_resource_<resource_name>``        |
|       |        |      || ``def event(response)``                        |
|       +--------+------+-------------------------------------------------+
|       |Item    |After || ``on_fetched_item``                            |
|       |        |      || ``def event(resource_name, response)``         |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_fetched_item_<resource_name>``            |
|       |        |      || ``def event(response)``                        |
+-------+--------+------+-------------------------------------------------+
|Insert |Items   |Before|| ``on_insert``                                  |
|       |        |      || ``def event(resource_name, items)``            |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_insert_<resource_name>``                  |
|       |        |      || ``def event(items)``                           |
|       |        +------+-------------------------------------------------+
|       |        |After || ``on_inserted``                                |
|       |        |      || ``def event(resource_name, items)``            |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_inserted_<resource_name>``                |
|       |        |      || ``def event(items)``                           |
+-------+--------+------+-------------------------------------------------+
|Replace|Item    |Before|| ``on_replace``                                 |
|       |        |      || ``def event(resource_name, item, original)``   |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_replace_<resource_name>``                 |
|       |        |      || ``def event(item, original)``                  |
|       |        +------+-------------------------------------------------+
|       |        |After || ``on_replaced``                                |
|       |        |      || ``def event(resource_name, item, original)``   |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_replaced_<resource_name>``                |
|       |        |      || ``def event(item, original)``                  |
+-------+--------+------+-------------------------------------------------+
|Update |Item    |Before|| ``on_update``                                  |
|       |        |      || ``def event(resource_name, updates, original)``|
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_update_<resource_name>``                  |
|       |        |      || ``def event(updates, original)``               |
|       |        +------+-------------------------------------------------+
|       |        |After || ``on_updated``                                 |
|       |        |      || ``def event(resource_name, updates, original)``|
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_updated_<resource_name>``                 |
|       |        |      || ``def event(updates, original)``               |
+-------+--------+------+-------------------------------------------------+
|Delete |Item    |Before|| ``on_delete_item``                             |
|       |        |      || ``def event(resource_name, item)``             |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_delete_item_<resource_name>``             |
|       |        |      || ``def event(item)``                            |
|       |        +------+-------------------------------------------------+
|       |        |After || ``on_deleted_item``                            |
|       |        |      || ``def event(resource_name, item)``             |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_deleted_item_<resource_name>``            |
|       |        |      || ``def event(item)``                            |
|       +--------+------+-------------------------------------------------+
|       |Resource|Before|| ``on_delete_resource``                         |
|       |        |      || ``def event(resource_name, item)``             |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_delete_resource_<resource_name>``         |
|       |        |      || ``def event(item)``                            |
|       |        +------+-------------------------------------------------+
|       |        |After || ``on_deleted_resource``                        |
|       |        |      || ``def event(resource_name, item)``             |
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_deleted_resource_<resource_name>``        |
|       |        |      || ``def event(item)``                            |
+-------+--------+------+-------------------------------------------------+



Fetch Events
^^^^^^^^^^^^

These are the fetch events with their method signature:

- ``on_fetched_resource(resource_name, response)``
- ``on_fetched_resource_<resource_name>(response)``
- ``on_fetched_item(resource_name, response)``
- ``on_fetched_item_<resource_name>(response)``

They are raised when items have just been read from the database and are
about to be sent to the client. Registered callback functions can manipulate
the items as needed before they are returned to the client.

.. code-block:: pycon

    >>> def before_returning_items(resource_name, response):
    ...  print 'About to return items from "%s" ' % resource_name

    >>> def before_returning_contacts(response):
    ...  print 'About to return contacts'

    >>> def before_returning_item(resource_name, response):
    ...  print 'About to return an item from "%s" ' % resource_name

    >>> def before_returning_contact(response):
    ...  print 'About to return a contact'

    >>> app = Eve()
    >>> app.on_fetched_resource += before_returning_items
    >>> app.on_fetched_resource_contacts += before_returning_contacts
    >>> app.on_fetched_item += before_returning_item
    >>> app.on_fetched_item_contact += before_returning_contact


Insert Events
^^^^^^^^^^^^^

These are the insert events with their method signature:

- ``on_insert(resource_name, items)``
- ``on_insert_<resource_name>(items)``
- ``on_inserted(resource_name, items)``
- ``on_inserted_<resource_name>(items)``

When a POST requests hits the API and new items are about to be stored in
the database, these vents are fired:

- ``on_insert`` for every resource endpoint.
- ``on_insert_<resource_name>`` for the specific `<resource_name>` resource
  endpoint.

Callback functions could hook into these events to arbitrarily add new fields
or edit existing ones.

After the items have been inserted, these two events are fired:

- ``on_inserted`` for every resource endpoint.
- ``on_inserted_<resource_name>`` for the specific `<resource_name>` resource
  endpoint.

.. admonition:: Validation errors

    Items passed to these events as arguments come in a list. And only those items
    that passed validation are sent.

Example:

.. code-block:: pycon

    >>> def before_insert(resource_name, items):
    ...  print 'About to store items to "%s" ' % resource

    >>> def after_insert_contacts(items):
    ...  print 'About to store contacts'

    >>> app = Eve()
    >>> app.on_insert += before_insert
    >>> app.on_inserted_contacts += after_insert_contacts


Replace Events
^^^^^^^^^^^^^^

These are the replace events with their method signature:

- ``on_replace(resource_name, item, original)``
- ``on_replace_<resource_name>(item, original)``
- ``on_replaced(resource_name, item, original)``
- ``on_replaced_<resource_name>(item, original)``

When a PUT request hits the API and an item is about to be replaced after
passing validation, these events are fired:

- ``on_replace`` for any resource item endpoint.
- ``on_replace_<resource_name>`` for the specific resource endpoint.

`item` is the new item which is about to be stored. `original` is the item in
the database that is being replaced. Callback functions could hook into these
events to arbitrarily add or update `item` fields, or to perform other
accessory action.

After the item has been replaced, these other two events are fired:

- ``on_replaced`` for any resource item endpoint.
- ``on_replaced_<resource_name>`` for the specific resource endpont.

Update Events
^^^^^^^^^^^^^

These are the update events with their method signature:

- ``on_update(resource_name, updates, original)``
- ``on_update_<resource_name>(updates, original)``
- ``on_updated(resource_name, updates, original)``
- ``on_updated_<resource_name>(updates, original)``

When a PATCH request hits the API and an item is about to be updated after
passing validation, these events are fired `before` the item is updated:

- ``on_update`` for any resource endpoint.
- ``on_update_<resource_name>`` is fired only when the `<resource_name>`
  endpoint is hit.

Here `updates` stands for updates being applied to the item and `original` is
the item in the database that is about to be updated. Callback functions
could hook into these events to arbitrarily add or update fields in
`updates`, or to perform other accessory action.

`After` the item has been updated: 

- ``on_updated`` is fired for any resource endpoint.
- ``on_updated_<resource_name>`` is fired only when the `<resource_name>`
  endpoint is hit.

.. admonition:: Please note

    Please be aware that ``last_modified`` and ``etag`` headers will always be
    consistent with the state of the items on the database (they  won't be
    updated to reflect changes eventually applied by the callback functions).

Delete Events
^^^^^^^^^^^^^

These are the delete events with their method signature:

- ``on_delete_item(resource_name, item)``
- ``on_delete_item_<resource_name>(item)``
- ``on_deleted_item(resource_name, item)``
- ``on_deleted_item_<resource_name>(item)``
- ``on_delete_resource(resource_name)``
- ``on_delete_resource_<resource_name>()``
- ``on_deleted_resource(resource_name)``
- ``on_deleted_resource_<resource_name>()``

Items
.....

When a DELETE request hits an item endpoint and `before` the item is deleted,
these events are fired:

- ``on_delete_item`` for any resource hit by the request.
- ``on_delete_item_<resource_name>`` for the specific `<resource_name>` item endpoint
  hit by the DELETE.

`After` the item has been deleted the ``on_deleted_item(resource_name,
item)`` and ``on_deleted_item_<resource_name>(item)`` are raised.

`item` is the item being deleted. Callback functions could hook into
these events to perform accessory actions. And no you can't arbitrarily abort
the delete operation at this point (you should probably look at
:ref:`validation`, or eventually disable the delete command altogether).

Resources
.........

If you were brave enough to enable the DELETE command on resource endpoints
(allowing for wipeout of the entire collection in one go), then you can be
notified of such a disastrous occurence by hooking a callback function to the
``on_delete_resource(resource_name)`` or
``on_delete_resource_<resource_name>()`` hooks.


.. admonition:: Please note

    To provide seamless event handling features Eve relies on the Events_ package.

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

Custom ID Fields
----------------
Eve allows to extend its standard data type support. In the :ref:`custom_ids`
tutorial we see how it is possible to use UUID values instead of MongoDB
default ObjectIds as unique document identifiers.

File Storage
------------
Media files (images, pdf, etc.) can be uploaded as ``media`` document
fields. Upload is done via ``POST``, ``PUT`` and
``PATCH`` as usual, but using the ``multipart/data-form`` content-type.

Let us assume that the ``accounts`` endpoint has a schema like this:

.. code-block:: python

    accounts = {
        'name': {'type': 'string'},
        'pic': {'type': 'media'},
        ...
    }

With curl we would ``POST`` like this:

.. code-block:: console

    $ curl -F "name=john" -F "pic=@profile.jpg" http://example.com/accounts

For optmized performance files are stored in GridFS_ by default. Custom
``MediaStorage`` classes can be implemented and passed to the application to
support alternative storage systems. A ``FileSystemMediaStorage`` class is in
the works, and will soon be included with the Eve package.

As a proper developer guide is not available yet, you can peek at the
MediaStorage_ source if you are interested in developing custom storage
classes.

When a document is requested media files will be returned as Base64 strings,
unless the `EXTENDED_MEDIA_INFO` list is populated. This flag allows
passthrough from the driver of additional, meta fields. For example,
using the MongoDB driver, fields like `content_type` and `length` can be
added to this list and will be passed-through from the underlying driver.
Further fields can be found in the MongoDB driver [documentation](http://api.mongodb.org/python/2.7rc0/api/gridfs/grid_file.html#gridfs.grid_file.GridOut).


.. _projection_filestorage:

Leveraging Projections to optimize the handling of media files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Clients and API maintainers can exploit the :ref:`projections` feature to
include/exclude media fields from response payloads.

Suppose that a client stored a document with an image. The image field is
called *image* and it is of ``media`` type. At a later time, the client wants
to retrieve the same document but, in order to optimize for speed and since the
image is cached already, it does not want to download the image along with the
document. It can do so by requesting the field to be trimmed out of the
response payload:

.. code-block:: console

    $ curl -i http://example.com/people/<id>?projection={"image": 0}
    HTTP/1.1 200 OK

The document will be returned with all its fields except the *image* field.

Moreover, when setting the ``datasource`` property for any given resource
endpoint it is possible to explictly exclude fields (of ``media`` type, but
also of any other type) from default responses:

.. code-block:: python

    people = {
        'datasource': {
            'projection': {'image': 0}
        },
        ...
    }

Now clients will have to explicitly request the image field to be included with
response payloads by sending requests like this one:

.. code-block:: console

    $ curl -i http://example.com/people/<id>?projection={"image": 1}
    HTTP/1.1 200 OK

.. admonition:: See also

    - :ref:`config`
    - :ref:`datasource`

    for details on the ``datasource`` setting.

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
.. _`MongoDB Data Model Design`: http://docs.mongodb.org/manual/core/data-model-design
.. _GridFS: http://docs.mongodb.org/manual/core/gridfs/
.. _MediaStorage: https://github.com/nicolaiarocci/eve/blob/develop/eve/io/media.py
