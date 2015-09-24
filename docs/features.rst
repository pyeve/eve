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
Create  PUT       Document
Replace PUT       Document
Read    GET, HEAD Collection/Document
Update  PATCH     Document
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
                    "self": {"href": "people/50bf198338345b1c604faf31", "title": "person"},
                },
            },
            ...
        ],
        "_meta": {
            "max_results": 25,
            "total": 70,
            "page": 1
        },
        "_links": {
            "self": {"href": "people", "title": "people"},
            "parent": {"href": "/", "title": "home"}
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

The ``_meta`` field provides pagination data and will only be there if
:ref:`Pagination` has been enabled (it is by default) and there is at least one
document being returned. The ``_links`` list provides HATEOAS_ directives.

.. _subresources:

Sub Resources
~~~~~~~~~~~~~
Endpoints support sub-resources so you could have something like:
``people/<contact_id>/invoices``. When setting the ``url`` rule for such and
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
be achieved by simply exposing an ``invoices`` endpoint that clients could query
this way:

::

    invoices?where={"contact_id": 51f63e0838345b6dcd7eabff}

or

::

    invoices?where={"contact_id": 51f63e0838345b6dcd7eabff, "number": 10}

It's mostly a design choice, but keep in mind that when it comes to enabling
individual document endpoints you might incur performance hits. This
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
get access to ``people``, ``people/<ObjectId>`` and ``people/Doe``,
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
            "self": {"href": "people/50acfba938345b0978fccad7", "title": "person"},
            "parent": {"href": "/", "title": "home"},
            "collection": {"href": "people", "title": "people"}
        }
    }

As you can see, item endpoints provide their own HATEOAS_ directives.

.. admonition:: Please Note

    According to REST principles resource items should only have one unique
    identifier. Eve abides by providing one default endpoint per item. Adding
    a secondary endpoint is a decision that should be pondered carefully.

    Consider our example above. Even without the ``people/<lastname>``
    endpoint, a client could always retrieve a person by querying the resource
    endpoint by last name: ``people/?where={"lastname": "Doe"}``. Actually the
    whole example is fubar, as there could be multiple people sharing the same
    last name, but you get the idea.

.. _filters:

Filtering
---------
Resource endpoints allow consumers to retrieve multiple documents. Query
strings are supported, allowing for filtering and sorting. Two query syntaxes
are supported. The mongo query syntax:

::

    http://eve-demo.herokuapp.com/people?where={"lastname": "Doe"}

which translates to the following ``curl`` request:

.. code-block:: console

    $ curl -i -g http://eve-demo.herokuapp.com/people?where={%22lastname%22:%20%22Doe%22}
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

Sorting
-------
Sorting is supported as well:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?sort=city,-lastname
    HTTP/1.1 200 OK

Would return documents sorted by city and then by lastname (descending). As you
can see you simply prepend a minus to the field name if you need the sort order
to be reversed for a field.

The MongoDB data layer also supports native MongoDB syntax:

::

    http://eve-demo.herokuapp.com/people?sort=[("lastname", -1)]

which translates to the following ``curl`` request:

.. code-block:: console

    $ curl -i http://eve-demo.herokuapp.com/people?sort=[(%22lastname%22,%20-1)]
    HTTP/1.1 200 OK

Would return documents sorted by lastname in descending order.

Sorting is enabled by default and can be disabled both globally and/or at
resource level (see ``SORTING`` in :ref:`global` and ``sorting`` in
:ref:`domain`). It is also possible to set the default sort at every API
endpoints (see ``default_sort`` in :ref:`domain`). 

.. admonition:: Please note

    Always use double quotes to wrap field names and values. Using single
    quotes will result in ``400 Bad Request`` responses.

.. _pagination:

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

Pagination can be disabled. Please note that, for clarity, the above example is
not properly escaped. If using ``curl``, refer to the examples provided in
:ref:`filters`.

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
                "href": "people",
                "title": "people"
            },
            "parent": {
                "href": "/",
                "title": "home"
            },
            "next": {
                "href": "people?page=2",
                "title": "next page"
            },
            "last": {
                "href": "people?page=10",
                "title": "last page"
            }
        }
    }

