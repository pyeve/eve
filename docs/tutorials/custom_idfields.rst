.. _custom_ids:

Handling custom ID fields
=========================

When it comes to individual document endpoints, in most cases you don't have
anything to do besides defining the parent resource endpoint. So let's say that
you configure a ``/invoices`` endpoint, which will allow clients to query the
underlying `invoices` database collection. The ``/invoices/<ObjectId>``
endpoint will be made available by the framework, and will be used by clients to
retrieve and/or edit individual documents. By default, Eve provides this feature
seamlessly when ``ID_FIELD`` fields are of ``ObjectId`` type.

However, you might have collections where your unique identifier is not an
``ObjectId``, and you still want individual document endpoints to work
properly. Don't worry, it's doable, it only requires a little tinkering.

Handling ``UUID`` fields
------------------------
In this tutorial we will consider a scenario in which one of our database
collections (invoices) uses UUID fields as unique identifiers. We want our API to
expose a document endpoint like ``/invoices/uuid``, which translates to something like:

``/invoices/48c00ee9-4dbe-413f-9fc3-d5f12a91de1c``.

These are the steps we need to follow:

1. Craft a custom JSONEncoder that is capable of serializing UUIDs as strings
   and pass it to our Eve application.
2. Add support for a new ``uuid`` data type so we can properly validate
   incoming uuid values.
3. Configure our invoices endpoint so Eve knows how to properly parse UUID
   urls.

Custom JSONEncoder
~~~~~~~~~~~~~~~~~~
The Eve default JSON serializer is perfectly capable of serializing common data
types like ``datetime`` (serialized to a RFC1123 string, like ``Sat, 23 Feb 1985
12:00:00 GMT``) and ``ObjectId`` values (also serialized to strings).

Since we are adding support for an unknown data type, we also need to instruct
our Eve instance on how to properly serialize it. This is as easy as
subclassing a standard ``JSONEncoder`` or, even better, Eve's own
``BaseJSONEncoder``, so our custom serializer will preserve all of Eve's
serialization magic:

.. code-block:: python

    from eve.io.base import BaseJSONEncoder
    from uuid import UUID

    class UUIDEncoder(BaseJSONEncoder):
        """ JSONEconder subclass used by the json render function.
        This is different from BaseJSONEoncoder since it also addresses
        encoding of UUID
        """

        def default(self, obj):
            if isinstance(obj, UUID):
                return str(obj)
            else:
                # delegate rendering to base class method (the base class
                # will properly render ObjectIds, datetimes, etc.)
                return super(UUIDEncoder, self).default(obj)


``UUID`` Validation
~~~~~~~~~~~~~~~~~~~
By default Eve creates a unique identifier for each newly inserted document,
and that is of ``ObjectId`` type. This is not what we want to happen at this
endpoint. Here we want the client itself to provide the unique identifiers, and
we also want to validate that they are of UUID type. In order to achieve that,
we first need to extend our data validation layer (see :ref:`validation` for
details on custom validation):

.. code-block:: python

    from eve.io.mongo import Validator
    from uuid import UUID

    class UUIDValidator(Validator):
        """
        Extends the base mongo validator adding support for the uuid data-type
        """
        def _validate_type_uuid(self, value):
            try:
                UUID(value)
            except ValueError:
                pass

``UUID`` URLs
~~~~~~~~~~~~~
Now Eve is capable of rendering and validating UUID values but it still doesn't know
which resources are going to use these features. We also need to set
``item_url`` so uuid formed urls can be properly parsed. Let's pick our
``settings.py`` module and update the API domain accordingly:

.. code-block:: python

    invoices = {
        # this resource item endpoint (/invoices/<id>) will match a UUID regex.
        'item_url': 'regex("[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}")',
        'schema': {
            # set our _id field of our custom uuid type.
            '_id': {'type': 'uuid'},
        },
    }

    DOMAIN = {
        'invoices': invoices
    }

If all your API resources are going to support uuid as unique document
identifiers then you might just want to set the global ``ITEM_URL`` to the uuid
regex in order to avoid setting it for every single resource endpoint.

Passing the ``UUID`` juice to Eve
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Now all the missing pieces are there we only need to instruct Eve on how to
use them. Eve needs to know about the new data type when its building the
URL map, so we need to pass our custom classes right at the beginning, when we
are instancing the application:

.. code-block:: python

    app = Eve(json_encoder=UUIDEncoder, validator=UUIDValidator)


Remember, if you are using custom ``ID_FIELD`` values then you should not rely
on MongoDB (and Eve) to auto-generate the ``ID_FIELD`` for you. You are
supposed to pass the value, like so:

::

    POST
    {"name":"bill", "_id":"48c00ee9-4dbe-413f-9fc3-d5f12a91de1c"}

.. _`custom url converters`: http://werkzeug.pocoo.org/docs/routing/#custom-converters
.. _Flask: http://flask.pocoo.org/
.. _Werkzeug: http://werkzeug.pocoo.org/
