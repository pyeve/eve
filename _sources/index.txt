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

All you need to bring your API online is a database, a configuration file
(defaults to ``settings.py``) and a launch script.  Overall, you will find that
configuring and fine-tuning your API is a very simple process.

.. _demo:

Live demo
---------
Check out the `live demo`_ (if using a browser you will get XML back,
for JSON use ``curl``). The `source code`_ will show you how easy it is to run
an API with Eve. You will also find `usage examples`_ for all common use cases
(GET, POST, PATCH, DELETE and more). There is also a simple `client app`_
available.

User's Guide
------------
.. toctree::
    :maxdepth: 2

    foreword
    features
    install
    quickstart
    config
    validation
    authentication
    contributing
    support
    updates
    license

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