A GET request to the API home page (the API entry point) will be served with
a list of links to accessible resources. From there, any client could navigate
the API just by following the links provided with every response.

HATEOAS links are always relative to the API entry point, so if your API home
is at ``examples.com/api/v1``, the ``self`` link in the above example would
mean that the *people* endpoint is located at ``examples.com/api/v1/people``.

Please note that ``next``, ``previous`` and ``last`` items will only be
included when appropriate. 

Disabling HATEOAS
~~~~~~~~~~~~~~~~~
HATEOAS can be disabled both at the API and/or resource level. Why would you
want to turn HATEOAS off? Well, if you know that your client application is not
going to use the feature, then you might want to save on both bandwidth and
performance. 

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
        <link rel="child" href="people" title="people" />
        <link rel="child" href="works" title="works" />
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
conditional requests by using the ``If-Modified-Since`` header:

.. code-block:: console

    $ curl -H "If-Modified-Since: Wed, 05 Dec 2012 09:53:07 GMT" -i http://eve-demo.herokuapp.com/people/521d6840c437dc0002d1203c 
    HTTP/1.1 200 OK

or the ``If-None-Match`` header:

.. code-block:: console

    $ curl -H "If-None-Match: 1234567890123456789012345678901234567890" -i http://eve-demo.herokuapp.com/people/521d6840c437dc0002d1203c 
    HTTP/1.1 200 OK


.. _concurrency:

Data Integrity and Concurrency Control
--------------------------------------
API responses include a ``ETag`` header which also allows for proper
concurrency control. An ``ETag`` is a hash value representing the current state
of the resource on the server. Consumers are not allowed to edit (``PATCH`` or
``PUT``) or delete (``DELETE``) a resource unless they provide an up-to-date
``ETag`` for the resource they are attempting to edit. This prevents
overwriting items with obsolete versions.

Consider the following workflow:

.. code-block:: console

    $ curl -H "Content-Type: application/json" -X PATCH -i http://eve-demo.herokuapp.com/people/521d6840c437dc0002d1203c -d '{"firstname": "ronald"}'
    HTTP/1.1 403 FORBIDDEN

We attempted an edit (``PATCH``), but we did not provide an ``ETag`` for the
item so we got a ``403 FORBIDDEN`` back. Let's try again:

.. code-block:: console

    $ curl -H "If-Match: 1234567890123456789012345678901234567890" -H "Content-Type: application/json" -X PATCH -i http://eve-demo.herokuapp.com/people/521d6840c437dc0002d1203c -d '{"firstname": "ronald"}'
    HTTP/1.1 412 PRECONDITION FAILED

What went wrong this time? We provided the mandatory ``If-Match`` header, but
it's value did not match the ``ETag`` computed on the representation of the item
currently stored on the server, so we got a ``412 PRECONDITION FAILED``. Again!

.. code-block:: console

    $ curl -H "If-Match: 80b81f314712932a4d4ea75ab0b76a4eea613012" -H "Content-Type: application/json" -X PATCH -i http://eve-demo.herokuapp.com/people/50adfa4038345b1049c88a37 -d '{"firstname": "ronald"}'
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
        "_links": {"self": {"href": "people/50ae43339fa12500024def5b", "title": "person"}}
    }

However, in order to reduce the number of loopbacks, a client might also submit
multiple documents with a single request. All it needs to do is enclose the
documents in a JSON list:

.. code-block:: console

    $ curl -d '[{"firstname": "barack", "lastname": "obama"}, {"firstname": "mitt", "lastname": "romney"}]' -H 'Content-Type: application/json' http://eve-demo.herokuapp.com/people
    HTTP/1.1 201 OK

The response will be a list itself, with the state of each document:

