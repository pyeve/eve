.. _quickstart:

Quickstart
==========

Eager to get started?  This page gives a good introduction to Eve.  It
assumes that:

- You already have Eve installed. If you do not, head over to the
  :ref:`install` section.
- MongoDB is `installed <MongoDB install>`_. 
- An instance of MongoDB is `running <mongod>`_.

A Minimal Application
---------------------

A minimal Eve application looks something like this::

    from eve import Eve
    app = Eve()

    if __name__ == '__main__':
        app.run()

Just save it as `run.py`. Next, create a new text file with the following
content:

::

    DOMAIN = {
        'people': {},
    }

Save it as `settings.py` in the same directory where `run.py` is stored. This
is the Eve configuration file, a standard Python module, and it is telling Eve
that your API is comprised of just one accessible resource, `people`.

Now your are ready to launch your API. 

.. code-block:: console

    $ python run.py
     * Running on http://127.0.0.1:5000/

Now let's see:

.. code-block:: console

    $ curl -i http://127.0.0.1:5000/
    HTTP/1.0 200 OK
    Content-Type: application/json
    Content-Length: 82
    Server: Eve/0.0.5-dev Werkzeug/0.8.3 Python/2.7.3
    Date: Wed, 27 Mar 2013 16:06:44 GMT

Congratulations, your GET request got a nice response back. Let's look at the
response payload:

::

    {
        "_links": {
            "child": [{"href": "127.0.0.1:5000/people/", "title": "people"}]
            }
        }

API entry points adhere to the :ref:`hateoas_feature` principle and provide
informations about the resources accessible through the API. In our case
there's only one child resource available, that being `people`.

Try requesting `people` now:

.. code-block:: console

    $ curl http://127.0.0.1:5000/people/

::

    {
        "_items": [], 
        "_links": {
            "self": {"href": "127.0.0.1:5000/people/", "title": "people"}, 
            "parent": {"href": "127.0.0.1:5000", "title": "home"}
            }
        }

Success! This time we also got an ``_items`` list, which is empty since there
are no items available for the resource. 

You might be wondering how can Eve know about `people`, given that you didn't
tell anything about the database. It turns out that's precisely the case. Since
Eve has no clue about the database, it seamlessly serves an empty resource.

Also, keep in mind that by default Eve APIs are read-only. 

.. code-block:: console

    $ curl -X DELETE http://127.0.0.1:5000/people/
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
    <title>405 Method Not Allowed</title>
    <h1>Method Not Allowed</h1>
    <p>The method DELETE is not allowed for the requested URL.</p>

It's time dig a little further.

A More Complex Application
--------------------------
For the next example we're going to use the :ref:`demo`, which is a fully
functional API that you can use to experiment on your own, either on the live
instance or locally (you can use the sample client app to populate and/or reset
the database).

.. note::
    Work in progress.

.. _`MongoDB install`: http://docs.mongodb.org/manual/installation/
.. _mongod: http://docs.mongodb.org/manual/tutorial/manage-mongodb-processes/
