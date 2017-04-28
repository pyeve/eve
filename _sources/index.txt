.. meta::
   :description: Python REST API Framework to effortlessly build and deploy full featured, highly customizable RESTful Web Services.

.. title:: Python REST API Framework: Eve, the Simple Way to REST.

Eve. The Simple Way to REST
===========================

Version |version|.

.. image:: https://img.shields.io/pypi/v/eve.svg?style=flat-square
    :target: https://pypi.org/project/eve

.. image:: https://img.shields.io/travis/pyeve/eve.svg?branch=master&style=flat-square
    :target: https://travis-ci.org/pyeve/eve

.. image:: https://img.shields.io/pypi/pyversions/eve.svg?style=flat-square
    :target: https://pypi.org/project/eve

.. image:: https://img.shields.io/badge/license-BSD-blue.svg?style=flat-square
    :target: https://en.wikipedia.org/wiki/BSD_License

-----

Eve is an :doc:`open source <license>` Python REST API framework designed for
human beings. It allows to effortlessly build and deploy highly customizable,
fully featured RESTful Web Services.

Eve is powered by Flask_ and Cerberus_ and it offers native support for MongoDB_ data
stores. Support for SQL, Elasticsearch and Neo4js backends is provided by
community extensions_. 

The codebase is thoroughly tested under Python 2.6-3.6, and PyPy.

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

Funding Eve
-----------
Eve REST framework is a :doc:`collaboratively funded project <funding>`. If you
run a business and are using Eve in a revenue-generating product, it would make
business sense to sponsor Eve development: it ensures the project that your
product relies on stays healthy and actively maintained. Individual users are
also welcome to make either a recurring pledge or a one time donation if Eve
has helped you in your work or personal projects. Every single sign-up makes
a significant impact towards making Eve possible. 

To join the backer ranks, check out `Eve campaign on Patreon`_.

.. _demo:

Live demo
---------
Check out the `live demo`_. If using a browser you will get XML back. For JSON
in the browser, you might want to install Postman_ or similar extension and
then set the ``Accept`` request header to ``application/json``. If you are
a CLI user (and you should), ``curl`` is your friend. The `source code`_ will
show you how easy it is to run an API with Eve. You will also find `usage
examples`_ for all common use cases (GET, POST, PATCH, DELETE and more). There
is also a simple `client app`_ available.

Development Version
--------------------
If you are on python-eve.org_ then you are looking at the documentation of the
development version. Looking for last release docs? Follow `this
link <http://eve.readthedocs.org/en/stable/>`_.

.. toctree::
    :hidden:

    foreword
    rest_api_for_humans
    install
    quickstart
    features
    config
    validation
    authentication
    funding
    tutorials/index
    snippets/index
    extensions
    contributing
    testing
    support
    updates
    authors
    license
    changelog

.. note::
   This documentation is under constant development. Please refer to the links
   on the sidebar for more information. 


.. _python-eve.org: http://python-eve.org
.. _`Eve Demo instructions`: http://github.com/pyeve/eve-demo#readme
.. _`live demo`: https://eve-demo.herokuapp.com/people
.. _`source code`: https://github.com/pyeve/eve-demo
.. _`usage examples`: https://github.com/pyeve/eve-demo#readme
.. _`client app`: https://github.com/pyeve/eve-demo-client
.. _Postman: https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&cad=rja&ved=0CC0QFjAA&url=https%3A%2F%2Fchrome.google.com%2Fwebstore%2Fdetail%2Fpostman-rest-client%2Ffdmmgilgnpjigdojojpjoooidkmcomcm&ei=dPQ7UpqEBISXtAbPpIGwDg&usg=AFQjCNFL71vN61QG0LKlw7VDJvIZDprjHA&bvm=bv.52434380,d.Yms

.. _Flask: http://flask.pocoo.org/
.. _eve-sqlalchemy: https://github.com/RedTurtle/eve-sqlalchemy
.. _MongoDB: https://mongodb.org
.. _Redis: http://redis.io
.. _Cerberus: http://python-cerberus.org
.. _events: https://github.com/pyeve/events
.. _extensions: http://python-eve.org/extensions
.. _`Eve campaign on Patreon`: https://www.patreon.com/nicolaiarocci