.. code-block:: javascript

    {
        "_status": "OK",
        "_items": [
            {
                "_status": "OK",
                "_updated": "Thu, 22 Nov 2012 15:22:27 GMT",
                "_id": "50ae43339fa12500024def5b",
                "_etag": "749093d334ebd05cf7f2b7dbfb7868605578db2c"
                "_links": {"self": {"href": "people/50ae43339fa12500024def5b", "title": "person"}}
            },
            {
                "_status": "OK",
                "_updated": "Thu, 22 Nov 2012 15:22:27 GMT",
                "_id": "50ae43339fa12500024def5c",
                "_etag": "62d356f623c7d9dc864ffa5facc47dced4ba6907"
                "_links": {"self": {"href": "people/50ae43339fa12500024def5c", "title": "person"}}
            }
        ]
    }

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

    {
        "_status": "ERR",
        "_error": "Some documents contains errors",
        "_items": [
            {
                "_status": "ERR",
                "_issues": {"lastname": "value 'clinton' not unique"}
            },
            {
                "_status": "OK",
            }
        ]
    ]

In the example above, the first document did not validate so the whole request
has been rejected. 

When all documents pass validation and are inserted correctly the response
status is ``201 Created``. If any document fails validation the response status
is ``422 Unprocessable Entity``, or any other error code defined by
``VALIDATION_ERROR_STATUS`` configuration.

For more information see :ref:`validation`.

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

Additionally, there are caching corner cases unique to document versions. A
specific document version includes the ``_latest_version`` field, the value of
which will change when a new document version is created. To account for this,
Eve determines the time ``_latest_version`` changed (the timestamp of the last
update to the primary document) and uses that value to populate the
``Last-Modified`` header and check the ``If-Modified-Since`` conditional cache
validator of specific document version queries. Note that this will be
different from the timestamp in the version's last updated field. The etag for
a document version does not change when ``_latest_version`` changes, however.
This results in two corner cases. First, because Eve cannot determine if the
client's ``_latest_version`` is up to date from an ETag alone, a query using
only ``If-None-Match`` for cache validation of old document versions will always
have its cache invalidated. Second, a version fetched and cached in the same
second that multiple new versions are created can receive incorrect
``Not Modified`` responses on ensuing ``GET`` queries due to ``Last-Modified``
values having a resolution of one second and the static etag values not
providing indication of the changes. These are both highly unlikely scenarios,
but an application expecting multiple edits per second should account for the
possibility of holing stale ``_latest_version`` data.

For more information see and :ref:`global` and :ref:`domain`.


Authentication
--------------
Customizable Basic Authentication (RFC-2617), Token-based authentication and
HMAC-based Authentication are supported. OAuth2 can be easily integrated. You
can lockdown the whole API, or just some endpoints. You can also restrict CRUD
commands, like allowing open read-only access while restricting edits, inserts
and deletes to authorized users. Role-based access control is supported as
well. For more information see :ref:`auth`.

CORS Cross-Origin Resource Sharing
----------------------------------
Disabled by default, CORS_ allows web pages to work with REST APIs, something
that is usually restricted by most broswers 'same domain' security policy.
Eve-powered APIs can be accessed by the JavaScript contained in web pages.

JSONP Support
-------------
In general you don't really want to add JSONP when you can enable CORS instead:

    There have been some criticisms raised about JSONP. Cross-origin resource
    sharing (CORS) is a more recent method of getting data from a server in
    a different domain, which addresses some of those criticisms. All modern
    browsers now support CORS making it a viable cross-browser alternative (source_.)

There are circumstances however when you do need JSONP, like when you have to
support legacy software (IE6 anyone?) 

To enable JSONP in Eve you just set
``JSONP_ARGUMENT``. Then, any valid request with ``JSONP_ARGUMENT`` will get
back a response wrapped with said argument value. For example if you set
``JSON_ARGUMENT = 'callback'``:

.. code-block:: console

    $ curl -i http://localhost:5000/?callback=hello
    hello(<JSON here>)

