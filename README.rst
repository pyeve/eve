Eve
===
.. image:: https://secure.travis-ci.org/nicolaiarocci/eve.png?branch=master 
        :target: https://secure.travis-ci.org/nicolaiarocci/eve

Eve allows to effortlessly build and deploy a fully featured, REST-compliant,
proprietary API. 

Simple
------
Once Eve is installed this is what you will need to bring your glorified API
online:

- A database 
- A simple configuration file
- A minimal launch script
  
Support for MongoDB comes out of the box; extensions for other SQL/NoSQL
databases can be developed with relative ease. API settings are stored in
a standard Python module (defaults to ``settings.py``). Most of
the times the launch script will be as simple as::
    
    from eve import Eve

    app = Eve() 
    app.run()


Overall, you will find that configuring and fine-tuning your API is a very
simple process.  

Live demo and examples
----------------------
Check out the live demo of a Eve-powered API at
https://github.com/nicolaiarocci/eve-demo. It comes with source code and usage
examples for all common use cases (GET, POST, PATCH, DELETE and more). There is
also a sample client app available. Check it out at
https://github.com/nicolaiarocci/eve-demo-client.

Features
--------
- **Emphasis on the REST**. The Eve project aims to provide the best possibile
  REST-compliant API implementation. Basic REST principles like separation of
  concerns, stateless and layered system, cacheability, uniform interface, etc
  have been (hopefully!) kept into consideration while designing the core API.
  
- **Full range of CRUD operations via HTTP verbs**. APIs can support the full
  range of CRUD (Create, Read, Update, Delete) operations. You can have
  a read-only resource accessible at one endpoint along with a fully editable
  resource at another endpoint within the same API. The following table shows
  Eve's implementation of CRUD via REST

    ====== ========= ===================
    Action HTTP Verb Context 
    ====== ========= ===================
    Create POST      Collection
    Read   GET       Collection/Document
    Update PATCH     Document
    Delete DELETE    Collection/Document
    ====== ========= ===================

- **Read-only by default**. If all you need is a read-only API, then you can
  have it up and running real quick.

- **Customizable resource endpoints (persistent identifiers)**. By default Eve
  will make known database collections available as resource endpoints.
  A ``contacts`` collection in the database will be ready to be consumed at
  ``example.com/contacts/``. You can customize the URIs of your resources so
  in our example the API endpoint could become, say,
  ``example.com/customers/``. 

- **Customizable, multiple item endpoints**. Resources can or cannot provide
  access to their own individual items. API consumers could get access to
  ``/contacts/``, ``/contacts/<ObjectId>/`` and ``/contacts/smith/``, but only
  to ``/invoices/`` if so you wish.  When you do grant access to resource
  items, you can define up to two lookup endpoints, both defined via regex. The
  first will be the primary endpoint and will match your database primary key
  structure (i.e. an ObjectId in a MongoDB database).  The second, which is
  optional, will match a field with unique values, since Eve will retrieve only
  the first match anyway.

- **Filtering and sorting**. Resource endpoints allow consumers to retrieve
  multiple documents. Query strings are supported, allowing for filtering and
  sorting. 
  
- **Two query formats**. Currently two query formats are supported: the mongo
  query syntax (``?where={"name": "john doe"}``), and the native python syntax
  (``?where=name=='john doe'``). Both query formats allow for conditional and
  logical And/Or operators, however nested and combined.

- **Pagination**. Resource pagination is enabled by default in order to improve
  performance and preserve bandwith. When a consumer requests a resource, the
  first N items matching the query are serverd. Links to subsequent/previous
  pages are provided with the response. Default and maximum page size is
  customizable, and consumers can request specific pages via the query string
  (``?page=10``).

- **HATEOAS**. Hypermedia as the Engine of Application State is enabled by
  default. Each GET response includes a ``_links`` section. Links provide details on
  their ``relation`` relative to the resource being accessed and a ``title``.
  Titles and relations can be used by clients to dynamically updated their
  UI, or to navigate the API without knowing it structure beforehand. An
  example::
  
    {
      "_links": {
        "self": {
          "href": "localhost:5000/contatti/", 
          "title": "contatti"
        }, 
        "parent": {
          "href": "localhost:5000", 
          "title": "home"
        }, 
        "next": {
          "href": "localhost:5000/contatti/?page=2", 
          "title": "next page"
        }
      }
    }

  In fact, a GET request to the API home page (the API entry point) will be
  served with a list of links to accessible resources. From there any consumer
  could navigate the API just by following the links.

- **JSON and XML**. Eve responses are automatically rendered as JSON or XML
  depending on the requested ``Accept`` header. Inbound documents (for inserts
  and edits) are in JSON format.
  
