.. _validation:

Data Validation
===============
Data validation is provided out-of-the-box. Your configuration includes
a schema definition for every resource managed by the API. Data sent to the API
to be inserted/updated will be validated against the schema, and a resource
will only be updated if validation passes.

.. code-block:: console

    $ curl -d '[{"firstname": "bill", "lastname": "clinton"}, {"firstname": "mitt", "lastname": "romney"}]' -H 'Content-Type: application/json' http://myapi/people
    HTTP/1.1 201 OK

The response will contain a success/error state for each item provided in the
request:

.. code-block:: javascript

    {
        "_status": "ERR",
        "_error": "Some documents contains errors",
        "_items": [
            {
                "_status": "ERR",
                "_issues": {"lastname": "value 'clinton' not unique"}
            },
            {
                "_status": "OK",
            }
        ]
    ]

In the example above, the first document did not validate so the whole request
has been rejected.

When all documents pass validation and are inserted correctly the response
status is ``201 Created``. If any document fails validation the response status
is ``422 Unprocessable Entity``, or any other error code defined by
``VALIDATION_ERROR_STATUS`` configuration.

For information on how to define documents schema and standard validation
rules, see :ref:`schema`.

Extending Data Validation
-------------------------
Data validation is based on the Cerberus_ validation system and it is therefore
extensible. As a matter of fact, Eve's MongoDB data-layer itself extends
Cerberus validation, implementing the ``unique`` and ``data_relation``
constraints, the ``ObjectId`` data type and the ``decimal128`` on top of
the standard rules.

.. _custom_validation_rules:

Custom Validation Rules
------------------------
Suppose that in your specific and very peculiar use case, a certain value can
only be expressed as an odd integer. You decide to add support for a new
``isodd`` rule to our validation schema. This is how you would implement
that:

.. code-block:: python

    from eve.io.mongo import Validator

    class MyValidator(Validator):
        def _validate_isodd(self, isodd, field, value):
            if isodd and not bool(value & 1):
                self._error(field, "Value must be an odd number")

    app = Eve(validator=MyValidator)

    if __name__ == '__main__':
        app.run()

By subclassing the base Mongo validator class and then adding a custom
``_validate_<rulename>`` method, you extended the available :ref:`schema`
grammar and now the new custom rule ``isodd`` is available in your schema. You
can now do something like:

.. code-block:: python

    'schema': {
        'oddity': {
            'isodd': True,
            'type': 'integer'
          }
    }

Cerberus and Eve also offer `function-based validation`_ and `type coercion`_,
lightweight alternatives to class-based custom validation.

Custom Data Types
-----------------
You can also add new data types by simply adding ``_validate_type_<typename>``
methods to your subclass. Consider the following snippet from the Eve source
code.

.. code-block:: python

    def _validate_type_objectid(self, value):
        """ Enables validation for `objectid` schema attribute.

        :param value: field value.
        """
        if isinstance(value, ObjectId):
            return True

This method enables support for MongoDB ``ObjectId`` type in your schema,
allowing something like this:

.. code-block:: python

    'schema': {
        'owner': {
            'type': 'objectid',
            'required': True,
        },
    }

You can also check the `source code`_ for Eve custom validation, where you will
find more advanced use cases, such as the implementation of the ``unique`` and
``data_relation`` constraints.

For more information on

.. note::

    We have only scratched the surface of data validation. Please make sure
    to check the Cerberus_ documentation for a complete list of available
    validation rules and data types.

    Also note that Cerberus requirement is pinned to version 0.9.2, which still
    supports the ``validate_update`` method used for ``PATCH`` requests.
    Upgrade to Cerberus 1.0+ is scheduled for Eve version 0.8.

.. _unknown:

Allowing the Unknown
--------------------
Normally you don't want clients to inject unknown fields in your documents.
However, there might be circumstances where this is desirable. During the
development cycle, for example, or when you are dealing with very heterogeneous
data. After all, not forcing normalized information is one of the selling
points of MongoDB and many other NoSQL data stores.

In Eve, you achieve this by setting the ``ALLOW_UNKNOWN`` option to ``True``.
Once this option is enabled, fields matching the schema will be validated
normally, while unknown fields will be quietly stored without a glitch. You
can also enable this feature only for certain endpoints by setting the
``allow_unknown`` local option.

Consider the following domain:

.. code-block:: python

    DOMAIN: {
        'people': {
            'allow_unknown': True,
            'schema': {
                'firstname': {'type': 'string'},
                }
            }
        }

Normally you can only add (POST) or edit (PATCH) `firstnames` to the
``/people`` endpoint. However, since ``allow_unknown`` has been enabled, even
a payload like this will be accepted:

.. code-block:: console

    $ curl -d '[{"firstname": "bill", "lastname": "clinton"}, {"firstname": "bill", "age":70}]' -H 'Content-Type: application/json' http://myapi/people
    HTTP/1.1 201 OK

.. admonition:: Please note

    Use this feature with extreme caution. Also be aware that, when this
    option is enabled, clients will be capable of actually `adding` fields via
    PATCH (edit).

``ALLOW_UNKNOWN`` is also useful for read-only APIs or endpoints that
need to return the whole document, as found in the underlying database. In this
scenario you don't want to bother with validation schemas. For the whole API
just set ``ALLOW_UNKNOWN`` to ``True``, then ``schema: {}`` at every endpoint.
For a single endpoint, use ``allow_unknown: True`` instead.

.. _schema_validation:

Schema validation
-----------------

By default, schemas are validated to ensure they conform to the structure
documented in :ref:`schema`.

In order to deal with non-conforming schemas, add
:ref:`custom_validation_rules` for non-conforming keys used in the schema.

.. _Cerberus: http://python-cerberus.org
.. _`source code`: https://github.com/pyeve/eve/blob/master/eve/io/mongo/validation.py
.. _`function-based validation`: http://docs.python-cerberus.org/en/latest/customize.html#function-validator
.. _`type coercion`: http://docs.python-cerberus.org/en/latest/usage.html#type-coercion
