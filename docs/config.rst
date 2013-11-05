.. _config:

Configuration Handling
======================
Generally Eve configuration is best done with configuration files. The
configuration files themselves are actual Python files. 

Configuration with Files
------------------------
On startup, Eve will look for a `settings.py` file in the application folder.
You can choose an alternative filename/path. Just pass it as an argument when
you instantiate the application.

.. code-block:: python
    
    from eve import Eve

    app = Eve(settings='my_settings.py')
    app.run()

Configuration with a Dictionary
-------------------------------
Alternatively, you can choose to provide a settings dictionary:

.. code-block:: python
    
    my_settings = {
        'MONGO_HOST': 'localhost',
        'MONGO_PORT': 27017,
        'MONGO_DBNAME': 'the_db_name'
        'DOMAIN': {'contacts': {}} 
    }

    from eve import Eve

    app = Eve(settings=my_settings)
    app.run()

Development / Production
------------------------
Most applications need more than one configuration. There should be at least
separate configurations for the production server and the one used during
development. The easiest way to handle this is to use a default configuration
that is always loaded and part of the version control, and a separate
configuration that overrides the values as necessary.

This is the main reason why you can override or extend the settings with the
contents of the file the :envvar:`EVE_SETTINGS` environment variable points to.
The development/local settings could be stored in `settings.py` and then, in
production, you could export EVE_SETTINGS=/path/to/production_setting.py, and
you are done. 

There are many alternative ways to handle development/production
however. Using Python modules for configuration is very convenient, as they
allow for all kinds of nice tricks, like being able to seamlessly launch the
same API on both local and production systems, connecting to the appropriate
database instance as needed.  Consider the following example, taken directly
from the :ref:`demo`:

::

    # We want to seamlessy run our API both locally and on Heroku, so:
    if os.environ.get('PORT'):
        # We're hosted on Heroku! Use the MongoHQ sandbox as our backend.
        MONGO_HOST = 'alex.mongohq.com'
        MONGO_PORT = 10047
        MONGO_USERNAME = '<user>'
        MONGO_PASSWORD = '<pw>'
        MONGO_DBNAME = '<dbname>'

        # also, correctly set the API entry point
        SERVER_NAME = 'eve-demo.herokuapp.com'
    else:
        # Running on local machine. Let's just use the local mongod instance.

        # Please note that MONGO_HOST and MONGO_PORT could very well be left
        # out as they already default to a bare bones local 'mongod' instance.
        MONGO_HOST = 'localhost'
        MONGO_PORT = 27017
        MONGO_USERNAME = 'user'
        MONGO_PASSWORD = 'user'
        MONGO_DBNAME = 'apitest'

        # let's not forget the API entry point
        SERVER_NAME = 'localhost:5000'


.. _global:

Global Configuration
--------------------
Besides defining the general API behaviour, most global configuration settings
are used to define the standard endpoint ruleset, and can be fine-tuned later,
when configuring individual endpoints. Global configuration settings are always
uppercase. 

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

=============================== =========================================
``SERVER_NAME``                 Domain on which the API is being hosted. 
                                Supports subdomains. Defaults to 
                                ``localhost:5000``. 

``URL_PREFIX``                  URL prefix for all API endpoints. Will be used 
                                in conjunction with ``SERVER_NAME`` and 
                                ``API_VERSION`` to construct all API urls 
                                (e.g., ``api`` will be rendered to 
                                ``localhost:5000/api/``).  Defaults to ``''``.

``API_VERSION``                 API version. Will be used in conjunction with 
                                ``SERVER_NAME`` and ``URL_PREFIX`` to construct
                                API urls (e.g., ``v1`` will be rendered to
                                ``localhost:5000/v1/``). Defaults to ``''``.