Requests with no ``callback`` argument will be served with no JSONP.
 

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
serialization. If the listed fields are embeddable and they are actually referencing
documents in other resources (and embedding is enbaled for the resource), then the
referenced documents will be embedded by default. Clients can still opt out from field
that are embedded by default:

.. code-block:: console

    $ curl -i http://example.com/people/?embedded{"author": 0}
    HTTP/1.1 200 OK

Limitations
~~~~~~~~~~~
Currently we support embedding of documents by references located in any
subdocuments (nested dicts and lists). For example, a query
``/invoices?/embedded={"user.friends":1}`` will return a document with ``user``
and all his ``friends`` embedded, but only if ``user`` is a subdocument and
``friends`` is a list of reference (it could be a list of dicts, nested
dict, ect.). We *do not* support multiple layers embeddings. This feature is
about serialization on GET requests. There's no support for POST, PUT or PATCH
of embedded documents.

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

.. _soft_delete:

Soft Delete
-----------
Eve provides an optional "soft delete" mode in which deleted documents continue
to be stored in the database and are able to be restored, but still act as
removed items in response to API requests. Soft delete is disabled by default,
but can be enabled globally using the ``SOFT_DELETE`` configuration setting, or
individually configured at the resource level using the domain configuration
``soft_delete`` setting. See :ref:`global` and :ref:`domain` for more
information on enabling and configuring soft delete.

Behavior
~~~~~~~~
With soft delete enabled, DELETE requests to individual items and resources
respond just as they do for a traditional "hard" delete. Behind the scenes,
however, Eve does not remove deleted items from the database, but instead
patches the document with a ``_deleted`` meta field set to ``true``. (The name
of the ``_deleted`` field is configurable. See :ref:`global`.) All requests
made when soft delete is enabled filter against or otherwise account for the
``_deleted`` field.

The ``_deleted`` field is automatically added and initialized to ``false`` for
all documents created while soft delete is enabled. Documents created prior to
soft delete being enabled and which therefore do not define the ``_deleted``
field in the database will still include ``_deleted: false`` in API response
data, added by Eve during response construction. PUTs or PATCHes to these
documents will add the ``_deleted`` field to the stored documents, set to
``false``.

Responses to GET requests for soft deleted documents vary slightly from
responses to missing or "hard" deleted documents. GET requests for soft deleted
documents will still respond with ``404 Not Found`` status codes, but the
response body will contain the soft deleted document with ``_deleted: true``.
Documents embedded in the deleted document will not be expanded in the
response, regardless of any default settings or the contents of the request's
``embedded`` query param. This is to ensure that soft deleted documents
included in ``404`` responses reflect the state of a document when it was
deleted, and do not to change if embedded documents are updated.

By default, resource level GET requests will not include soft deleted items in
their response. This behavior matches that of requests after a "hard" delete.
If including deleted items in the response is desired, the ``show_deleted``
query param can be added to the request. (the ``show_deleted`` param name is
configurable. See :ref:`global`) Eve will respond with all documents, deleted
or not, and it is up to the client to parse returned documents' ``_deleted``
field. The ``_deleted`` field can also be explicitly filtered against in a
request, allowing only deleted documents to be returned using a
``?where={"_deleted": true}`` query.

Soft delete is enforced in the data layer, meaning queries made by application
code using the ``app.data.find_one`` and ``app.data.find`` methods will
automatically filter out soft deleted items. Passing a request object with
``req.show_deleted == True`` or a lookup dictionary that explicitly filters on
the ``_deleted`` field will override the default filtering.

Restoring Soft Deleted Items
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
PUT or PATCH requests made to a soft deleted document will restore it,
automatically setting ``_deleted`` to ``false`` in the database. Modifying the
``_deleted`` field directly is not necessary (or allowed). For example, using
PATCH requests, only the fields to be changed in the restored version would be
specified, or an empty request would be made to restore the document as is. The
request must be made with proper authorization for write permission to the soft
deleted document or it will be refused.