- **Last-Modified and ETag (conditional requests)**.Each resource
  representation provides information on the last time it was updated along
  with an hash value computed on the representation itself (``Last-Modified``
  and ``ETag`` response headers). These allow consumers to only retrieve new or
  modified data via the ``If-Modified-Since`` and ``If-None-Match`` request
  headers.

- **Data integrity and concurrency control**. API responses include a ``ETag``
  header, which allows for proper concurrency control. An ``ETag`` is an hash
  value representing the current state of the resource on the server. Consumers
  are not allowed to edit or delete a resource unless they provide an
  up-to-date ``ETag`` for the resource they are attempting to edit.

- **Multiple inserts**. Consumers can send a stream of multiple documents to be
  inserted for a given resource. The response will provide detailed state
  information about each item inserted (creation date, link to the item
  endpoint, primary key/id, etc.). Errors on one documnt won't prevent the
  insertion of other documents in the data stream.

- **Data validation**. Data validation is provided out-of-the-box. Your
  configuration includes a schema definition for every resource managed by the
  API. Data sent to the API for insertion or edition will be validated against
  the schema, and a resource will be updated only if validation is passed. In
  case of multiple inserts the response will provide a success/error state for
  each individual item.
  
- **Extensible data validation**. Data validation is based on the Cerberus
  validation system and therefore it is extensible so you can adapt it to your
  specific use case. Say that your API can only accept odd numbers for
  a certain field values: you can extend the validation class to validate that.
  Or say that you want to make sure that a VAT field actually matches your own
  country VAT algorithm: you can do that too. As a matter of fact, Eve's
  MongoDB data-layer itself is extending Cerberus' standard validation,
  implementing the ``unique`` schema field constraint.

- **Resource-level cache control directives**. You can set global and individual
  cache-control directives for each resource.  Directives will be included in
  API response headers (``Cache-Control``, ``Expires``). This will minimize load on
  the server since cache-enbaled consumers will perform resource-intensive
  request only when really needed.

- **Versioning**. Define a default prefix and/or API version for all your
  endpoints. How about example.com/api/v1/<endpoint>? Both prefix and
  version are as easy to set up as setting a configuration variable.

Installation
------------
Eve is on PyPI so all you need to do is

::

    pip install eve


Testing
-------
Just run

::
    
    python setup.py test

Eve has been tested successfully under Python 2.7 and Python 2.6.

License
-------
Eve is BSD licensed. See the `LICENSE
<https://github.com/nicolaiarocci/eve/blob/master/LICENSE>`_ for details.

Current state
-------------
Consider this a public preview (Alpha). Best way to be notified about its
availability is by starring/following the project repo at GitHub
https://github.com/nicolaiarocci/eve. You can follow me on Twitter at
http://twitter.com/nicolaiarocci.

A little context
----------------
At `Gestionale Amica <http://gestionaleamica.com>`_ we had been working hard on
a full featured, Python powered, RESTful Web API. We learned quite a few things
on REST best patterns, and we got a chance to put Python's renowned web
capabilities under review. Then, at EuroPython 2012, I got a chance to share
what we learned and my talk sparked quite a bit of interest there. A few months
have passed and still the slides are receiving a lot of hits each day, and
I keep receiving emails about source code samples and whatnot. After all,
a REST API lies in the future of every web-oriented developer, and who isn't
these days?

So I thought that perhaps I could take the proprietary, closed code (codenamed
'Adam') and refactor it "just a little bit", so that it could fit a much wider
number of use cases. I could then release it as an open source project. Well
it turned out to be slightly more complex than that but finally here it is, and
of course it's called Eve.

It still got a long way to go before it becomes the fully featured open source,
out-of-the-box API solution I came to envision (see the Roadmap below), but
I feel that at this point the codebase is ready enough for a public preview.
This will hopefully allow for some constructive feedback and maybe, for some
contributors to join the ranks.

PS: the slides of my EuroPython REST API talk are `available online`_. You
might want to check them to understand why and how certain design decisions
were made, especially with regards to REST implementation.

Roadmap
-------
In no particular order, here's a partial list of the features that I plan/would
like to add to Eve, provided that there is enough interest in the project.

- Documentation (coming soon!)
- Granular exception handling
- Journaling/error logging
- Server side caching
- Alternative sort syntax (``?sort=name``)
- Authorization (OAuth2?)
- Support for MySQL and/or other SQL/NoSQL databases

.. _available online: https://speakerdeck.com/u/nicola/p/developing-restful-web-apis-with-python-flask-and-mongodb
