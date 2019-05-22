.. _quickstart:

Quickstart
==========

Eager to get started?  This page gives a first introduction to Eve.

Prerequisites
-------------
- You already have Eve installed. If you do not, head over to the
  :ref:`install` section.
- MongoDB is installed_.
- An instance of MongoDB is running_.

A Minimal Application
---------------------

A minimal Eve application looks something like this::

    from eve import Eve
    app = Eve()

    if __name__ == '__main__':
        app.run()

Just save it as run.py. Next, create a new text file with the following
content:

::

    DOMAIN = {'people': {}}

Save it as settings.py in the same directory where run.py is stored. This
is the Eve configuration file, a standard Python module, and it is telling Eve
that your API is comprised of just one accessible resource, ``people``.

Now your are ready to launch your API.

.. code-block:: console

    $ python run.py
     * Running on http://127.0.0.1:5000/

Now you can consume the API:

.. code-block:: console

    $ curl -i http://127.0.0.1:5000
    HTTP/1.0 200 OK
    Content-Type: application/json
    Content-Length: 82
    Server: Eve/0.0.5-dev Werkzeug/0.8.3 Python/2.7.3
    Date: Wed, 27 Mar 2013 16:06:44 GMT

Congratulations, your GET request got a nice response back. Let's look at the
payload:

::

    {
      "_links": {
        "child": [
          {
            "href": "people",
            "title": "people"
          }
        ]
      }
    }

API entry points adhere to the :ref:`hateoas_feature` principle and provide
information about the resources accessible through the API. In our case
there's only one child resource available, that being ``people``.

Try requesting ``people`` now:

.. code-block:: console

    $ curl http://127.0.0.1:5000/people

::

    {
      "_items": [],
      "_links": {
        "self": {
          "href": "people",
          "title": "people"
        },
        "parent": {
          "href": "/",
          "title": "home"
        }
      }
    }

This time we also got an ``_items`` list. The ``_links`` are relative to the
resource being accessed, so you get a link to the parent resource (the home
page) and to the resource itself. If you got a timeout error from pymongo, make
sure the prerequistes are met. Chances are that the ``mongod`` server process
is not running.

By default Eve APIs are read-only:

.. code-block:: console

    $ curl -X DELETE http://127.0.0.1:5000/people
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
    <title>405 Method Not Allowed</title>
    <h1>Method Not Allowed</h1>
    <p>The method DELETE is not allowed for the requested URL.</p>

Since we didn't provide any database detail in settings.py, Eve has no clue
about the real content of the ``people`` collection (it might even be
non-existent) and seamlessly serves an empty resource, as we don't want to let
API users down.

Database Interlude
------------------
Let's connect to a database by adding the following lines to settings.py:

::

    # Let's just use the local mongod instance. Edit as needed.

    # Please note that MONGO_HOST and MONGO_PORT could very well be left
    # out as they already default to a bare bones local 'mongod' instance.
    MONGO_HOST = 'localhost'
    MONGO_PORT = 27017

    # Skip this block if your db has no auth. But it really should.
    MONGO_USERNAME = '<your username>'
    MONGO_PASSWORD = '<your password>'
    # Name of the database on which the user can be authenticated,
    # needed if --auth mode is enabled.
    MONGO_AUTH_SOURCE = '<dbname>'

    MONGO_DBNAME = 'apitest'

Due to MongoDB *laziness*, we don't really need to create the database
collections. Actually we don't even need to create the database: GET requests
on an empty/non-existent DB will be served correctly (``200 OK`` with an empty
collection); DELETE/PATCH/PUT will receive appropriate responses (``404 Not
Found`` ), and POST requests will create database and collections as needed.
However, such an auto-managed database will perform very poorly since it lacks
indexes and any sort of optimization.

A More Complex Application
--------------------------
So far our API has been read-only. Let's enable the full spectrum of CRUD
operations:

::

    # Enable reads (GET), inserts (POST) and DELETE for resources/collections
    # (if you omit this line, the API will default to ['GET'] and provide
    # read-only access to the endpoint).
    RESOURCE_METHODS = ['GET', 'POST', 'DELETE']

    # Enable reads (GET), edits (PATCH), replacements (PUT) and deletes of
    # individual items  (defaults to read-only item access).
    ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']