Versioning
~~~~~~~~~~
Soft deleting a versioned document creates a new version of that document with
``_deleted`` set to ``true``. A GET request to the deleted version will recieve
a ``404 Not Found`` response as described above, while previous versions will
continue to respond with ``200 OK``. Responses to ``?version=diff`` or
``?version=all`` will include the deleted version as if it were any other.

Data Relations
~~~~~~~~~~~~~~
The Eve ``data_relation`` validator will not allow references to documents that
have been soft deleted. Attempting to create or update a document with a
reference to a soft deleted document will fail just as if that document had
been hard deleted. Existing data relations to documents that are soft deleted
remain in the database, but requests requiring embedded document serialization
of those relations will resolve to a null value. Again, this matches the
behavior of relations to hard deleted documents.

Versioned data relations to a deleted document version will also fail to
validate, but relations to versions prior to deletion or after restoration of
the document are allowed and will continue to resolve successfully.

Considerations
~~~~~~~~~~~~~~
Disabling soft delete after use in an application requires database maintenance
to ensure your API remains consistent. With soft delete disabled, requests will
no longer filter against or handle the ``_deleted`` field, and documents that
were soft deleted will now be live again on your API. It is therefore necessary
when disabling soft delete to perform a data migration to remove all documents
with ``_deleted == True``, and recommended to remove the ``_deleted`` field
from documents where ``_deleted == False``. Enabling soft delete in an existing
application is safe, and will maintain documents deleted from that point on.

.. _eventhooks:

Event Hooks
-----------
Pre-Request Event Hooks
~~~~~~~~~~~~~~~~~~~~~~~
When a GET/HEAD, POST, PATCH, PUT, DELETE request is received, both
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

You may use flask's ``abort()`` to interrupt the database operation:

.. code-block:: pycon

   >>> from flask import abort

   >>> def check_update_access(resource, updates, original):
   ...     abort(403)

   >>> app = Eve()
   >>> app.on_insert_item += check_update_access

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
|       |        |      || ``def event(resource_name, updated, original)``|
|       |        |      +-------------------------------------------------+
|       |        |      || ``on_updated_<resource_name>``                 |
|       |        |      || ``def event(updated, original)``               |
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

It is important to note that fetch events will work with `Document
Versioning`_ for specific document versions or accessing all document
versions with ``?version=all``, but they *will not* work when acessing diffs
of all versions with ``?version=diffs``.


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

Serving media files as Base64 strings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
When a document is requested media files will be returned as Base64 strings,

.. code-block:: python

    {
        '_items': [
            {
                '_updated':'Sat, 05 Apr 2014 15:52:53 GMT',
                'pic':'iVBORw0KGgoAAAANSUhEUgAAA4AAAAOACA...',
            }
        ]
        ...
   } 

However, if the ``EXTENDED_MEDIA_INFO`` list is populated (it isn't by
default) the payload format will be different. This flag allows passthrough
from the driver of additional meta fields. For example, using the MongoDB
driver, fields like ``content_type``, ``name`` and ``length`` can be added to
this list and will be passed-through from the underlying driver. 

When ``EXTENDED_MEDIA_INFO`` is used the field will be a dictionary
whereas the file itself is stored under the ``file`` key and other keys
are the meta fields. Suppose that the flag is set like this:

.. code-block:: python

    EXTENDED_MEDIA_INFO = ['content_type', 'name', 'length']

Then the output will be something like

.. code-block:: python

    {
        '_items': [
            {
                '_updated':'Sat, 05 Apr 2014 15:52:53 GMT',
                'pic': {
                    'file': 'iVBORw0KGgoAAAANSUhEUgAAA4AAAAOACA...',
                    'content_type': 'text/plain',
                    'name': 'test.txt',
                    'length': 8129
                }
            }
        ]
        ...
    }

For MongoDB, further fields can be found in the `driver documentation`_. 

