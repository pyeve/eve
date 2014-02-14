.. meta::
   :description: Python REST API Framework to effortlessly build and deploy full featured, highly customizable RESTful Web Services. Powerd by Flask, MongoDB, Redis and good intentions.  

Python REST API Framework
=========================
*Powered by Flask, MongoDB, Redis and good intentions Eve allows to
effortlessly build and deploy highly customizable, fully featured RESTful Web
Services*

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

Eve is thoroughly tested under Python 2.6, Python 2.7 and Python 3.3.

.. _demo:

Live demo
---------
Check out the `live demo`_. If using a browser you will get XML back. For JSON
in the browser, you might want to install Postman_ or similar extension and
then set the ``Accept`` request header to ``application/json``. If you are
a CLI guy (and you should), ``curl`` is your friend. The `source code`_ will
show you how easy it is to run an API with Eve. You will also find `usage
examples`_ for all common use cases (GET, POST, PATCH, DELETE and more). There
is also a simple `client app`_ available.

User's Guide
------------
.. toctree::
    :maxdepth: 2

    foreword
    install
    quickstart
    features
    config
    validation
    authentication
    tutorials/index
    extensions

Developer's Guide
-----------------
.. toctree::
    :maxdepth: 1

    contributing
    testing

*A proper developer guide will be available when 1.0 is released*

Support, Updates and Licensing
------------------------------
.. toctree::
    :maxdepth: 1

    support
    updates
    authors
    license

Changelog
---------
.. toctree::
    :maxdepth: 2

    changelog

.. note::
   This documentation is under development. Please refer to the links on the
   sidebar for more information, or to get in touch with the development team
   (that being me_).

.. _`Eve Demo instructions`: http://github.com/nicolaiarocci/eve-demo#readme
.. _`live demo`: http://eve-demo.herokuapp.com
.. _`source code`: https://github.com/nicolaiarocci/eve-demo
.. _`usage examples`: https://github.com/nicolaiarocci/eve-demo#readme
.. _`client app`: https://github.com/nicolaiarocci/eve-demo-client
.. _me: mailto:me@nicolaiaroccicom
.. _Postman: https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&cad=rja&ved=0CC0QFjAA&url=https%3A%2F%2Fchrome.google.com%2Fwebstore%2Fdetail%2Fpostman-rest-client%2Ffdmmgilgnpjigdojojpjoooidkmcomcm&ei=dPQ7UpqEBISXtAbPpIGwDg&usg=AFQjCNFL71vN61QG0LKlw7VDJvIZDprjHA&bvm=bv.52434380,d.Yms