``ALLOWED_FILTERS``             List of fields on which filtering is allowed. 
                                Can be set to ``[]`` (no filters allowed) or
                                ``['*']`` (filters allowed on every field).
                                Unless your API is comprised of just one
                                endpoint, this global setting should be used as
                                an on/off switch, delegating explicit
                                whitelisting at the local level (see
                                ``allowed_filters`` below). Defaults to
                                ``['*']``.

                                *Please note:* If API scraping or DB DoS
                                attacks are a concern, then globally disabling
                                filters and whitelisting valid ones at the local
                                level is the way to go.

``SORTING``                     ``True`` if sorting is supported for ``GET``
                                requests, otherwise ``False``. Can be overridden
                                by resource settings. Defaults to ``True``.

``PAGINATION``                  ``True`` if pagination is enabled for ``GET`` 
                                requests, otherwise ``False``. Can be overridden
                                by resource settings. Defaults to ``True``.

``PAGINATION_LIMIT``            Maximum value allowed for ``max_results``
                                querydef parameter. Values exceeding the limit
                                will be silently replaced with this value.
                                You want to aim for a reasonable compromise
                                between performance and transfer size. Defaults
                                to 50.

``PAGINATION_DEFAULT``          Default value for ``max_results`` applied when 
                                the parameter is omitted.  Defaults to 25.

``DATE_FORMAT``                 A Python date format used to parse and render 
                                datetime values. When serving requests, 
                                matching JSON strings will be parsed and stored as
                                ``datetime`` values. In responses, ``datetime``
                                values will be rendered as JSON strings using
                                this format. Defaults to the RFC1123 (ex RFC
                                822) standard ``a, %d %b %Y %H:%M:%S GMT`` 
                                ("Tue, 02 Apr 2013 10:29:13 GMT"). 

``RESOURCE_METHODS``            A list of HTTP methods supported at resource 
                                endpoints. Allowed values: ``GET``, ``POST``,
                                ``DELETE``. ``POST`` is used for insertions.
                                ``DELETE`` will delete *all* resource contents
                                (enable with caution). Can be overridden by
                                resource settings. Defaults to ``['GET']``.

``PUBLIC_METHODS``              A list of HTTP methods supported at resource
                                endpoints, open to public access even when
                                :ref:`auth` is enabled. Can be overridden by
                                resource settings. Defaults to ``[]``.

``ITEM_METHODS``                A list of HTTP methods supported at item 
                                endpoints. Allowed values: ``GET``, ``PATCH``
                                and ``DELETE``. ``PATCH`` or, for clients not
                                supporting PATCH, ``POST`` with the
                                ``X-HTTP-Method-Override`` header tag, is used
                                for item updates; ``DELETE`` for item deletion.
                                Can be overridden by resource settings. Defaults
                                to ``['GET']``.  

``PUBLIC_ITEM_METHODS``         A list of HTTP methods supported at item
                                endpoints, left open to public access when when
                                :ref:`auth` is enabled. Can be overridden by
                                resource settings. Defaults to ``[]``.

``ALLOWED_ROLES``               A list of allowed `roles` for resource
                                endpoints. Can be overridden by resource
                                settings. See :ref:`auth` for more
                                information. Defaults to ``[]``.

``ALLOWED_ITEM_ROLES``          A list of allowed `roles` for item endpoints. 
                                See :ref:`auth` for more information. Can be
                                overridden by resource settings.  Defaults to
                                ``[]``.

``CACHE_CONTROL``               Value of the ``Cache-Control`` header field 
                                used when serving ``GET`` requests (e.g., 
                                ``max-age=20,must-revalidate``). Leave empty if
                                you don't want to include cache directives with
                                API responses. Can be overridden by resource
                                settings. Defaults to ``''``.

``CACHE_EXPIRES``               Value (in seconds) of the ``Expires`` header 
                                field used when serving ``GET`` requests. If
                                set to a non-zero value, the header will 
                                always be included, regardless of the setting
                                of ``CACHE_CONTROL``. Can be overridden by
                                resource settings. Defaults to 0.

