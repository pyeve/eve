.. meta::
   :description: Python REST API Framework to effortlessly build and deploy full featured, highly customizable RESTful Web Services.

Python REST API Framework
=========================
Eve is an :doc:`open source <license>` Python REST API framework designed for
human beings. It allows to effortlessly build and deploy highly customizable,
fully featured RESTful Web Services.

Eve is powered by Flask_, Redis_, Cerberus_, Events_ and offers support for
both MongoDB_ and SQL backends [*]_.

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

.. [*] SQLALchemy support is provided by the awesome eve-sqlalchemy_ extension.

.. note::
   This documentation is under development. Please refer to the links on the
   sidebar for more information, or to get in touch with the development team
   (that being me_).


.. _python-eve.org: http://python-eve.org
.. _`Eve Demo instructions`: http://github.com/nicolaiarocci/eve-demo#readme
.. _`live demo`: https://eve-demo.herokuapp.com/people
.. _`source code`: https://github.com/nicolaiarocci/eve-demo
.. _`usage examples`: https://github.com/nicolaiarocci/eve-demo#readme
.. _`client app`: https://github.com/nicolaiarocci/eve-demo-client
.. _me: mailto:me@nicolaiarocci.com
.. _Postman: https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&cad=rja&ved=0CC0QFjAA&url=https%3A%2F%2Fchrome.google.com%2Fwebstore%2Fdetail%2Fpostman-rest-client%2Ffdmmgilgnpjigdojojpjoooidkmcomcm&ei=dPQ7UpqEBISXtAbPpIGwDg&usg=AFQjCNFL71vN61QG0LKlw7VDJvIZDprjHA&bvm=bv.52434380,d.Yms

.. _Flask: http://flask.pocoo.org/
.. _eve-sqlalchemy: https://github.com/RedTurtle/eve-sqlalchemy
.. _MongoDB: https://mongodb.org
.. _Redis: http://redis.io
.. _Cerberus: http://python-cerberus.org
.. _events: https://github.com/nicolaiarocci/events
