.. _sqlalchemy_support:

SQLAlchemy support
==================

This tutorial will show how to use Eve with the `SQLAlchemy`_ support. Using 
`SQLAlchemy`_ instead MongoDB means that you can re-use your existing SQL data
model and expose it via REST thanks to Eve with no hassle. The example app used
by this tutorial is available at ``examples/SQL/`` inside Eve repository.


Schema registration
-------------------
The main goal of the `SQLAlchemy`_ integration in Eve is to separate dependencies
and keep model registration depend only on sqlalchemy library. This means that
you can simply use something like that:

.. literalinclude:: ../../examples/SQL/tables.py
   :lines: 6-19,46-53,59-

We have used ``CommonColumns`` abstract class to provide attributes used by Eve,
such us ``_created`` and ``_updated``, but you are not forced to used them:

.. literalinclude:: ../../examples/SQL/tables.py
   :lines: 22-26


Eve settings
------------
All standard Eve settings will work with `SQLAlchemy`_ support. However, you need
manually decide which `SQLAlchemy`_ declarative classes you wish to register.
You can do it using ``registerSchema``:

.. literalinclude:: ../../examples/SQL/settings.py
   :lines: 9-13, 25-29

As you noticed the schema will be stored inside `_eve_schema` class attribute
so it can be easily used. You can of course extend the autogenerate schema
with your custom options:

.. literalinclude:: ../../examples/SQL/settings.py
   :lines: 31-


Start Eve
---------
That's almost everything. Before you can start Eve you need to bind SQLAlchemy
from the Eve data driver:

.. literalinclude:: ../../examples/SQL/sqla_example.py
   :lines: 1-11

Now you can run Eve:

.. code-block:: python

   app.run(debug=True)

and start it:

.. code-block:: console

    $ python sqla_example.py
     * Running on http://127.0.0.1:5000/

and check that everything is working like expected, by trying requesting `people`:

.. code-block:: console

    $ curl http://127.0.0.1:5000/people/1

::

    {
        "id": 1,
        "fullname": "George Washington",
        "firstname": "George",
        "lastname": "Washington",
        "_etag": "31a6c47afe9feb118b80a5f0004dd04ee2ae7442",
        "_created": "Thu, 21 Aug 2014 11:18:24 GMT",
        "_updated": "Thu, 21 Aug 2014 11:18:24 GMT",
        "_links": {
            "self": {
                "href":"/people/1",
                "title":"person"
            },
            "parent": {
                "href": "",
                "title": "home"
            },
            "collection": {
                "href": "/people",
                "title": "people"
            }
        },
    }

SQLAlchemy expressions
----------------------
With this version of Eve you can use `SQLAlchemy`_ expressions such as: `like`,
`in_`, etc. For more examples please check `SQLAlchemy internals`_.

Using those expresssion is straightforward (you can use them only with dictionary
where filter):

.. code-block:: console

    http://127.0.0.1:5000/people?where={"lastname":"like(\"Smi%\")"}

which produces where closure:

.. code-block:: sql

   people.lastname LIKE "Smi%"

Another examples using `in_`:

.. code-block:: console

    http://127.0.0.1:5000/people?where={"firstname":"in_([\"John\",\"Fred\"])"}

which produces where closure:

.. code-block:: sql

   people.firstname IN ("John", "Fred")


.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _SQLAlchemy internals: http://docs.sqlalchemy.org/en/latest/orm/internals.html