``X_DOMAINS``                   CORS (Cross-Origin Resource Sharing) support. 
                                Allows API maintainers to specify which domains
                                are allowed to perform CORS requests. Allowed
                                values are: ``None``, a list of domains or '*'
                                for a wide-open API. Defaults to ``None``.

``X_HEADERS``                   CORS (Cross-Origin Resource Sharing) support. 
                                Allows API maintainers to specify which headers
                                are allowed to be sent with CORS requests. Allowed
                                values are: ``None`` or a list of headers names.
                                Defaults to ``None``.
                                

``LAST_UPDATED``                Name of the field used to record a document's 
                                last update date. This field is automatically
                                handled by Eve. Defaults to ``updated``.

``DATE_CREATED``                Name for the field used to record a document
                                creation date. This field is automatically
                                handled by Eve. Defaults to ``created``.

``STATUS_OK``                   Status message returned when data validation is
                                successful. Defaults to `OK`.

``STATUS_ERR``                  Status message returned when data validation
                                failed. Defaults to `ERR`.

``ID_FIELD``                    Name of the field used to uniquely identify
                                resource items within the database. You want
                                this field to be properly indexed on the
                                database.  Defaults to ``_id``. 

``ITEM_LOOKUP``                 ``True`` if item endpoints should be generally 
                                available acroos the API, ``False`` otherwise. 
                                Can be overridden by resource settings. Defaults
                                to ``True``.

``ITEM_LOOKUP_FIELD``           Document field used when looking up a resource
                                item. Can be overridden by resource settings.
                                Defaults to ``ID_FIELD``.

``ITEM_URL``                    RegEx used to construct default item
                                endpoint URLs. Can be overridden by resource
                                settings. Defaults ``[a-f0-9]{24}`` which is
                                MongoDB standard ``Object_Id`` format.

``ITEM_TITLE``                  Title to be used when building item references, 
                                both in XML and JSON responses. Defaults to 
                                resource name, with the plural 's' stripped if
                                present. Can and most likely will be overridden 
                                when configuring single resource endpoints.

``AUTH_FIELD``                  Enables :ref:`user-restricted`. When the
                                feature is enabled, users can only
                                read/update/delete resource items created by
                                themselves. The keyword contains the actual
                                name of the field used to store the id of
                                the user who created the resource item. Can be
                                overridden by resource settings. Defaults to
                                ``None``, which disables the feature. 

``ALLOW_UNKNOWN``               When ``True``, this option will allow insertion
                                of arbitrary, unknown fields to any API
                                endpoint. Use with caution. See :ref:`unknown`
                                for more information. Defaults to ``False``.

``PROJECTION``                  When ``True``, this option enables the
                                :ref:`projections` feature. Can be overridden
                                by resource settings. Defaults to ``True``.

``EMBEDDING``                   When ``True`` this option enables the
                                :ref:`embedded_docs` feature. Defaults to
                                ``True``.

``EXTRA_RESPONSE_FIELDS``       Allows to configure a list of additional
                                document fields that should be provided with
                                every POST response. Normally only
                                automatically handled fields (``ID_FIELD``,
                                ``LAST_UPDATED``, ``DATE_CREATED``, ``etag``)
                                are included in response payloads. Can be
                                overridden by resource settings. Defaults to
                                ``[]``, effectively disabling the feature.

``RATE_LIMIT_GET``              A tuple expressing the rate limit on GET 
                                requests. The first element of the tuple is 
                                the number of requests allowed, while the
                                second is the time window in seconds. For
                                example, ``(300, 60 * 15)`` would set a limit
                                of 300 requests every 15 minutes. Defaults
                                to ``None``.

``RATE_LIMIT_POST``             A tuple expressing the rate limit on POST 
                                requests. The first element of the tuple is 
                                the number of requests allowed, while the
                                second is the time window in seconds. For
                                example ``(300, 60 * 15)`` would set a limit
                                of 300 requests every 15 minutes. Defaults
                                to ``None``. 