If you have other means to retrieve the media files (custom Flask endpoint for
example) then the media files can be excluded from the paylod by setting to
``False`` the ``RETURN_MEDIA_AS_BASE64_STRING`` flag. This takes into account
if ``EXTENDED_MEDIA_INFO`` is used.

Serving media files at a dedicated endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
While returning files embedded as Base64 fields is the default behaviour, you
can opt for serving them at a dedicated media endpoint. You achieve that by
setting ``RETURN_MEDIA_AS_URL`` to ``True``. When this feature is enabled
document fields contain urls to the correspondent files, which are served at the
media endpoint. 

You can change the default media endpoint (``media``) by updating the
``MEDIA_BASE_URL`` and ``MEDIA_ENDPOINT`` setting. Suppose you are storing your
images on Amazon S3 via a custom ``MediaStorage`` subclass. You would probably
set your media endpoint like so:

.. code-block:: python

    # disable default behaviour
    RETURN_MEDIA_AS_BASE64_STRING = False

    # return media as URL instead
    RETURN_MEDIA_AS_URL = True

    # set up the desired media endpoint
    MEDIA_BASE_URL = 'https://s3-us-west-2.amazonaws.com'
    MEDIA_ENDPOINT = 'media'

Setting ``MEDIA_BASE_URL`` is optional. If no value is set, then
the API base address will be used when building the URL for ``MEDIA_ENDPOINT``.

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
    
.. _geojson_feature:

GeoJSON
-------
The MongoDB data layer supports geographic data structures
encoded in GeoJSON_ format. All GeoJSON objects supported by MongoDB_ are available:

    - ``Point``
    - ``Multipoint``
    - ``LineString``
    - ``MultiLineString``
    - ``Polygon``
    - ``MultiPolygon``
    - ``GeometryCollection``
      
These are implemented as native Eve data types (see :ref:`schema`) so they are
are subject to proper validation.

In the example below we are extending the `people` endpoint by adding
a ``location`` field is of type Point_.

.. code-block:: javascript

    people = {
    	...
        'location': {
            'type': 'point'
        },
        ...
    }
    
Storing a contact along with its location is pretty straightforward:

.. code-block:: console

    $ curl -d '[{"firstname": "barack", "lastname": "obama", "location": {"type":"Point","coordinates":[100.0,10.0]}}]' -H 'Content-Type: application/json'  http://127.0.0.1:5000/people
    HTTP/1.1 201 OK

Querying GeoJSON Data
~~~~~~~~~~~~~~~~~~~~~
As a general rule all MongoDB `geospatial query operators`_ and their associated
geometry specifiers are supported. In this example we are using the `$near`_
operator to query for all contacts living in a location within 1000 meters from
a certain point:
    
::

    ?where={"location": {"$near": {"$geometry": {"type":"Point", "coordinates": [10.0, 20.0]}, "$maxDistance": 1000}}}

Please refer to MongoDB documentation for details on geo queries.
	
.. _internal_resources:

Internal Resources
------------------
By default responses to GET requests to the home endpoint will include all the
resources. The ``internal_resource`` setting keyword, however, allows you to
make an endpoint internal, available only for internal data manipulation: no
HTTP calls can be made against it and it will be excluded from the ``HATEOAS``
links.

An usage example would be a mechanism for logging all inserts happening in
the system, something that can be used for auditing or a notification system.
First we define an ``internal_transaction`` endpoint, which is flagged as an
``internal_resource``:

.. code-block:: python
   :emphasize-lines: 10

    internal_transactions = {
        'schema': {
            'entities': {
                'type': 'list',
            },
            'original_resource': {
                'type': 'string',
            },
        },
        'internal_resource': True
    }


Now, if we access the home endpoint and ``HATEOAS`` is enabled, we won't get
the ``internal-transactions`` listed (and hitting the endpoint via HTTP wil
return a ``404``.) We can use the data layer to access our secret endpoint.
Something like this:

.. code-block:: python
   :emphasize-lines: 12
    
    from eve import Eve

    def on_generic_inserted(self, resource, documents):
        if resource != 'internal_transactions':
            dt = datetime.now()
            transaction = {
                'entities':  [document['_id'] for document in documents],
                'original_resource': resource,
                config.LAST_UPDATED: dt,
                config.DATE_CREATED: dt,
            }
            app.data.insert('internal_transactions', [transaction])

    app = Eve()
    app.on_inserted += self.on_generic_inserted

    app.run()

I admit that this example is as rudimentary as it can get, but hopefully it
will get the point across.

.. _logging:

Enhanced Logging
----------------
A number of events are available for logging via the default application
logger. The standard `LogRecord attributes`_ are extended with a few request
attributes:

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

=================================== =========================================
``clientip``                        IP address of the client performing the
                                    request.

``url``                             Full request URL, eventual query parameters 
                                    included.

``method``                          Request method (``POST``, ``GET``, etc.)

=================================== =========================================


You can use these fields when logging to a file or any other destination.

Callback functions can also take advantage of the builtin logger. The following
example logs application events to a file, and also logs custom messages every
time a custom function is invoked.

.. code-block:: python

    import logging

    from eve import Eve

    def log_every_get(resoure, request, payload):
        # custom INFO-level message is sent to the log file
        app.logger.info('We just answered to a GET request!')

    app = Eve()
    app.on_post_GET += log_every_get

    if __name__ == '__main__':

        # enable logging to 'app.log' file
        handler = logging.FileHandler('app.log')

        # set a custom log format, and add request 
        # metadata to each log line
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(filename)s:%(lineno)d] -- ip: %(clientip)s, '
            'url: %(url)s, method:%(method)s'))

        # the default log level is set to WARNING, so
        # we have to explictly set the logging level 
        # to INFO to get our custom message logged.
        app.logger.setLevel(logging.INFO)

        # append the handler to the default application logger
        app.logger.addHandler(handler)

        # let's go
        app.run()


Currently only exceptions raised by the MongoDB layer and ``POST``, ``PATCH``
and ``PUT`` methods are logged. The idea is to also add some ``INFO`` and
possibly ``DEBUG`` level events in the future. 

.. _oplog:

Operations Log
--------------
The OpLog is an API-wide log of all edit operations. Every ``POST``, ``PATCH``
``PUT`` and ``DELETE`` operation can be recorded to the oplog. At its core the
oplog is simply a server log. What makes it a little bit different is that it
can be exposed as a read-only endpoint, thus allowing clients to query it as
they would with any other API endpoint.

Every oplog entry contains informations about the document and the operation:

- Operation performed
- Unique ID of the document
- Update date
- Creation date
- Resource endpoint URL
- User token, if :ref:`user-restricted` is enabled for the endpoint

Like any other API-maintained document, oplog entries also expose:

- Entry ID
- ETag
- HATEOAS fields if that's enabled.

If ``OPLOG_AUDIT`` is enabled entries also expose both client IP and changes
applied to the document (for ``DELETE`` the whole document is included).

A typical oplog entry looks like this:

.. code-block:: python

    {
        "o": "DELETE", 
        "r": "people", 
        "i": "542d118938345b614ea75b3c",
        "c": {...},
        "ip": "127.0.0.1",
        "_updated": "Fri, 03 Oct 2014 08:16:52 GMT", 
        "_created": "Fri, 03 Oct 2014 08:16:52 GMT",
        "_etag": "e17218fbca41cb0ee6a5a5933fb9ee4f4ca7e5d6"
        "_id": "542e5b7438345b6dadf95ba5", 
        "_links": {...},
    }

To save a little space (at least on MongoDB) field names have been shortened: 

- ``o`` stands for operation performed
- ``r`` stands for resource endpoint
- ``i`` stands for document id
- ``ip`` is the client IP
- ``c`` stands for changes occurred 
  
``_created`` and ``_updated`` are relative to the target document, which comes
handy in a variety of scenarios (like when the oplog is available to clients,
more on this later).

