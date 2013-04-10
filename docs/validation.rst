.. _validation:

Data Validation
===============
Data validation is provided out-of-the-box. Your configuration includes
a :ref:`schema` for every resource managed by the API. Data sent to the API
for insertion or edition will be validated against the schema, and a resource
will be updated only if validation is passed. 

.. code-block:: console

    $ curl -d 'item1={"firstname": "bill", "lastname": "clinton"}' -d 'item2={"firstname": "mitt", "lastname": "romney"}' http://eve-demo.herokuapp.com/people/
    HTTP/1.0 200 OK

The response will contain a success/error state for each item provided with the
request:

.. code-block:: javascript

      {
        "item2": {
            "status": "ERR",
            "issues": [
                "value 'romney' for field 'lastname' not unique"
            ]
        },
        "item1": {
            "status": "OK",
            "updated": "Thu, 22 Nov 2012 15:29:08 UTC",
            "_id": "50ae44c49fa12500024def5d",
            "_links": {"self": {"href": "eve-demo.herokuapp.com/people/50ae44c49fa12500024def5d/", "title": "person"}}
        }
    }

In the example above, ``item2`` did not validate and was rejected, while
``item1`` was successfully created. API maintainer has complete control on
data validation.

Extending Data Validation
-------------------------
Data validation is based on the Cerberus_ validation system and it is therefore
extensible. As a matter of fact, Eve's MongoDB data-layer itself is extending
Cerberus validation, implementing the ``unique`` and ``data_relation``
constraints and the ``ObjectId`` data type on top of the standard rules.

Custom Validation Rules
------------------------
Suppose that in your specific and very peculiar use case a certain value can
only be expressed as an odd integer. You decide to add support for a new
``isodd`` rule to our validation schema. This is how your would go to implement
that: 

::

    from eve.io.mongo import Validator

    class MyValidator(Validator):
        def _validate_isodd(self, isodd, field, value):
            if isodd and not bool(value & 1):
                self._error("Value for field '%s' must be an odd number" % field)

    app = Eve(validator=MyValidator)

    if __name__ == '__main__':
        app.run()

By subclassing the base Mongo validator class and then adding a custom
``_validate_<rulename>`` method, you extended the available :ref:`schema`
grammar and now the new custom rule ``isodd`` is available in your schema. You
can now do something like:

.. code-block:: javascript

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

::

    def _validate_type_objectid(self, field, value):
        """ Enables validation for `objectid` schema attribute.

        :param unique: Boolean, wether the field value should be
                       unique or not.
        :param field: field name.
        :param value: field value.
        """
        if not re.match('[a-f0-9]{24}', value):
            self._error(ERROR_BAD_TYPE % (field, 'ObjectId'))

This method enables support for MongoDB ``ObjectId`` type in your schema,
allowing something like this:

.. code-block:: javascript

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