``RATE_LIMIT_PATCH``            A tuple expressing the rate limit on PATCH 
                                requests. The first element of the tuple is 
                                the number of requests allowed, while the
                                second is the time window in seconds. For
                                example ``(300, 60 * 15)`` would set a limit
                                of 300 requests every 15 minutes. Defaults
                                to ``None``. 

``RATE_LIMIT_DELETE``           A tuple expressing the rate limit on DELETE 
                                requests. The first element of the tuple is 
                                the number of requests allowed, while the
                                second is the time window in seconds. For
                                example ``(300, 60 * 15)`` would set a limit
                                of 300 requests every 15 minutes. Defaults
                                to ``None``. 

``DEBUG``                       ``True`` to enable Debug Mode, ``False``
                                otherwise. 


``HATEOAS``                     When ``False``, this option disables 
                                :ref:`hateoas_feature`. Defaults to ``True``. 

``MONGO_HOST``                  MongoDB server address. Defaults to ``localhost``.

``MONGO_PORT``                  MongoDB port. Defaults to ``27017``.

``MONGO_USERNAME``              MongoDB user name.

``MONGO_PASSWORD``              MongoDB password.

``MONGO_DBNAME``                MongoDB database name.

``MONGO_QUERY_BLACKLIST``       A list of Mongo query operators that are not
                                allowed to be used in resource filters
                                (``?where=``). Defaults to ``['$where',
                                '$regex']``. 
                                
                                Mongo JavaScript operators are disabled by
                                default, as they might be used as vectors for
                                injection attacks. Javascript queries also tend
                                to be slow and generally can be easily replaced
                                with the (very rich) Mongo query dialect.

``MONGO_WRITE_CONCERN``         A dictionary defining MongoDB write concern
                                settings. All stadard write concern settings 
                                (w, wtimeout, j, fsync) are supported. Defaults
                                to ``{'w': 1}``, which means 'do regular
                                aknowledged writes' (this is also the Mongo
                                default).

                                Please be aware that setting 'w' to a value of
                                2 or greater requires replication to be active
                                or you will be getting 500 errors (the write
                                will still happen; Mongo will just be unable
                                to check that it's being written to multiple
                                servers).
                                
                                Can be overridden at endpoint (Mongo
                                collection) level. See ``mongo_write_concern``
                                below.

``DOMAIN``                      A dict holding the API domain definition.
                                See `Domain Configuration`_.
=============================== =========================================

.. _domain:

Domain Configuration
--------------------
In Eve terminology, a `domain` is the definition of the API structure, the area
where you design your API, fine-tune resources endpoints, and define validation
rules. 

``DOMAIN`` is a :ref:`global configuration setting <global>`: a Python
dictionary where keys are API resources and values their definitions. 

::

    # Here we define two API endpoints, 'people' and 'works', leaving their
    # definitions empty.
    DOMAIN = {
        'people': {},
        'works': {},
        }

In the following two sections, we will customize the `people` resource.

.. _local:

Resource / Item Endpoints
'''''''''''''''''''''''''
Endpoint customization is mostly done by overriding some :ref:`global settings
<global>`, but other unique settings are also available. Resource settings are
always lowercase.

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

=============================== ===============================================
``url``                         The endpoint URL. If omitted the resource key 
                                of the ``DOMAIN`` dict will be used to build
                                the URL. As an example, ``contacts`` would make
                                the `people` resource available at
                                ``/contacts`` (instead of ``/people``). URL can
                                be as complex as needed and can be nested
                                relative to another API endpoint (you can have
                                a ``/contacts`` endpoint and then
                                a ``/contacts/overseas`` endpoint. Both are
                                independent of each other and freely
                                configurable.)

``allowed_filters``             List of fields on which filtering is allowed. 
                                Can be set to ``[]`` (no filters allowed), or
                                ``['*']`` (fields allowed on every field).
                                Defaults to ``['*']``.

                                *Please note:* If API scraping or DB DoS
                                attacks are a concern, then globally disabling
                                filters (see ``ALLOWED_FILTERS`` above) and
                                then whitelisting valid ones at the local level
                                is the way to go.

