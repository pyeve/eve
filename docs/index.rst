.. meta::
   :description: Python REST API Framework to effortlessly build and deploy full featured, highly customizable RESTful Web Services.

.. title:: Python REST API Framework: Eve, the Simple Way to REST.

Eve. The Simple Way to REST
===========================

Version |release|.

.. image:: https://img.shields.io/pypi/v/eve.svg?style=flat-square
    :target: https://pypi.org/project/eve

.. image:: https://img.shields.io/travis/pyeve/eve.svg?branch=master&style=flat-square
    :target: https://travis-ci.org/pyeve/eve

.. image:: https://img.shields.io/pypi/pyversions/eve.svg?style=flat-square
    :target: https://pypi.org/project/eve

.. image:: https://img.shields.io/badge/license-BSD-blue.svg?style=flat-square
    :target: https://en.wikipedia.org/wiki/BSD_License

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

-----

Eve is an :doc:`open source <license>` Python REST API framework designed for
human beings. It allows to effortlessly build and deploy highly customizable,
fully featured RESTful Web Services.

Eve is powered by Flask_ and Cerberus_ and it offers native support for
MongoDB_ data stores. Support for SQL, Elasticsearch and Neo4js backends is
provided by community extensions_.

The codebase is thoroughly tested under Python 2.7, 3.5+, and PyPy.

.. note:: The use of **Python 3** is *highly* preferred over Python 2. Consider upgrading your applications and infrastructure if you find yourself *still* using Python 2 in production today.

Eve is Simple
-------------
.. code-block:: python

    from eve import Eve

    settings = {'DOMAIN': {'people': {}}}

    app = Eve(settings=settings)
    app.run()

The API is now live, ready to be consumed:

.. code-block:: console

    $ curl -i http://example.com/people
    HTTP/1.1 200 OK

All you need to bring your API online is a database, a configuration file
(defaults to ``settings.py``) or dictionary, and a launch script. Overall, you
will find that configuring and fine-tuning your API is a very simple process.

Funding Eve
-----------
Eve REST framework is a :doc:`collaboratively funded project <funding>`. If you
run a business and are using Eve in a revenue-generating product, it would make
business sense to sponsor Eve development: it ensures the project that your
product relies on stays healthy and actively maintained. Individual users are
also welcome to make either a recurring pledge or a one time donation if Eve
has helped you in your work or personal projects. Every single sign-up makes
a significant impact towards making Eve possible.

You can support Eve development by pledging on GitHub, Patreon, or PayPal.

- `Become a Backer on GitHub <https://github.com/sponsors/nicolaiarocci>`_
- `Become a Backer on Patreon <https://www.patreon.com/nicolaiarocci>`_
- `Donate via PayPal <https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=7U7G7EWU7EPNW>`_ (one time)

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
    support
    updates
    authors
    license
    changelog

.. note::
   This documentation is under constant development. Please refer to the links
   on the sidebar for more information.


.. _python-eve.org: http://python-eve.org
.. _Postman: https://www.getpostman.com
.. _Flask: http://flask.pocoo.org/
.. _eve-sqlalchemy: https://github.com/RedTurtle/eve-sqlalchemy
.. _MongoDB: https://mongodb.org
.. _Redis: http://redis.io
.. _Cerberus: http://python-cerberus.org
.. _events: https://github.com/pyeve/events
.. _extensions: http://python-eve.org/extensions.html