``RESOURCE_METHODS`` lists methods allowed at resource endpoints (``/people``)
while ``ITEM_METHODS`` lists the methods enabled at item endpoints
(``/people/<ObjectId>``). Both settings have a global scope and will apply to
all endpoints.  You can then enable or disable HTTP methods at individual
endpoint level, as we will soon see.

Since we are enabling editing we also want to enable proper data validation.
Let's define a schema for our ``people`` resource.

::

    schema = {
        # Schema definition, based on Cerberus grammar. Check the Cerberus project
        # (https://github.com/pyeve/cerberus) for details.
        'firstname': {
            'type': 'string',
            'minlength': 1,
            'maxlength': 10,
        },
        'lastname': {
            'type': 'string',
            'minlength': 1,
            'maxlength': 15,
            'required': True,
            # talk about hard constraints! For the purpose of the demo
            # 'lastname' is an API entry-point, so we need it to be unique.
            'unique': True,
        },
        # 'role' is a list, and can only contain values from 'allowed'.
        'role': {
            'type': 'list',
            'allowed': ["author", "contributor", "copy"],
        },
        # An embedded 'strongly-typed' dictionary.
        'location': {
            'type': 'dict',
            'schema': {
                'address': {'type': 'string'},
                'city': {'type': 'string'}
            },
        },
        'born': {
            'type': 'datetime',
        },
    }

For more information on validation see :ref:`validation`.

Now let's say that we want to further customize the ``people`` endpoint. We want
to:

- set the item title to ``person``
- add an extra :ref:`custom item endpoint <custom_item_endpoints>` at ``/people/<lastname>``
- override the default :ref:`cache control directives <cache_control>`
- disable DELETE for the ``/people`` endpoint (we enabled it globally)

Here is how the complete ``people`` definition looks in our updated settings.py
file:

::

    people = {
        # 'title' tag used in item links. Defaults to the resource title minus
        # the final, plural 's' (works fine in most cases but not for 'people')
        'item_title': 'person',

        # by default the standard item entry point is defined as
        # '/people/<ObjectId>'. We leave it untouched, and we also enable an
        # additional read-only entry point. This way consumers can also perform
        # GET requests at '/people/<lastname>'.
        'additional_lookup': {
            'url': 'regex("[\w]+")',
            'field': 'lastname'
        },

        # We choose to override global cache-control directives for this resource.
        'cache_control': 'max-age=10,must-revalidate',
        'cache_expires': 10,

        # most global settings can be overridden at resource level
        'resource_methods': ['GET', 'POST'],

        'schema': schema
    }

Finally we update our domain definition:

::

    DOMAIN = {
        'people': people,
    }

Save settings.py and launch run.py. We can now insert documents at the
``people`` endpoint:

.. code-block:: console

    $ curl -d '[{"firstname": "barack", "lastname": "obama"}, {"firstname": "mitt", "lastname": "romney"}]' -H 'Content-Type: application/json'  http://127.0.0.1:5000/people
    HTTP/1.0 201 OK

We can also update and delete items (but not the whole resource since we
disabled that). We can also perform GET requests against the new ``lastname``
endpoint:

.. code-block:: console

    $ curl -i http://127.0.0.1:5000/people/obama
    HTTP/1.0 200 OK
    Etag: 28995829ee85d69c4c18d597a0f68ae606a266cc
    Last-Modified: Wed, 21 Nov 2012 16:04:56 GMT
    Cache-Control: 'max-age=10,must-revalidate'
    Expires: 10
    ...

.. code-block:: javascript

    {
        "firstname": "barack",
        "lastname": "obama",
        "_id": "50acfba938345b0978fccad7"
        "updated": "Wed, 21 Nov 2012 16:04:56 GMT",
        "created": "Wed, 21 Nov 2012 16:04:56 GMT",
        "_links": {
            "self": {"href": "people/50acfba938345b0978fccad7", "title": "person"},
            "parent": {"href": "/", "title": "home"},
            "collection": {"href": "people", "title": "people"}
        }
    }

Cache directives and item title match our new settings. See :doc:`features` for
a complete list of features available and more usage examples.

.. note::
    All examples and code snippets are from the :ref:`demo`, which is a fully
    functional API that you can use to experiment on your own, either on the
    live instance or locally (you can use the sample client app to populate
    and/or reset the database).

.. _`installed`: http://docs.mongodb.org/manual/installation/
.. _running: http://docs.mongodb.org/manual/tutorial/manage-mongodb-processes/
