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

However, you might have collections where your unique identifier is not and
``ObjectId``, and you still want individual document endpoints to work
properly. Don't worry, it's doable, it only requires a little tinkering. 

Handling ``UUID`` fields
------------------------
In this tutorial we will consider a scenario in which one of our database
collections (invoices) uses UUID fields as unique identifiers. We want our API to
expose a document endpoint like ``/invoices/uuid``, which translates to something like:

``/invoices/48c00ee9-4dbe-413f-9fc3-d5f12a91de1c``.


These are the steps we need to follow:

1. Craft a custom URL converter that can handle UUID URLs like the one above
2. Craft a custom JSONEncoder that is capable of serializing UUIDs as strings
3. Pass both the url converter and JSONEncoder to our Eve instance
4. Configure our invoices resource so Eve knows it should parse UUID urls with
   the custom url converter. 

Custom URL Converter
~~~~~~~~~~~~~~~~~~~~
Remember, Eve is a Flask_ application which is, in turn, a wrapper around the
magnificent Werkzeug_. This means that the features provided by these awesome
tools are also available in Eve, `custom url converters`_ included. A custom
URL converter is needed in order to allow our API to convert a URL segment into
the corresponding data type (an UUID in our case).

Crafting custom converters is easy. In our case, the only thing we have to do is to
subclass ``BaseConverter`` and pass that new converter to the ``url_map``. A converter
has to provide two public methods: ``to_python`` and ``to_url``, as well as a member
that represents a regular expression. 

Here is our UUID URL converter:

.. code-block:: python

    from werkzeug.routing import BaseConverter
    from uuid import UUID

    class UUIDConverter(BaseConverter):
        """
        UUID converter for the Werkzeug routing system.
        """

        def __init__(self, url_map):
            super(UUIDConverter, self).__init__(url_map)

        def to_python(self, value):
            return UUID(value)

        def to_url(self, value):
            return str(value)

    # you can have multiple custom converters. Each converter has a key,
    # which will be later used to designate endpoint urls, and a specialized
    # BaseConverter subclass. In this case the url converter dictionary has
    # only one item: our UUID converter.
    url_converters = {'uuid': UUIDConverter}

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

 
Passing the ``UUID`` juice to Eve
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Now all the missing pieces are ready, we only need to instruct Eve on how to
use them. Eve needs to already know about the new data type when its building the 
URL map, so we need to pass our custom classes right at the beginning, when we
are instancing the application:

.. code-block:: python

    app = Eve(url_converters=url_converters, json_encoder=UUIDEncoder)

We are almost done!         

Setting up the ``UUID`` endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Now Eve is capable of both parsing UUID link segments and rendering UUID
values, but it still doesn't know which resources are going to use these
features. Let's pick our ``settings.py`` module and update the API domain
accordingly:

.. code-block:: python
   :emphasize-lines: 4

    invoices = {
        'resource_methods': ['GET'],
        'item_methods': ['GET'],
        'item_url': 'uuid',
    }

    DOMAIN = {
        'invoices': invoices
    }

As you may recall, ``uuid`` was the key that we used when we built our url
converters dictionary, the one that we then passed to the Eve instance. Now,
thanks to the ``item_url`` setting, Eve knows that single item URLs for the
invoices endpoint are to be treated with the ``UUIDConverter`` class. 

Our API will now gladly accept UUID link segments for the invoices endpoint;
transparently store UUID strings as UUID values, and render UUID values as
strings. 

Allowing POST operations
~~~~~~~~~~~~~~~~~~~~~~~~
So far the `invoices` endpoint is only allowing read operations. If we wanted
to also enable document edition we would just add ``PATCH``, ``PUT`` and maybe
``DELETE`` to the ``item_methods`` list, but what about document creation? 

By default Eve creates a unique identifier for each newly inserted document,
and that is of ``ObjectId`` type. This is not what we want to happen at this
endpoint. Here we want the client itself to provide the unique identifiers, and
we also want to validate that they are of UUID type. In order to achieve that,
we first need to extend our data validation layer (see :ref:`validation` for details on
custom validation):

.. code-block:: python

    from eve.io.mongo import Validator
    from uuid import UUID

    class UUIDValidator(Validator):
        """
        Extends the base mongo validator adding support for the uuid data-type
        """
        def _validate_type_uuid(self, field, value):
            try:
                UUID(value)
            except ValueError:
                self._error(field, "value '%s' cannot be converted to a UUID" % 
                            value)

So, our complete code snippet will now look like this:

.. code-block:: python

    from eve import Eve
    from eve.io.base import BaseJSONEncoder
    from eve.io.mongo import Validator
    from werkzeug.routing import BaseConverter
    from uuid import UUID

    class UUIDConverter(BaseConverter):
        """
        UUID converter for the Werkzeug routing system.
        """

        def __init__(self, url_map):
            super(UUIDConverter, self).__init__(url_map)

        def to_python(self, value):
            return UUID(value)

        def to_url(self, value):
            return str(value)

    # you can have multiple custom converters. Each converter has a key,
    # which will be later used to designate endpoint urls, and a specialized
    # BaseConverter subclass. In this case the url converter dictionary has
    # only one item: our UUID converter.
    url_converters = {'uuid': UUIDConverter}

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

    class UUIDValidator(Validator):
        """
        Extends the base mongo validator adding support for the uuid data-type
        """
        def _validate_type_uuid(self, field, value):
            try:
                UUID(value)
            except ValueError:
                self._error(field, "value '%s' cannot be converted to a UUID" % 
                            value)

    app = Eve(url_converters=url_converters, json_encoder=UUIDEncoder,
              validator=UUIDValidator)

    if __name__ == '__main__':
        app.run()

We also need to enable edit and insertion methods for the endpoint, and of
course add a resource schema which will be used to validate the document
fields. This is our updated ``settings.py`` script:

.. code-block:: python
   :emphasize-lines: 5-6

    invoices = {
        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'PUT', 'DELETE'],
        'item_url': 'uuid',
        'schema': {
            '_id': {'type': 'uuid'},
        },
    }

    DOMAIN = {
        'invoices': invoices
    }

Now we're also accepting new document, and allowing clients to edit them.

.. _`custom url converters`: http://werkzeug.pocoo.org/docs/routing/#custom-converters
.. _Flask: http://flask.pocoo.org/
.. _Werkzeug: http://werkzeug.pocoo.org/