``sorting``                     ``True`` if sorting is enabled, ``False`` 
                                otherwise. Locally overrides ``SORTING``.
                                
``pagination``                  ``True`` if pagination is enabled, ``False``
                                otherwise. Locally overrides ``PAGINATION``.

``resource_methods``            A list of HTTP methods supported at resource 
                                endpoint. Allowed values: ``GET``, ``POST``,
                                ``DELETE``. Locally overrides
                                ``RESOURCE_METHODS``.

                                *Please note:* if you're running version 0.0.5
                                or earlier use the now unsupported ``methods``
                                keyword instead.

``public_methods``              A list of HTTP methods supported at resource
                                endpoint, open to public access even when
                                :ref:`auth` is enabled. Locally overrides
                                ``PUBLIC_METHODS``.

``item_methods``                A list of HTTP methods supported at item 
                                endpoint. Allowed values: ``GET``, ``PATCH``
                                and ``DELETE``. ``PATCH`` or, for clients not
                                supporting PATCH, ``POST`` with the
                                ``X-HTTP-Method-Override`` header tag.
                                Locally overrides ``ITEM_METHODS``.

``public_item_methods``         A list of HTTP methods supported at item
                                endpoint, left open to public access when
                                :ref:`auth` is enabled. Locally overrides
                                ``PUBLIC_ITEM_METHODS``.

``allowed_roles``               A list of allowed `roles` for resource
                                endpoint. See :ref:`auth` for more
                                information. Locally overrides
                                ``ALLOWED_ROLES``.

``allowed_item_roles``          A list of allowed `roles` for item endpoint. 
                                See :ref:`auth` for more information.
                                Locally overrides ``ALLOWED_ITEM_ROLES``.

``cache_control``               Value of the ``Cache-Control`` header field 
                                used when serving ``GET`` requests. Leave empty
                                if you don't want to include cache directives
                                with API responses. Locally overrides
                                ``CACHE_CONTROL``.

``cache_expires``               Value (in seconds) of the ``Expires`` header 
                                field used when serving ``GET`` requests. If
                                set to a non-zero value, the header will 
                                always be included, regardless of the setting
                                of ``CACHE_CONTROL``. Locally overrides
                                ``CACHE_EXPIRES``.

``item_lookup``                 ``True`` if item endpoint should be available, 
                                ``False`` otherwise. Locally overrides
                                ``ITEM_LOOKUP``.

``item_lookup_field``           Field used when looking up a resource
                                item. Locally overrides ``ITEM_LOOKUP_FIELD``.

``item_url``                    RegEx used to construct item endpoint URL.
                                Locally overrides ``ITEM_URL``.

``item_title``                  Title to be used when building item references, 
                                both in XML and JSON responses. Overrides
                                ``ITEM_TITLE``.

``additional_lookup``           Besides the standard item endpoint which
                                defaults to ``/<resource>/<ID_FIELD_value>``,
                                you can optionally define a secondary,
                                read-only, endpoint like
                                ``/<resource>/<person_name>``. You do so by
                                defining a dictionary comprised of two items
                                `field` and `url`. The former is the name of
                                the field used for the lookup. If the field
                                type (as defined in the resource schema_) is
                                a string, then you put a regex in `url`.  If it
                                is an integer, then you just omit `url`, as it
                                is automatically handled.  See the code snippet
                                below for an usage example of this feature.

``datasource``                  Explicitly links API resources to database 
                                collections. See `Advanced Datasource
                                Patterns`_. 

``auth_field``                  Enables :ref:`user-restricted`. When the
                                feature is enabled, users can only
                                read/update/delete resource items created by
                                themselves. The keyword contains the actual
                                name of the field used to store the id of
                                the user who created the resource item. Locally
                                overrides ``AUTH_FIELD``. 

