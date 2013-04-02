.. _config:

Configuration Handling
======================
Generally Eve configuration is best done with configuration files. The
configuration files themselves are actual Python files. 

Configuration Files
-------------------
On startup Eve will look for a `settings.py` file in the application folder.
You can choose an alternative filename/path, just pass it as an argument when
you instantiate the application.

::
    
    from eve import Eve

    app = Eve(settings='my_settings.py')
    app.run()

Development / Production
''''''''''''''''''''''''
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
however. For an alternative approach see :ref:`dynamic`. 

.. _global:

Global Configuration
--------------------
Besides defining the general API behaviour, most global configuration settings
are used to define the standard endpoint ruleset, and can be fine-tuned
(overrideen) later, when configuring individual endpoints. Global configuration
settings are always in uppercase. 

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

=============================== =========================================
``SERVER_NAME``                 Domain on which the API is being hosted. 
                                Supports subdomains. Defaults to 
                                ``localhost:5000``. 

``URL_PREFIX``                  URL prefix for all API endpoints. Will be used 
                                in conjunction with ``SERVER_NAME`` and 
                                ``API_VERSION`` to construct all API urls 
                                (e.g. ``api`` will be rendered to 
                                ``localhost:5000/api/``).  Defaults to ``''``.

``API_VERSION``                 API version. Will be used in conjunction with 
                                ``SERVER_NAME`` and ``URL_PREFIX`` to construct
                                API urls (e.g. ``v1`` will be rendered to
                                ``localhost:5000/v1/``). Defaults to ``''``.

``FILTERS``                     ``True`` if filters are supported for ``GET`` 
                                requests, ``False`` otherwise. Can be overriden
                                by resource settings. Defaults to ``True``.

``SORTING``                     ``True`` if sorting is supported for ``GET``
                                requests, otherwise ``False``. Can be overriden
                                by resource settings. Defaults to ``True``.

``PAGING``                      ``True`` if pagination is enabled for ``GET`` 
                                requests, otherwise ``False``. Can be overriden
                                by resource settings. Defaults to ``True``.

``PAGING_LIMIT``                Maximum value allowed for ``max_results``
                                querydef parameter. Values exceeding the limit
                                will be silently replaced with this value.
                                You want to aim for a reasonable compromise
                                between performance and transfer size. Defaults
                                to 50.

``PAGING_DEFAULT``              Default value for ``max_results`` applied when 
                                the parameter is omitted.  Defaults to 25.

``DATE_FORMAT``                 A Python date format used to parse and render 
                                datetime values. When serving requests, 
                                matching JSON strings will be parsed and stored as
                                ``datetime`` values. In responses, ``datetime``
                                values will be rendered as JSON strings using
                                this format. Defaults to the RFC1123 (ex RFC
                                822) standard ``a, %d %b %Y %H:%M:%S UTC`` 
                                ("Tue, 02 Apr 2013 10:29:13 UTC"). 

``RESOURCE_METHODS``            A list of HTTP methods supported at resource 
                                endpoints. Allowed values: ``GET``, ``POST``,
                                ``DELETE``. ``POST`` is used for insertions.
                                ``DELETE`` will delete *all* resource contents
                                (enable with caution). Can be overriden by
                                resource settings. Defaults to ``['GET']``.

``PUBLIC_METHODS``              A list of HTTP methods supported at resource
                                endpoints, open to public access even when
                                :ref:`auth` is enabled. Can be overriden by
                                resource settings. Defaults to ``[]``.

``ITEM_METHODS``                A list of HTTP methods supported at item 
                                endpoints. Allowed values: ``GET``, ``PATCH``
                                and ``DELETE``. ``PATCH`` or, for clients not
                                supporting PATCH, ``POST`` with the
                                ``X-HTTP-Method-Override`` header tag, is used
                                for item updates; ``DELETE`` for item deletion.
                                Can be overriden by resource settings. Defaults
                                to ``['GET']``.  

``PUBLIC_ITEM_METHODS``         A list of HTTP methods supported at item
                                endpoints, left open to public access when when
                                :ref:`auth` is enabled. Can be overriden by
                                resource settings. Defaults to ``[]``.

``ALLOWED_ROLES``               A list of allowed `roles` for resource
                                endpoints. Can be overriden by resource
                                settings. See :ref:`auth` for more
                                informations. Defaults to ``[]``.

``ALLOWED_ITEM_ROLES``          A list of allowed `roles` for item endpoints. 
                                See :ref:`auth` for more informations. Can be
                                overriden by resource settings.  Defaults to
                                ``[]``.

``CACHE_CONTROL``               Value of the ``Cache-Control`` header field 
                                used when serving ``GET`` requests (e.g. 
                                ``max-age=20,must-revalidate``). Leave empty if
                                you don't want to include cache directives with
                                API responses. Can be overriden by resource
                                settings. Defaults to ``''``.

``CACHE_EXPIRES``               Value (in seconds) of the ``Expires`` header 
                                field used when serving ``GET`` requests. If
                                set to a non-zero value, the header will 
                                always be included, regardless of the setting
                                of ``CACHE_CONTROL``. Can be overriden by
                                resource settings. Defaults to 0.

``X_DOMAINS``                   CORS (Cross-Origin Resource Sharing) support. 
                                Allows API maintainers to specify which domains
                                are allowed to perform CORS requests. Allowed
                                values are: ``None``, a list of domains or '*'
                                for a wide-open API. Defaults to ``None``.

``LAST_UPDATED``                Name of the field used to record a document's 
                                last update date. This field is automatically
                                handled the Eve. Defaults to ``updated``.

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
                                Can be overriden by resource settings. Defaults
                                to ``True``.

``ITEM_LOOKUP_FIELD``           Document field used when looking up a resource
                                item. Can be overriden by resource settings.
                                Defaults to ``ID_FIELD``.

``ITEM_URL``                    RegEx used to construct default item
                                endpoint URLs. Can be overriden by resource
                                settings. Defaults ``[a-f0-9]{24}`` which is
                                MongoDB standard ``Object_Id`` format.

``ITEM_TITLE``                  Title to be used when building item references, 
                                both in XML and JSON responses. Defaults to 
                                resource name, with the plural 's' stripped if
                                present. Can and most likely will be overriden 
                                when configuring single resource endpoints.

``DEBUG``                       ``True`` to enable Debug Mode, ``False``
                                otherwise. 

``DOMAIN``                      A dict holding the whole API domain definition.
                                See `Domain Configuration`_ below.
=============================== =========================================

Domain Configuration
--------------------
In Eve terminology, the `domain` is the definition of the proper API structure.
``DOMAIN`` itself is :ref:`global configuration setting <global>`, a Python
dictionary where keys are API resources, and values express the corresponding
definitions. This is where you fine-tune resource and item endpoints, and
define your data validation ruleset.

.. note:: Work in progress.

.. _dynamic:

Dynamic Configuration Loading
-----------------------------
Using Python modules for configuration is very convenient, as they allow for
all kind of nice tricks, like being able to seamlessly launch the same API on
both local and production systems, connecting to the appropriate database
instance as needed.  Consider the following example, taken directly from the
:ref:`demo`:

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
        MONGO_HOST = 'localhost'
        MONGO_PORT = 27017
        MONGO_USERNAME = 'user'
        MONGO_PASSWORD = 'user'
        MONGO_DBNAME = 'apitest'

        # let's not forget the API entry point
        SERVER_NAME = 'localhost:5000'

.. note:: Work in progress.
