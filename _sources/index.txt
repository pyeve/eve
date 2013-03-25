RESTful APIs Made Simple
========================

*Eve is an out-of-the-box, highly customizable and fully featured RESTful Web
API framework that you can use to effortlessly build and deploy your own APIs*

Eve is Simple
-------------
.. code-block:: python

    from eve import Eve

    app = Eve()
    app.run()

The API is now live, ready to be consumed:

.. code-block:: console

    $ curl -i http://example.com/people/

    HTTP/1.1 200 OK
    ...

All you need to bring your API online is a database, a configuration file
(defaults to ``settings.py``) and a launch script.  Overall, you will find that
configuring and fine-tuning your API is a very simple process.

Features
--------
- REST compliant
- Full range of CRUD operations (GET, POST, PATCH, DELETE)
- JSON and XML responses
- Customizable data validation 
- Customizable resource endpoints (``/people/``)
- Automatic item endpoints (``/people/<ObjectId>/``)
- Customizable item endpoints (``/people/john/``)
- Pagination (``?page=10``)
- Filtering: Python query syntax (``?where=name=='john doe'``)
- Filtering: MongoDB query syntax (``?where={"name": "john doe"}``)
- Sorting
- Multiple inserts with a single request
- Data integrity and concurrency control
- Resource-level cache control directives
- Conditional requests (``Last-Modified`` and ``ETag`` headers)
- API Versioning
- HATEOAS (Hypermedia as Engine of Application State)
- CORS (Cross-Origin Resource Sharing)
- Powered by Flask_.  

Support for MongoDB comes out of the box; extensions for other SQL/NoSQL
backends can be developed with relative ease (a `PostgreSQL
effort`_ is ongoing, maybe you can lend a hand?)

Live demo
---------
Check out the `live demo`_ (if using a browser you will get XML back,
for JSON use ``curl``). The `source code`_ will show you how easy it is to run
an API with Eve. You will also find `usage examples`_ for all common use cases
(GET, POST, PATCH, DELETE and more). There is also a simple `client app`_
available.

User Guide
----------
.. toctree::
    :maxdepth: 2

    foreword
    installation
    quickstart
    config
    validation
    authorization
    extending
    contributing
    license

.. note::
   This documentation is under development. Please refer to the links on the
   sidebar for more information, or to get in touch with the development team
   (that being me_).

.. _Flask: http://flask.pocoo.org
.. _`PostgreSQL effort`: https://github.com/nicolaiarocci/eve/issues/17
.. _`Eve Demo instructions`: http://github.com/nicolaiarocci/eve-demo#readme
.. _`live demo`: http://eve-demo.herokuapp.com
.. _`source code`: https://github.com/nicolaiarocci/eve-demo
.. _`usage examples`: https://github.com/nicolaiarocci/eve-demo#readme
.. _`client app`: https://github.com/nicolaiarocci/eve-demo-client
.. _me: mailto:me@nicolaiaroccicom