``allow_unknown``               When ``True``, this option will allow insertion
                                of arbitrary, unknown fields to the endpoint.
                                Use with caution. Locally overrides
                                ``ALLOW_UNKNOWN``. See :ref:`unknown` for more
                                information. Defaults to ``False``.

``projection``                  When ``True``, this option enables the
                                :ref:`projections` feature. Locally overrides
                                ``PROJECTION``. Defaults to ``True``.

``embedding``                   When ``True`` this option enables the
                                :ref:`embedded_docs` feature. Defaults to
                                ``True``.

``extra_response_fields``       Allows to configure a list of additional
                                document fields that should be provided with
                                every POST response. Normally only
                                automatically handled fields (``ID_FIELD``,
                                ``LAST_UPDATED``, ``DATE_CREATED``, ``etag``)
                                are included in response payloads. Overrides
                                ``EXTRA_RESPONSE_FIELDS``. 

``hateoas``                     When ``False``, this option disables
                                :ref:`hateoas_feature` for the resource.
                                Defaults to ``True``. 

``mongo_write_concern``         A dictionary defining MongoDB write concern
                                settings for the endpoint datasource. All
                                stadard write concern settings (w, wtimeout, j,
                                fsync) are supported. Defaults to ``{'w': 1}``
                                which means 'do regular aknowledged writes'
                                (this is also the Mongo default.)

                                Please be aware that setting 'w' to a value of
                                2 or greater requires replication to be active
                                or you will be getting 500 errors (the write
                                will still happen; Mongo will just be unable
                                to check that it's being written to multiple
                                servers.)
                                
``schema``                      A dict defining the actual data structure being
                                handled by the resource. Enables data
                                validation. See `Schema Definition`_.
=============================== ===============================================

Here's an example of resource customization, mostly done by overriding global
API settings:

::

    people = {
        # 'title' tag used in item links. Defaults to the resource title minus
        # the final, plural 's' (works fine in most cases but not for 'people')
        'item_title': 'person',

        # by default, the standard item entry point is defined as
        # '/people/<ObjectId>/'. We leave it untouched, and we also enable an
        # additional read-only entry point. This way consumers can also perform 
        # GET requests at '/people/<lastname>'.
        'additional_lookup': {
            'url': '[\w]+',
            'field': 'lastname'
        },

        # We choose to override global cache-control directives for this resource.
        'cache_control': 'max-age=10,must-revalidate',
        'cache_expires': 10,

        # we only allow GET and POST at this resource endpoint.
        'resource_methods': ['GET', 'POST'],
    }

.. _schema:

Schema Definition
-----------------
Unless your API is read-only, you probably want to define resource `schemas`.
Schemas are important because they enable proper validation for incoming
streams.