How is the oplog operated?
~~~~~~~~~~~~~~~~~~~~~~~~~~
Six settings are dedicated to the OpLog:

- ``OPLOG`` switches the oplog feature on and off. Defaults to ``False``.
- ``OPLOG_NAME`` is the name of the oplog collection on the database. Defaults to ``oplog``.
- ``OPLOG_METHODS`` is a list of HTTP methods to be logged. Defaults to all of them.
- ``OPLOG_ENDPOINT`` is the endpoint name. Defaults to ``None``.
- ``OPLOG_AUDIT`` if enabled, IP addresses and changes are also logged. Defaults to ``True``.

As you can see the oplog feature is turned off by default. Also, since
``OPLOG_ENDPOINT`` defaults to ``None``, even if you switch the feature on no
public oplog endpoint will be available. You will have to explictly set the
endpoint name in order to expose your oplog to the public. 

The Oplog endpoint
~~~~~~~~~~~~~~~~~~
Since the oplog endpoint is nothing but a standard API endpoint, you can
customize it. This allows for setting up custom authentication
(you might want this resource to be only accessible for administrative
purposes) or any other useful setting. 

Note that while you can change most of its settings, the endpoint will always
be read-only so setting either ``resource_methods`` or ``item_methods`` to
something other than ``['GET']`` will serve no purpose. Also, unless you need to
customize it, adding an oplog entry to the domain is not really necessary as it
will be added for you automatically.

Exposing the oplog as an endpoint could be useful in scenarios where you have
multiple clients (say phone, tablet, web and desktop apps) which need to stay
in sync with each other and the server. Instead of hitting every single
endpoint they could just access the oplog to learn all that's happened
since their last access. That’s a single request versus several. This is not
always the best approach a client could take. Sometimes it is probably better
to only query for changes on a certain endpoint. That's also possible, just
query the oplog for changes occured on that endpoint.

.. note:: 

    Are you on MongoDB? Consider making the oplog a `capped collection`_. Also,
    in case you are wondering yes, the Eve oplog is blatantly inpsired by the
    awesome `Replica Set Oplog`_.

.. _schema_endpoint:

The Schema Endpoint
-------------------
Resource schema can be exposed to API clients by enabling Eve's schema
endpoint. To do so, set the ``SCHEMA_ENDPOINT`` configuration option to the API
endpoint name from which you want to serve schema data. Once enabled, Eve will
treat the endpoint as a read only resource containing JSON encoded Cerberus
schema definitons, indexed by resource name. Resource visibility and
authorization settings are honored, so internal resources or resources for
which a request does not have read authentication will not be accessible at the
schema endpoint. By default, ``SCHEMA_ENDPOINT`` is set to ``None``.

MongoDB and SQL Support
------------------------
Support for single or multiple MongoDB database/servers comes out of the box.
An SQLAlchemy extension provides support for SQL backends. Additional data
layers can can be developed with relative ease. Visit the `extensions page`_
for a list of community developed data layers and extensions. 

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
.. _`driver documentation`: http://api.mongodb.org/python/2.7rc0/api/gridfs/grid_file.html#gridfs.grid_file.GridOut
.. _GeoJSON: http://geojson.org/
.. _Point: http://geojson.org/geojson-spec.html#point
.. _MongoDB: http://docs.mongodb.org/manual/applications/geospatial-indexes/#geojson-objects
.. _`geospatial query operators`: http://docs.mongodb.org/manual/reference/operator/query-geospatial/#query-selectors
.. _$near: http://docs.mongodb.org/manual/reference/operator/query/near/#op._S_near
.. _`capped collection`: http://docs.mongodb.org/manual/ore/capped-collections/
.. _`Replica Set Oplog`: http://docs.mongodb.org/manual/core/replica-set-oplog/
.. _`extensions page`: http://python-eve.org/extensions
.. _source: http://en.wikipedia.org/wiki/JSONP
.. _`LogRecord attributes`: https://docs.python.org/2/library/logging.html#logrecord-attributes 
