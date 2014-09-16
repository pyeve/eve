.. _validation:

Data Validation
===============
Data validation is provided out-of-the-box. Your configuration includes
a :ref:`schema` for every resource managed by the API. Data sent to the API
to be inserted or updated will be validated against the schema, and a resource
will be updated only if validation passes.

.. code-block:: console

    $ curl -d '{"firstname": "bill", "lastname": "clinton"}, {"firstname": "mitt", "lastname": "romney"}]' -H 'Content-Type: application/json' http://eve-demo.herokuapp.com/people
    HTTP/1.1 201 OK

The response will contain a success/error state for each item provided in the
request:

.. code-block:: javascript

    [
        {
            "_status": "ERR",
            "_issues": {"lastname": "value 'clinton' not unique"}
        },
        {
            "_status": "OK",
            "_updated": "Thu, 22 Nov 2012 15:29:08 GMT",
            "_id": "50ae44c49fa12500024def5d",
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae44c49fa12500024def5d", "title": "person"}}
        }
    ]

In the example above, the first document did not validate and was rejected,
while the second was successfully created. The API maintainer has complete
control of data validation.

.. admonition:: Please Note

    Eventual validation errors on one or more document won't prevent the
    insertion of valid documents. The response status code will be
    ``201 Created`` if *at least one document* passed validation and has
    actually been stored. If no document passed validation the status code will
    be ``200 OK``, meaning that the request was accepted and processed. It is
    still client's responsability to parse the response payload and make sure
    that all documents passed validation.

Extending Data Validation
-------------------------
Data validation is based on the Cerberus_ validation system and it is therefore
extensible. As a matter of fact, Eve's SQLAlchemy data-layer itself extends
Cerberus validation, implementing the ``unique`` and ``data_relation``
constraints.

Custom Validation Rules
------------------------
Suppose that in your specific and very peculiar use case, a certain value can
only be expressed as an odd integer. You decide to add support for a new
``isodd`` rule to our validation schema. This is how you would implement
that:

.. code-block:: python

    from eve.io.sql import ValidatorSQL

    class MyValidator(ValidatorSQL):
        def _validate_isodd(self, isodd, field, value):
            if isodd and not bool(value & 1):
                self._error(field, "Value must be an odd number")

    app = Eve(validator=MyValidator)

    if __name__ == '__main__':
        app.run()

By subclassing the base SQLAlchemy validator class and then adding a custom
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

Custom Data Types
-----------------
You can also add new data types by simply adding ``_validate_type_<typename>``
methods to your subclass. Consider the following snippet from the Eve source
code.

.. code-block:: python

    def _validate_type_objectid(self, field, value):
        """ Enables validation for `objectid` schema attribute.

        :param unique: Boolean, whether the field value should be
                       unique or not.
        :param field: field name.
        :param value: field value.
        """
        if not re.match('[a-f0-9]{24}', value):
            self._error(field, ERROR_BAD_TYPE % 'ObjectId')

This method matches the ``ObjectId`` type in your schema,
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
``data_relation`` constraints. Please see the Cerberus_ documentation for
a complete list rules and data types available. 


.. _Cerberus: http://cerberus.readthedocs.org
.. _`source code`: https://github.com/nicolaiarocci/eve/blob/develop/eve/io/mongo/validation.py