::

    # 'people' schema definition
    'schema'= {
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

As you can see, schema keys are the actual field names, while values are dicts
defining the field validation rules. Allowed validation rules are:

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

=============================== ==============================================
``type``                        Field data type. Can be one of the following:
                                ``string``, ``integer``, ``boolean``,
                                ``float``, ``datetime``, ``dict``, ``list``,
                                ``objectid``.

``required``                    If ``True``, the field is mandatory on
                                insertion.

``readonly``                    If ``True``, the field is readonly.

``minlength``, ``maxlength``    Minimum and maximum length allowed for
                                ``string`` and ``list`` types.

``min``, ``max``                Minimum and maximum values allowed for
                                ``integer`` types.

``allowed``                     List of allowed values for ``string`` and 
                                ``list`` types.

``empty``                       Only applies to string fields. If ``False``,
                                validation will fail if the value is empty. 
                                Defaults to ``True``.

``items``                       Defines a list of values allowed in a ``list`` 
                                of fixed length.

``schema``                      Validation schema for ``dict`` types and 
                                arbitrary length ``list`` types. For details 
                                and usage examples, see :ref:`Cerberus documentation <cerberus:schema>`

``unique``                      The value of the field must be unique within
                                the collection.

                                Please note: validation constraints are checked
                                against the database, and not between the
                                payload documents themselves. This causes an
                                interesting corner case: in the event of
                                a multiple documents payload where two or more
                                documents carry the same value for a field
                                where the 'unique' constraint is set, the
                                payload will validate successfully, as there
                                are no duplicates in the database (yet). 
                                
                                If this is an issue, the client can always send
                                the documents one at a time for insertion, or
                                validate locally before submitting the payload
                                to the API.

``data_relation``               Allows to specify a referential integrity rule
                                that the value must satisfy in order to
                                validate. It is a dict with three keys:

                                - ``resource``: the name of the resource being referenced;
                                - ``field``: the field name in the foreign resource;
                                - ``embeddable``: set to ``True`` if clients can request the referenced document to be embedded with the serialization. See :ref:`embedded_docs`. Defaults to ``False``.

``nullable``                    If ``True`` the field value can be set to 
                                ``None``. 

``default``                     The default value for the field. When serving
                                POST (create) requests, missing fields will be
                                assigned the configured default values.
=============================== ==============================================

Schema syntax is based on Cerberus_ and yes, it can be extended.  In fact, Eve
itself extends the original grammar by adding the ``unique`` and
``data_relation`` keywords, along with the ``objectid`` datatype. For more
information on custom validation and usage examples see :ref:`validation`.

In :ref:`local` you customized the `people` endpoint. Then, in this section,
you defined `people` validation rules. Now you are ready to update the domain
which was originally set up in `Domain Configuration`_:

::

    # add the schema to the 'people' resource definition
    people['schema'] = schema
    # update the domain
    DOMAIN['people'] = people

Advanced Datasource Patterns
----------------------------
The ``datasource`` keyword allows you to explicitly link API resources to
database collections (if you omit it, the domain resource key is assumed to be
the name of the database collection itself). It is a dictionary with three allowed
keys: `source`, `filter` and `projection`. ``source`` dictates the database
collection consumed by the resource, ``filter`` expresses the underlying
query used to retrieve and validate data, and ``projection`` allows you to
redefine the exposed fieldset.


Predefined Database Filters
'''''''''''''''''''''''''''
Database filters for the API endpoint are set with the ``filter`` keyword.

::

    people = {
        'datasource': {
            'filter': {'username': {'$exists': True}}
            }
        }
  
In the example above, the API endpoint for the `people` resource will only
expose and update documents with an existing `username` field.

Predefined filters run on top of user queries (GET requests with `where`
clauses) and standard conditional requests (`If-Modified-Since`, etc.)

Please note that datasource filters are applied on GET, PATCH and DELETE
requests. If your resource allows POST requests (document insertions),
then you will probably want to set the validation rules accordingly (in our
example, 'username' should probably be a required field).

Multiple API Endpoints, One Datasource
''''''''''''''''''''''''''''''''''''''
Multiple API endpoints can target the same database collection. For
example you can set both ``/admins`` and ``/users`` to read and write from
the same `people` collection on the database.

::

    people = {
        'datasource': {
            'source': 'people', 
            'filter': {'userlevel': 1}
            }
        }

The above setting will retrieve, edit and delete only documents from the
`people` collection with a `userlevel` of 1.

Limiting the Fieldset Exposed by the API Endpoint
'''''''''''''''''''''''''''''''''''''''''''''''''
By default API responses to GET requests will include all fields defined by the
corresponding resource schema_. The ``projection`` setting of the `datasource`
resource keyword allows you to redefine the fieldset.

::

    people = {
        'datasource': {
            'projection': {'username': 1}
            }
        }

The above setting will expose only the `username` field to GET requests, no
matter the schema_ defined for the resource. Please note that POST and PATCH
methods will still allow the whole schema to be manipulated. This feature can
come in handy when you want to protect insertion and modification behind an
:ref:`auth` scheme while leaving read access open to the public.

.. _Cerberus: http://cerberus.readthedocs.org
