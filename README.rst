Eve
====
.. image:: https://img.shields.io/pypi/v/eve.svg?style=flat-square
    :target: https://pypi.org/project/eve

.. image:: https://github.com/pyeve/eve/workflows/CI/badge.svg
  :target: https://github.com/pyeve/eve/actions?query=workflow%3ACI

.. image:: https://img.shields.io/pypi/pyversions/eve.svg?style=flat-square
    :target: https://pypi.org/project/eve

.. image:: https://img.shields.io/badge/license-BSD-blue.svg?style=flat-square
    :target: https://en.wikipedia.org/wiki/BSD_License

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

Eve is an open source Python REST API framework designed for human beings. It
allows to effortlessly build and deploy highly customizable, fully featured
RESTful Web Services. Eve offers native support for MongoDB, and SQL backends
via community extensions.

Eve is Simple
-------------
.. code-block:: python

    from eve import Eve

    app = Eve()
    app.run()

The API is now live, ready to be consumed:

.. code-block:: console

    $ curl -i http://example.com/people
    HTTP/1.1 200 OK

All you need to bring your API online is a database, a configuration file
(defaults to ``settings.py``) and a launch script.  Overall, you will find that
configuring and fine-tuning your API is a very simple process.

`Check out the Eve Website <http://python-eve.org/>`_

Features
--------
* Emphasis on REST
* Full range of CRUD operations
* Customizable resource endpoints
* Customizable, multiple item endpoints
* Filtering and Sorting
* Pagination
* HATEOAS
* JSON and XML Rendering
* Conditional Requests
* Data Integrity and Concurrency Control
* Bulk Inserts
* Data Validation
* Extensible Data Validation
* Resource-level Cache Control
* API Versioning
* Document Versioning
* Authentication
* CORS Cross-Origin Resource Sharing
* JSONP
* Read-only by default
* Default Values
* Predefined Database Filters
* Projections
* Embedded Resource Serialization
* Event Hooks
* Rate Limiting
* Custom ID Fields
* File Storage
* GeoJSON
* Internal Resources
* Enhanced Logging
* Operations Log
* MongoDB Aggregation Framework
* MongoDB and SQL Support
* Powered by Flask

Error Handling
--------------
Good error messages are a feature. Eve comes with sensible defaults, but you can
customize error responses to fit your specific needs. Since Eve is powered by
Flask, you can use Flask's standard error handling mechanisms.

For example, here's how you can customize the response for a ``404 Not Found``
error:

.. code-block:: python

    from eve import Eve
    from eve.render import send_error

    app = Eve()

    @app.errorhandler(404)
    def not_found(e):
        # You can customize the message and code.
        # send_error will render a response in the right