Eve
====
.. image:: https://secure.travis-ci.org/nicolaiarocci/eve.png?branch=master 
        :target: https://secure.travis-ci.org/nicolaiarocci/eve

Eve is an open source Python REST API framework designed for human beings. It
allows to effortlessly build and deploy highly customizable, fully featured
RESTful Web Services.

Eve is powered by Flask, Redis, Cerberus, Events and offers support for both
MongoDB and SQL backends.

The codebase is thoroughly tested under Python 2.6, 2.7, 3.3, 3.4 and PyPy.

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
* MongoDB and SQL Support
* Powered by Flask


License
-------
Eve is a `Nicola Iarocci`_ and `Gestionali Amica`_ open source project,
distributed under the `BSD license
<https://github.com/nicolaiarocci/eve/blob/master/LICENSE>`_. 

.. _`Nicola Iarocci`: http://nicolaiarocci.com
.. _`Gestionali Amica`: http://gestionaleamica.com
