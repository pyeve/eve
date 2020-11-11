.. _config:

Configuration
=============
Generally Eve configuration is best done with configuration files. The
configuration files themselves are actual Python files. However, Eve will
give precedence to dictionary-based settings first, then it will try to
locate a file passed in :envvar:`EVE_SETTINGS` environmental variable (if
set) and finally it will try to locate `settings.py` or a file with filename
passed to `settings` flag in constructor.

Configuration With Files
------------------------
On startup, if `settings` flag is omitted in constructor, Eve will try to locate
file named `settings.py`, first in the application folder and then in one of the
application's subfolders. You can choose an alternative filename/path, just pass
it as an argument when you instantiate the application. If the file path is
relative, Eve will try to locate it recursively in one of the folders in your
`sys.path`, therefore you have to be sure that your application root is appended
to it. This is useful, for example, in testing environments, when settings file
is not necessarily located in the root of your application.

.. code-block:: python

    from eve import Eve

    app = Eve(settings='my_settings.py')
    app.run()

Configuration With a Dictionary
-------------------------------
Alternatively, you can choose to provide a settings dictionary. Unlike
configuring Eve with the settings file, dictionary-based approach will only
update Eve's default settings with your own values, rather than overwriting
all the settings.

.. code-block:: python

    from eve import Eve

    my_settings = {
        'MONGO_HOST': 'localhost',
        'MONGO_PORT': 27017,
        'MONGO_DBNAME': 'the_db_name',
        'DOMAIN': {'contacts': {}}
    }

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
database instance as needed. Consider the following example:

::

    # We want to run seamlessly our API both locally and on Heroku, so:
    if os.environ.get('PORT'):
        # We're hosted on Heroku! Use the MongoHQ sandbox as our backend.
        MONGO_HOST = 'alex.mongohq.com'
        MONGO_PORT = 10047
        MONGO_USERNAME = '<user>'
        MONGO_PASSWORD = '<pw>'
        MONGO_DBNAME = '<dbname>'
    else:
        # Running on local machine. Let's just use the local mongod instance.

        # Please note that MONGO_HOST and MONGO_PORT could very well be left
        # out as they already default to a bare bones local 'mongod' instance.
        MONGO_HOST = 'localhost'
        MONGO_PORT = 27017
        MONGO_USERNAME = 'user'
        MONGO_PASSWORD = 'user'
        MONGO_DBNAME = 'apitest'

.. _global:

Global Configuration
--------------------
Besides defining the general API behavior, most global configuration settings
are used to define the standard endpoint ruleset, and can be fine-tuned later,
when configuring individual endpoints. Global configuration settings are always
uppercase.

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

=================================== =========================================
``URL_PREFIX``                      URL prefix for all API endpoints. Will be
                                    used in conjunction with ``API_VERSION`` to
                                    build API endpoints (e.g., ``api`` will be
                                    rendered to ``/api/<endpoint>``).  Defaults
                                    to ``''``.

``API_VERSION``                     API version. Will be used in conjunction with
                                    ``URL_PREFIX`` to build API endpoints
                                    (e.g., ``v1`` will be rendered to
                                    ``/v1/<endpoint>``). Defaults to ``''``.

``ALLOWED_FILTERS``                 List of fields on which filtering is allowed.
                                    Entries in this list work in a hierarchical
                                    way. This means that, for instance, filtering
                                    on ``'dict.sub_dict.foo'`` is allowed if
                                    ``ALLOWED_FILTERS`` contains any of
                                    ``'dict.sub_dict.foo``, ``'dict.sub_dict'``
                                    or ``'dict'``. Instead filtering on
                                    ``'dict'`` is allowed if ``ALLOWED_FILTERS``
                                    contains ``'dict'``.
                                    Can be set to ``[]`` (no filters allowed)
                                    or ``['*']`` (filters allowed on every
                                    field). Unless your API is comprised of
                                    just one endpoint, this global setting
                                    should be used as an on/off switch,
                                    delegating explicit whitelisting at the
                                    local level (see ``allowed_filters``
                                    below). Defaults to ``['*']``.

                                    *Please note:* If API scraping or DB DoS
                                    attacks are a concern, then globally
                                    disabling filters and whitelisting valid
                                    ones at the local level is the way to go.

``VALIDATE_FILTERS``                Whether to validate the filters against the
                                    resource schema. Invalid filters will throw
                                    an exception. Defaults to ``False``.

                                    Word of caution: validation on filter
                                    expressions involving fields with custom
                                    rules or types might have a considerable
                                    impact on performance. This is the case,
                                    for example, with ``data_relation``-rule
                                    fields. Consider excluding heavy-duty
                                    fields from filters (see
                                    ``ALLOWED_FILTERS``).

``SORTING``                         ``True`` if sorting is supported for ``GET``
                                    requests, otherwise ``False``. Can be
                                    overridden by resource settings. Defaults
                                    to ``True``.

``PAGINATION``                      ``True`` if pagination is enabled for ``GET``
                                    requests, otherwise ``False``. Can be
                                    overridden by resource settings. Defaults
                                    to ``True``.

``PAGINATION_LIMIT``                Maximum value allowed for QUERY_MAX_RESULTS
                                    query parameter. Values exceeding the
                                    limit will be silently replaced with this
                                    value. You want to aim for a reasonable
                                    compromise between performance and transfer
                                    size. Defaults to 50.

``PAGINATION_DEFAULT``              Default value for QUERY_MAX_RESULTS.
                                    Defaults to 25.

``OPTIMIZE_PAGINATION_FOR_SPEED``   Set this to ``True`` to improve pagination
                                    performance. When optimization is active no
                                    count operation, which can be slow on large
                                    collections, is performed on the database.
                                    This does have a few consequences.
                                    Firstly, no document count is returned.
                                    Secondly, ``HATEOAS`` is less accurate: no
                                    last page link is available, and next page
                                    link is always included, even on last page.
                                    On big collections, switching this feature
                                    on can greatly improve performance.
                                    Defaults to ``False`` (slower performance;
                                    document count included; accurate
                                    ``HATEOAS``).

``QUERY_WHERE``                     Key for the filters query parameter. Defaults to ``where``.

``QUERY_SORT``                      Key for the sort query parameter. Defaults to ``sort``.

``QUERY_PROJECTION``                Key for the projections query parameter. Defaults to ``projection``.

``QUERY_PAGE``                      Key for the pages query parameter. Defaults to ``page``.

``QUERY_MAX_RESULTS``               Key for the max results query parameter. Defaults to ``max_results``.

``QUERY_EMBEDDED``                  Key for the embedding query parameter. Defaults to ``embedded``.

``QUERY_AGGREGATION``               Key for the aggregation query parameter.
                                    Defaults to ``aggregate``.

``DATE_FORMAT``                     A Python date format used to parse and render
                                    datetime values. When serving requests,
                                    matching JSON strings will be parsed and
                                    stored as ``datetime`` values. In
                                    responses, ``datetime`` values will be
                                    rendered as JSON strings using this format.
                                    Defaults to the RFC1123 (ex RFC 822)
                                    standard ``a, %d %b %Y %H:%M:%S GMT``
                                    ("Tue, 02 Apr 2013 10:29:13 GMT").

``RESOURCE_METHODS``                A list of HTTP methods supported at resource
                                    endpoints. Allowed values: ``GET``,
                                    ``POST``, ``DELETE``. ``POST`` is used for
                                    insertions. ``DELETE`` will delete *all*
                                    resource contents (enable with caution).
                                    Can be overridden by resource settings.
                                    Defaults to ``['GET']``.

``PUBLIC_METHODS``                  A list of HTTP methods supported at resource
                                    endpoints, open to public access even when
                                    :ref:`auth` is enabled. Can be overridden
                                    by resource settings. Defaults to ``[]``.

``ITEM_METHODS``                    A list of HTTP methods supported at item
                                    endpoints. Allowed values: ``GET``,
                                    ``PATCH``, ``PUT`` and ``DELETE``. ``PATCH``
                                    or, for clients not supporting PATCH,
                                    ``POST`` with the ``X-HTTP-Method-Override``
                                    header tag, is used for item updates;
                                    ``DELETE`` for item deletion. Can be
                                    overridden by resource settings. Defaults to
                                    ``['GET']``.

``PUBLIC_ITEM_METHODS``             A list of HTTP methods supported at item
                                    endpoints, left open to public access when
                                    when :ref:`auth` is enabled. Can be
                                    overridden by resource settings. Defaults
                                    to ``[]``.

``ALLOWED_ROLES``                   A list of allowed `roles` for resource
                                    endpoints. Can be overridden by resource
                                    settings. See :ref:`auth` for more
                                    information. Defaults to ``[]``.

``ALLOWED_READ_ROLES``              A list of allowed `roles` for resource
                                    endpoints with GET and OPTIONS methods.
                                    Can be overridden by resource
                                    settings. See :ref:`auth` for more
                                    information. Defaults to ``[]``.

``ALLOWED_WRITE_ROLES``             A list of allowed `roles` for resource
                                    endpoints with POST, PUT and DELETE
                                    methods. Can be overridden by resource
                                    settings. See :ref:`auth` for more
                                    information. Defaults to ``[]``.

``ALLOWED_ITEM_ROLES``              A list of allowed `roles` for item endpoints.
                                    See :ref:`auth` for more information. Can
                                    be overridden by resource settings.
                                    Defaults to ``[]``.

``ALLOWED_ITEM_READ_ROLES``         A list of allowed `roles` for item endpoints
                                    with GET and OPTIONS methods.
                                    See :ref:`auth` for more information. Can
                                    be overridden by resource settings.
                                    Defaults to ``[]``.

``ALLOWED_ITEM_WRITE_ROLES``        A list of allowed `roles` for item endpoints
                                    with PUT, PATCH and DELETE methods.
                                    See :ref:`auth` for more information. Can
                                    be overridden by resource settings.
                                    Defaults to ``[]``.

``ALLOW_OVERRIDE_HTTP_METHOD``      Enables / Disables global the possibility
                                    to override the sent method with a header
                                    ``X-HTTP-METHOD-OVERRIDE``.

``CACHE_CONTROL``                   Value of the ``Cache-Control`` header field
                                    used when serving ``GET`` requests (e.g.,
                                    ``max-age=20,must-revalidate``). Leave
                                    empty if you don't want to include cache
                                    directives with API responses. Can be
                                    overridden by resource settings. Defaults
                                    to ``''``.

``CACHE_EXPIRES``                   Value (in seconds) of the ``Expires`` header
                                    field used when serving ``GET`` requests.
                                    If set to a non-zero value, the header will
                                    always be included, regardless of the
                                    setting of ``CACHE_CONTROL``. Can be
                                    overridden by resource settings. Defaults
                                    to 0.

``X_DOMAINS``                       CORS (Cross-Origin Resource Sharing) support.
                                    Allows API maintainers to specify which
                                    domains are allowed to perform CORS
                                    requests. Allowed values are: ``None``,
                                    a list of domains, or ``'*'`` for
                                    a wide-open API. Defaults to ``None``.

``X_DOMAINS_RE``                    The same setting as ``X_DOMAINS``, but a list
                                    of regexes is allowed. This is useful for
                                    websites with dynamic ranges of
                                    subdomains. Make sure to properly anchor and
                                    escape the regexes. Invalid
                                    regexes (such as ``'*'``) are ignored.
                                    Defaults to ``None``.

``X_HEADERS``                       CORS (Cross-Origin Resource Sharing) support.
                                    Allows API maintainers to specify which
                                    headers are allowed to be sent with CORS
                                    requests. Allowed values are: ``None`` or
                                    a list of headers names. Defaults to
                                    ``None``.

``X_EXPOSE_HEADERS``                CORS (Cross-Origin Resource Sharing) support.
                                    Allows API maintainers to specify which
                                    headers are exposed within a CORS response.
                                    Allowed values are: ``None`` or
                                    a list of headers names. Defaults to
                                    ``None``.

``X_ALLOW_CREDENTIALS``             CORS (Cross-Origin Resource Sharing) support.
                                    Allows API maintainers to specify if cookies can
                                    be sent by clients.
                                    The only allowed value is: ``True``, any other
                                    will be ignored. Defaults to
                                    ``None``.

``X_MAX_AGE``                       CORS (Cross-Origin Resource Sharing)
                                    support. Allows to set max age for the
                                    access control allow header. Defaults to
                                    21600.


``LAST_UPDATED``                    Name of the field used to record a document's
                                    last update date. This field is
                                    automatically handled by Eve. Defaults to
                                    ``_updated``.

``DATE_CREATED``                    Name for the field used to record a document
                                    creation date. This field is automatically
                                    handled by Eve. Defaults to ``_created``.

``ID_FIELD``                        Name of the field used to uniquely identify
                                    resource items within the database. You
                                    want this field to be properly indexed on
                                    the database. Can be overridden by resource
                                    settings. Defaults to ``_id``.

``ITEM_LOOKUP``                     ``True`` if item endpoints should be generally
                                    available across the API, ``False``
                                    otherwise. Can be overridden by resource
                                    settings. Defaults to ``True``.

``ITEM_LOOKUP_FIELD``               Document field used when looking up a resource
                                    item. Can be overridden by resource
                                    settings. Defaults to ``ID_FIELD``.

``ITEM_URL``                        URL rule used to construct default item
                                    endpoint URLs. Can be overridden by
                                    resource settings. Defaults
                                    ``regex("[a-f0-9]{24}")`` which is MongoDB
                                    standard ``Object_Id`` format.

``ITEM_TITLE``                      Title to be used when building item references,
                                    both in XML and JSON responses. Defaults to
                                    resource name, with the plural 's' stripped
                                    if present. Can and most likely will be
                                    overridden when configuring single resource
                                    endpoints.

``AUTH_FIELD``                      Enables :ref:`user-restricted`. When the
                                    feature is enabled, users can only
                                    read/update/delete resource items created
                                    by themselves. The keyword contains the
                                    actual name of the field used to store the
                                    id of the user who created the resource
                                    item. Can be overridden by resource
                                    settings. Defaults to ``None``, which
                                    disables the feature.

``ALLOW_UNKNOWN``                   When ``True``, this option will allow insertion
                                    of arbitrary, unknown fields to any API
                                    endpoint. Use with caution. See
                                    :ref:`unknown` for more information.
                                    Defaults to ``False``.

``PROJECTION``                      When ``True``, this option enables the
                                    :ref:`projections` feature. Can be
                                    overridden by resource settings. Defaults
                                    to ``True``.

``EMBEDDING``                       When ``True``, this option enables the
                                    :ref:`embedded_docs` feature. Defaults to
                                    ``True``.

``BANDWIDTH_SAVER``                 When ``True``, POST, PUT, and PATCH responses
                                    only return automatically handled fields
                                    and ``EXTRA_RESPONSE_FIELDS``. When
                                    ``False``, the entire document will be
                                    sent. Defaults to ``True``.

``EXTRA_RESPONSE_FIELDS``           Allows to configure a list of additional
                                    document fields that should be provided
                                    with every POST response. Normally only
                                    automatically handled fields (``ID_FIELD``,
                                    ``LAST_UPDATED``, ``DATE_CREATED``,
                                    ``ETAG``) are included in response
                                    payloads. Can be overridden by resource
                                    settings. Defaults to ``[]``, effectively
                                    disabling the feature.

``RATE_LIMIT_GET``                  A tuple expressing the rate limit on GET
                                    requests. The first element of the tuple is
                                    the number of requests allowed, while the
                                    second is the time window in seconds. For
                                    example, ``(300, 60 * 15)`` would set
                                    a limit of 300 requests every 15 minutes.
                                    Defaults to ``None``.

``RATE_LIMIT_POST``                 A tuple expressing the rate limit on POST
                                    requests. The first element of the tuple is
                                    the number of requests allowed, while the
                                    second is the time window in seconds. For
                                    example ``(300, 60 * 15)`` would set
                                    a limit of 300 requests every 15 minutes.
                                    Defaults to ``None``.

``RATE_LIMIT_PATCH``                A tuple expressing the rate limit on PATCH
                                    requests. The first element of the tuple is
                                    the number of requests allowed, while the
                                    second is the time window in seconds. For
                                    example ``(300, 60 * 15)`` would set
                                    a limit of 300 requests every 15 minutes.
                                    Defaults to ``None``.

``RATE_LIMIT_DELETE``               A tuple expressing the rate limit on DELETE
                                    requests. The first element of the tuple is
                                    the number of requests allowed, while the
                                    second is the time window in seconds. For
                                    example ``(300, 60 * 15)`` would set
                                    a limit of 300 requests every 15 minutes. Defaults to
                                    ``None``.

``DEBUG``                           ``True`` to enable Debug Mode, ``False``
                                    otherwise.

``ERROR``                           Allows to customize the error_code field. Defaults
                                    to ``_error``.

``HATEOAS``                         When ``False``, this option disables
                                    :ref:`hateoas_feature`. Defaults to ``True``.

``ISSUES``                          Allows to customize the issues field. Defaults
                                    to ``_issues``.

``STATUS``                          Allows to customize the status field. Defaults
                                    to ``_status``.

``STATUS_OK``                       Status message returned when data validation is
                                    successful. Defaults to ``OK``.

``STATUS_ERR``                      Status message returned when data validation
                                    failed. Defaults to ``ERR``.

``ITEMS``                           Allows to customize the items field. Defaults
                                    to ``_items``.

``META``                            Allows to customize the meta field. Defaults
                                    to ``_meta``

``INFO``                            String value to include an info section, with the
                                    given INFO name, at the Eve homepage (suggested
                                    value ``_info``). The info section will include
                                    Eve server version and API version (API_VERSION,
                                    if set).  ``None`` otherwise, if you do not want
                                    to expose any server info. Defaults to ``None``.

``LINKS``                           Allows to customize the links field. Defaults
                                    to ``_links``.

``ETAG``                            Allows to customize the etag field. Defaults
                                    to ``_etag``.

``IF_MATCH``                        ``True`` to enable concurrency control, ``False``
                                    otherwise. Defaults to ``True``. See
                                    :ref:`concurrency`.

``ENFORCE_IF_MATCH``                ``True`` to always enforce concurrency control when
                                    it is enabled, ``False`` otherwise. Defaults to
                                    ``True``. See :ref:`concurrency`.

``RENDERERS``                       Allows to change enabled renderers. Defaults to
                                    ``['eve.render.JSONRenderer', 'eve.render.XMLRenderer']``.

``JSON_SORT_KEYS``                  ``True`` to enable JSON key sorting, ``False``
                                    otherwise. Defaults to ``False``.

``JSON_REQUEST_CONTENT_TYPES``      Supported JSON content types. Useful when
                                    you need support for vendor-specific json
                                    types. Please note: responses will still
                                    carry the standard ``application/json``
                                    type. Defaults to ``['application/json']``.

``VALIDATION_ERROR_STATUS``         The HTTP status code to use for validation errors.
                                    Defaults to ``422``.

``VERSIONING``                      Enabled documents version control when
                                    ``True``. Can be overridden by resource
                                    settings. Defaults to ``False``.

``VERSIONS``                        Suffix added to the name of the primary
                                    collection to create the name of the shadow
                                    collection to store document versions.
                                    Defaults to ``_versions``. When
                                    ``VERSIONING`` is enabled , a collection
                                    such as ``myresource_versions`` would be
                                    created for a resource with a datasource of
                                    ``myresource``.

``VERSION_PARAM``                   The URL query parameter used to access the
                                    specific version of a document. Defaults to
                                    ``version``. Omit this parameter to get the
                                    latest version of a document or use
                                    `?version=all`` to get a list of all
                                    version of the document. Only valid for
                                    individual item endpoints.

``VERSION``                         Field used to store the version number of a
                                    document. Defaults to ``_version``.

``LATEST_VERSION``                  Field used to store the latest version number
                                    of a document. Defaults to
                                    ``_latest_version``.

``VERSION_ID_SUFFIX``               Used in the shadow collection to store the
                                    document id. Defaults to ``_document``. If
                                    ``ID_FIELD`` is set to ``_id``, the
                                    document id will be stored in field
                                    ``_id_document``.

``MONGO_URI``                       A `MongoDB URI`_ which is used in preference
                                    of the other configuration variables.

``MONGO_HOST``                      MongoDB server address. Defaults to ``localhost``.

``MONGO_PORT``                      MongoDB port. Defaults to ``27017``.

``MONGO_USERNAME``                  MongoDB user name.

``MONGO_PASSWORD``                  MongoDB password.

``MONGO_DBNAME``                    MongoDB database name.

``MONGO_OPTIONS``                   MongoDB keyword arguments to passed to
                                    MongoClient class ``__init__``.
                                    Defaults to ``{'connect': True, 'tz_aware': True, 'appname': 'flask_app_name'}``.
                                    See `PyMongo mongo_client`_ for reference.

``MONGO_AUTH_SOURCE``               MongoDB authorization database. Defaults to ``None``.

``MONGO_AUTH_MECHANISM``            MongoDB authentication mechanism.
                                    See `PyMongo Authentication Mechanisms`_.
                                    Defaults to ``None``.

``MONGO_AUTH_MECHANISM_PROPERTIES`` Specify MongoDB extra authentication mechanism properties
                                    if required. Defaults to ``None``.

``MONGO_QUERY_BLACKLIST``           A list of Mongo query operators that are not
                                    allowed to be used in resource filters
                                    (``?where=``). Defaults to ``['$where',
                                    '$regex']``.

                                    Mongo JavaScript operators are disabled by
                                    default, as they might be used as vectors
                                    for injection attacks. Javascript queries
                                    also tend to be slow and generally can be
                                    easily replaced with the (very rich) Mongo
                                    query dialect.

``MONGO_QUERY_WHITELIST``           A list of extra Mongo query operators to allow
                                    besides the official list of allowed operators.
                                    Defaults to ``[]``.

                                    Can be overridden at endpoint (Mongo
                                    collection) level. See
                                    ``mongo_query_whitelist`` below.


``MONGO_WRITE_CONCERN``             A dictionary defining MongoDB write concern
                                    settings. All standard write concern
                                    settings (w, wtimeout, j, fsync) are
                                    supported. Defaults to ``{'w': 1}``, which
                                    means 'do regular acknowledged writes'
                                    (this is also the Mongo default).

                                    Please be aware that setting 'w' to a value of
                                    2 or greater requires replication to be
                                    active or you will be getting 500 errors
                                    (the write will still happen; Mongo will
                                    just be unable to check that it's being
                                    written to multiple servers).

                                    Can be overridden at endpoint (Mongo
                                    collection) level. See
                                    ``mongo_write_concern`` below.

``DOMAIN``                          A dict holding the API domain definition.
                                    See `Domain Configuration`_.

``EXTENDED_MEDIA_INFO``             A list of properties to forward from the file upload
                                    driver.

``RETURN_MEDIA_AS_BASE64_STRING``   Controls the embedding of the media type in
                                    the endpoint response. This is useful when
                                    you have other means of getting the binary
                                    (like custom Flask endpoints) but still
                                    want clients to be able to POST/PATCH it.
                                    Defaults to ``True``.

``RETURN_MEDIA_AS_URL``             Set it to ``True`` to enable serving media
                                    files at a dedicated media endpoint.
                                    Defaults to ``False``.

``MEDIA_BASE_URL``                  Base URL to be used when
                                    ``RETURN_MEDIA_AS_URL`` is active. Combined
                                    with ``MEDIA_ENDPOINT`` and ``MEDIA_URL``
                                    dictates the URL returned for media files.
                                    If ``None``, which is the default value,
                                    the API base address will be used instead.

``MEDIA_ENDPOINT``                  The media endpoint to be used when
                                    ``RETURN_MEDIA_AS_URL`` is enabled.
                                    Defaults to ``media``.

``MEDIA_URL``                       Format of a file url served at the
                                    dedicated media endpoints. Defaults to
                                    ``regex("[a-f0-9]{24}")``.

``MULTIPART_FORM_FIELDS_AS_JSON``   In case you are submitting your resource as
                                    ``multipart/form-data`` all form data fields
                                    will be submitted as strings, breaking any
                                    validation rules you might have on the
                                    resource fields. If you want to treat all
                                    submitted form data as JSON strings you will
                                    have to activate this setting. In that case
                                    field validation will continue working
                                    correctly. Read more about how the fields
                                    should be formatted at
                                    :ref:`multipart`. Defaults to ``False``.

``AUTO_COLLAPSE_MULTI_KEYS``        If set to ``True``, multiple values sent
                                    with the same key, submitted using the
                                    ``application/x-www-form-urlencoded`` or
                                    ``multipart/form-data`` content types,
                                    will automatically be converted to a list of
                                    values.

                                    When using this together with
                                    ``AUTO_CREATE_LISTS`` it becomes possible
                                    to use lists of media fields.

                                    Defaults to ``False``

``AUTO_CREATE_LISTS``               When submitting a non ``list`` type value
                                    for a field with type ``list``,
                                    automatically create a one element list
                                    before running the validators.

                                    Defaults to ``False``

``OPLOG``                           Set it to ``True`` to enable the :ref:`oplog`.
                                    Defaults to ``False``.

``OPLOG_NAME``                      This is the name of the database collection
                                    where the :ref:`oplog` is stored. Defaults
                                    to ``oplog``.

``OPLOG_METHODS``                   List of HTTP methods which operations
                                    should be logged in the :ref:`oplog`.
                                    Defaults to ``['DELETE', 'POST', 'PATCH',
                                    'PUT']``.

``OPLOG_CHANGE_METHODS``            List of HTTP methods which operations
                                    will include changes into the :ref:`oplog` entry.
                                    Defaults to ``['DELETE','PATCH', 'PUT']``.

``OPLOG_ENDPOINT``                  Name of the :ref:`oplog` endpoint. If the
                                    endpoint is enabled it can be configured
                                    like any other API endpoint. Set it to
                                    ``None`` to disable the endpoint. Defaults
                                    to ``None``.

``OPLOG_AUDIT``                     Set it to ``True`` to enable the audit
                                    feature. When audit is enabled client IP
                                    and document changes are also logged to the
                                    :ref:`oplog`. Defaults to ``True``.

``OPLOG_RETURN_EXTRA_FIELD``        When enabled, the optional ``extra`` field
                                    will be included in the payload returned by
                                    the ``OPLOG_ENDPOINT``. Defaults to
                                    ``False``.

``SCHEMA_ENDPOINT``                 Name of the :ref:`schema_endpoint`. Defaults
                                    to ``None``.

``HEADER_TOTAL_COUNT``              Custom header containing total count of
                                    items in response payloads for collection
                                    ``GET`` requests. This is handy for ``HEAD``
                                    requests when client wants to know items
                                    count without retrieving response body.
                                    An example use case is to get the count
                                    of unread posts using ``where`` query without
                                    loading posts themselves. Defaults to
                                    ``X-Total-Count``.

``JSONP_ARGUMENT``                  This option will cause the response to be
                                    wrapped in a JavaScript function call if
                                    the argument is set in the request. For
                                    example if you set ``JSON_ARGUMENT
                                    = 'callback'``, then all responses to
                                    ``?callback=funcname`` requests will be
                                    wrapped in a ``funcname`` call. Defaults to
                                    ``None``.

``BULK_ENABLED``                    Enables bulk insert when set to ``True``.
                                    See :ref:`bulk_insert` for more
                                    information. Defaults to ``True``.

``SOFT_DELETE``                     Enables soft delete when set to ``True``.
                                    See :ref:`soft_delete` for more
                                    information. Defaults to ``False``.

``DELETED``                         Field name used to indicate if a document
                                    has been deleted when ``SOFT_DELETE``
                                    is enabled. Defaults to ``_deleted``.

``SHOW_DELETED_PARAM``              The URL query parameter used to include
                                    soft deleted items in resource level GET
                                    responses. Defaults to 'show_deleted'.

``STANDARD_ERRORS``                 This is a list of HTTP error codes for
                                    which a standard API response will be
                                    provided. Canonical error response includes
                                    a JSON body with actual error code and
                                    description. Set this to an empty list if
                                    you want to disable canonical responses
                                    altogether. Defaults to ``[400, 401, 403,
                                    404, 405, 406, 409, 410, 412, 422, 428]``

``VALIDATION_ERROR_AS_STRING``      If ``True`` even single field errors will
                                    be returned in a list. By default single
                                    field errors are returned as strings while
                                    multiple field errors are bundled in a
                                    list. If you want to standardize the field
                                    errors output, set this setting to ``True``
                                    and you will always get a list of field
                                    issues. Defaults to ``False``.

``UPSERT_ON_PUT``                   ``PUT`` attempts to create a document if it
                                    does not exist. The URL endpoint will be
                                    used as ``ID_FIELD`` value (if ``ID_FIELD``
                                    is included with the payload, it will be
                                    ignored). Normal validation rules apply.
                                    The response will be a ``201 Created`` on
                                    successful creation. Response payload will
                                    be identical the one you would get by
                                    performing a single document POST to the
                                    resource endpoint. Set to ``False`` to
                                    disable this feature, and a ``404`` will be
                                    returned instead. Defaults to ``True``.

``MERGE_NESTED_DOCUMENTS``          If ``True``, updates to nested fields are
                                    merged with the current data on ``PATCH``.
                                    If ``False``, the updates overwrite the
                                    current data. Defaults to ``True``.

``NORMALIZE_DOTTED_FIELDS``         If ``True``, dotted fields are parsed
                                    and processed as subdocument fields. If
                                    ``False``, dotted fields are left unparsed
                                    and unprocessed, and the payload is passed
                                    to the underlying data-layer as-is. Please
                                    note that with the default Mongo layer,
                                    setting this to ``False`` will result in an
                                    error. Defaults to ``True``.
``NORMALIZE_ON_PATCH``              If ``True``, the patch document will be
                                    normalized according to schema. This means
                                    if a field is not included in the patch
                                    body, it will be reset to the default value
                                    in its schema. If ``False``, the field which
                                    is not included in the patch body will be
                                    kept untouched. Defaults to ``True``.

=================================== =========================================

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
                                configurable).

                                You can also use regexes to setup
                                subresource-like endpoints. See
                                :ref:`subresources`.

``allowed_filters``             List of fields on which filtering is allowed.
                                Entries in this list work in a hierarchical
                                way. This means that, for instance, filtering
                                on ``'dict.sub_dict.foo'`` is allowed if
                                ``allowed_filters`` contains any of
                                ``'dict.sub_dict.foo``, ``'dict.sub_dict'``
                                or ``'dict'``. Instead filtering on
                                ``'dict'`` is allowed if ``allowed_filters``
                                contains ``'dict'``.
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
                                endpoint. Allowed values: ``GET``, ``PATCH``,
                                ``PUT`` and ``DELETE``. ``PATCH`` or, for
                                clients not supporting PATCH, ``POST`` with
                                the ``X-HTTP-Method-Override`` header tag.
                                Locally overrides ``ITEM_METHODS``.

``public_item_methods``         A list of HTTP methods supported at item
                                endpoint, left open to public access when
                                :ref:`auth` is enabled. Locally overrides
                                ``PUBLIC_ITEM_METHODS``.

``allowed_roles``               A list of allowed `roles` for resource
                                endpoint. See :ref:`auth` for more
                                information. Locally overrides
                                ``ALLOWED_ROLES``.

``allowed_read_roles``          A list of allowed `roles` for resource
                                endpoint with GET and OPTIONS methods.
                                See :ref:`auth` for more
                                information. Locally overrides
                                ``ALLOWED_READ_ROLES``.

``allowed_write_roles``         A list of allowed `roles` for resource
                                endpoint with POST, PUT and DELETE.
                                See :ref:`auth` for more
                                information. Locally overrides
                                ``ALLOWED_WRITE_ROLES``.

``allowed_item_read_roles``     A list of allowed `roles` for item endpoint
                                with GET and OPTIONS methods.
                                See :ref:`auth` for more information.
                                Locally overrides ``ALLOWED_ITEM_READ_ROLES``.


``allowed_item_write_roles``    A list of allowed `roles` for item endpoint
                                with PUT, PATH and DELETE methods.
                                See :ref:`auth` for more information.
                                Locally overrides ``ALLOWED_ITEM_WRITE_ROLES``.

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

``id_field``                    Field used to uniquely identify resource items
                                within the database. Locally overrides
                                ``ID_FIELD``.

``item_lookup``                 ``True`` if item endpoint should be available,
                                ``False`` otherwise. Locally overrides
                                ``ITEM_LOOKUP``.

``item_lookup_field``           Field used when looking up a resource
                                item. Locally overrides ``ITEM_LOOKUP_FIELD``.

``item_url``                    Rule used to construct item endpoint URL.
                                Locally overrides ``ITEM_URL``.

``resource_title``              Title used when building resource links
                                (HATEOAS). Defaults to resource's ``url``.

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
                                a string, then you put a URL rule in `url`.  If
                                it is an integer, then you just omit `url`, as
                                it is automatically handled.  See the code
                                snippet below for an usage example of this
                                feature.

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
                                ``LAST_UPDATED``, ``DATE_CREATED``, ``ETAG``)
                                are included in response payloads. Overrides
                                ``EXTRA_RESPONSE_FIELDS``.

``hateoas``                     When ``False``, this option disables
                                :ref:`hateoas_feature` for the resource.
                                Defaults to ``True``.

``mongo_query_whitelist``       A list of extra Mongo query operators to allow
                                for this endpoint besides the official list of
                                allowed operators. Defaults to ``[]``.

``mongo_write_concern``         A dictionary defining MongoDB write concern
                                settings for the endpoint datasource. All
                                standard write concern settings (w, wtimeout, j,
                                fsync) are supported. Defaults to ``{'w': 1}``
                                which means 'do regular acknowledged writes'
                                (this is also the Mongo default.)

                                Please be aware that setting 'w' to a value of
                                2 or greater requires replication to be active
                                or you will be getting 500 errors (the write
                                will still happen; Mongo will just be unable
                                to check that it's being written to multiple
                                servers.)

``mongo_prefix``                Allows overriding of the default ``MONGO``
                                prefix, which is used when retrieving MongoDB
                                settings from configuration.

                                For example if ``mongo_prefix`` is set to
                                ``MONGO2`` then, when serving requests for the
                                endpoint, ``MONGO2`` prefixed settings will
                                be used to access the database.

                                This allows for eventually serving data from
                                a different database/server at every endpoint.

                                See also: :ref:`authdrivendb`.

``mongo_indexes``               Allows to specify a set of indexes to be
                                created for this resource before the app is
                                launched.

                                Indexes are expressed as a dict where keys are
                                index names and values are either a list of
                                tuples of (field, direction) pairs, or
                                a tuple with a list of field/direction pairs
                                *and* index options expressed as a dict, such
                                as ``{'index name': [('field', 1)], 'index with
                                args': ([('field', 1)], {"sparse": True})}``.

                                Multiple pairs are used to create compound
                                indexes. Direction takes all kind of values
                                supported by PyMongo, such as ``ASCENDING``
                                = 1 and ``DESCENDING`` = -1. All index options
                                such as ``sparse``, ``min``, ``max``,
                                etc. are supported (see PyMongo_ documentation.)

                                *Please note:* keep in mind that index design,
                                creation and maintenance is a very important
                                task and should be planned and executed with
                                great care. Usually it is also a very resource
                                intensive operation. You might therefore want
                                to handle this task manually, out of the
                                context of API instantiation. Also remember
                                that, by default, any already existent index
                                for which the definition has been changed, will
                                be dropped and re-created.

``authentication``              A class with the authorization logic for the
                                endpoint. If not provided the eventual
                                general purpose auth class (passed as
                                application constructor argument) will be used.
                                For details on authentication and authorization
                                see :ref:`auth`.  Defaults to ``None``,

``embedded_fields``             A list of fields for which :ref:`embedded_docs`
                                is enabled by default. For this feature to work
                                properly fields in the list must be
                                ``embeddable``, and ``embedding`` must be
                                active for the resource.

``query_objectid_as_string``    When enabled the Mongo parser will avoid
                                automatically casting electable strings to
                                ObjectIds. This can be useful in those rare
                                occurrences where you have string fields in the
                                database whose values can actually be casted to
                                ObjectId values, but shouldn't. It effects
                                queries (``?where=``) and parsing of payloads.
                                Defaults to ``False``.

``internal_resource``           When ``True``, this option makes the resource
                                internal. No HTTP action can be performed on
                                the endpoint, which is still accessible from
                                the Eve data layer. See
                                :ref:`internal_resources` for more
                                information. Defaults to ``False``.

``etag_ignore_fields``          List of fields that
                                should not be used to compute the ETag value.
                                Defaults to ``None`` which means that by
                                default all fields are included in the computation.
                                It looks like ``['field1', 'field2',
                                'field3.nested_field', ...]``.

``schema``                      A dict defining the actual data structure being
                                handled by the resource. Enables data
                                validation. See `Schema Definition`_.

``bulk_enabled``                When ``True`` this option enables the
                                :ref:`bulk_insert` feature for this resource.
                                Locally overrides ``BULK_ENABLED``.

``soft_delete``                 When ``True`` this option enables the
                                :ref:`soft_delete` feature for this resource.
                                Locally overrides ``SOFT_DELETE``.

``merge_nested_documents``      If ``True``, updates to nested fields are
                                merged with the current data on ``PATCH``.
                                If ``False``, the updates overwrite the
                                current data. Locally overrides
                                ``MERGE_NESTED_DOCUMENTS``.
``normalize_dotted_fields``     If ``True``, dotted fields are parsed and
                                processed as subdocument fields. If ``False``,
                                dotted fields are left unparsed and
                                unprocessed, and the payload is passed to the
                                underlying data-layer as-is. Please note that
                                with the default Mongo layer, setting this to
                                ``False`` will result in an error. Defaults to
                                ``True``.
``normalize_on_patch``          If ``True``, the patch document will be
                                normalized according to schema. This means if
                                a field is not included in the patch body, it
                                will be reset to the default value in its
                                schema. If ``False``, the field which is not
                                included in the patch body will be kept
                                untouched. Defaults to ``True``.

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
            'url': 'regex("[\w]+")',
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
    schema = {
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

                                - ``string``
                                - ``boolean``
                                - ``integer``
                                - ``float``
                                - ``number`` (integer and float values allowed)
                                - ``datetime``
                                - ``dict``
                                - ``list``
                                - ``media``

                                If the MongoDB data layer is used then
                                ``objectid``, ``dbref`` and geographic data
                                structures are also allowed:

                                - ``objectid``
                                - ``dbref``
                                - ``point``
                                - ``multipoint``
                                - ``linestring``
                                - ``multilinestring``
                                - ``polygon``
                                - ``multipolygon``
                                - ``geometrycollection``
                                - ``decimal``

                                See :ref:`GeoJSON <geojson_feature>` for more
                                information geo fields.

``required``                    If ``True``, the field is mandatory on
                                insertion.

``readonly``                    If ``True``, the field is readonly.

``minlength``, ``maxlength``    Minimum and maximum length allowed for
                                ``string`` and ``list`` types.

``min``, ``max``                Minimum and maximum values allowed for
                                ``integer``, ``float`` and ``number`` types.

``allowed``                     List of allowed values for ``string`` and
                                ``list`` types.

``empty``                       Only applies to string fields. If ``False``,
                                validation will fail if the value is empty.
                                Defaults to ``True``.

``items``                       Defines a list of values allowed in a ``list``
                                of fixed length, see `docs <http://docs.python-cerberus.org/en/latest/usage.html#items-list>`_.

``schema``                      Validation schema for ``dict`` types and
                                arbitrary length ``list`` types. For details
                                and usage examples, see `Cerberus documentation <http://docs.python-cerberus.org/en/latest/usage.html#schema-dict>`_.

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

``unique_to_user``              The field value is unique to the user. This is
                                useful when :ref:`user-restricted` is
                                enabled on an endpoint. The rule will be
                                validated against *user data only*. So in this
                                scenario duplicates are allowed as long as they
                                are stored by different users. Conversely,
                                a single user cannot store duplicate values.

                                If URRA is not active on the endpoint, this
                                rule behaves like ``unique``

``unique_within_resource``      The value of the field must be unique within
                                the resource.

                                This differs from the ``unique`` rule in that
                                it will use the datasource filter when searching
                                for documents with the same value for the field.
                                Use this when the resource shares the database
                                collection with other resources but their documents
                                should not be taken into account when evaluating
                                the uniqueness of the field. When used in a resource
                                without datasource filter, this rule behaves like
                                ``unique``.

``data_relation``               Allows to specify a referential integrity rule
                                that the value must satisfy in order to
                                validate. It is a dict with four keys:

                                - ``resource``: the name of the resource being referenced;
                                - ``field``: the field name in the foreign resource;
                                - ``embeddable``: set to ``True`` if clients can
                                  request the referenced document to be embedded
                                  with the serialization. See :ref:`embedded_docs`. Defaults to ``False``.
                                - ``version``: set to ``True`` to require a
                                  ``_version`` with the data relation. See :ref:`document_versioning`.
                                  Defaults to ``False``.

``nullable``                    If ``True``, the field value can be set to
                                ``None``.

``default``                     The default value for the field. When serving
                                POST and PUT requests, missing fields will be
                                assigned the configured default values.

                                It works also for types ``dict`` and ``list``.
                                The latter is restricted and works only for
                                lists with schemas (list with a random number
                                of elements and each element being a ``dict``)

                                ::

                                    schema = {
                                      # Simple default
                                      'title': {
                                        'type': 'string',
                                        'default': 'M.'
                                      },
                                      # Default in a dict
                                      'others': {
                                        'type': 'dict',
                                        'schema': {
                                          'code': {
                                            'type': 'integer',
                                            'default': 100
                                          }
                                        }
                                      },
                                      # Default in a list of dicts
                                      'mylist': {
                                        'type': 'list',
                                        'schema': {
                                          'type': 'dict',
                                          'schema': {
                                            'name': {'type': 'string'},
                                            'customer': {
                                              'type': 'boolean',
                                              'default': False
                                            }
                                          }
                                        }
                                      }
                                    }

``versioning``                  Enabled documents version control when ``True``.
                                Defaults to ``False``.

``versioned``                   If ``True``, this field will be included in the
                                versioned history of each document when
                                ``versioning`` is enabled. Defaults to ``True``.

``valueschema``                 Validation schema for all values of a ``dict``.
                                The dict can have arbitrary keys, the values
                                for all of which must validate with given
                                schema. See `valueschema <http://docs.python-cerberus.org/en/latest/validation-rules.html#valueschema>`_ in Cerberus docs.

``keyschema``                   This is the counterpart to ``valueschema`` that
                                validates the keys of a dict.   Validation
                                schema for all values of a ``dict``. See
                                `keyschema <http://docs.python-cerberus.org/en/latest/validation-rules.html#keyschema>`_ in Cerberus docs.


``regex``                       Validation will fail if field value does not
                                match the provided regex rule. Only applies to
                                string fields. See `regex <http://docs.python-cerberus.org/en/latest/validation-rules.html#regex>`_ in Cerberus docs.


``dependencies``                This rule allows a list of fields that must be
                                present in order for the target field to be
                                allowed. See `dependencies <http://docs.python-cerberus.org/en/latest/validation-rules.html#dependencies>`_  in Cerberus docs.

``anyof``                       This rule allows you to list multiple sets of
                                rules to validate against. The field will be
                                considered valid if it validates against one
                                set in the list. See `*of-rules <http://docs.python-cerberus.org/en/latest/validation-rules.html#of-rules>`_ in Cerberus docs.

``allof``                       Same as ``anyof``, except that all rule
                                collections in the list must validate.

``noneof``                      Same as ``anyof``, except that it requires no
                                rule collections in the list to validate.

``oneof``                       Same as ``anyof``, except that only one rule
                                collections in the list can validate.

``coerce``                      Type coercion allows you to apply a callable to
                                a value before any other validators run. The
                                return value of the callable replaces the new
                                value in the document. This can be used to
                                convert values or sanitize data before it is
                                validated. See `value coercion <http://docs.python-cerberus.org/en/latest/normalization-rules.html#value-coercion>`_ in Cerberus docs.

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

.. _datasource:

Advanced Datasource Patterns
----------------------------
The ``datasource`` keyword allows to explicitly link API resources to database
collections. If omitted, the domain resource key is assumed to also be the name
of the database collection. It is a dictionary with four allowed keys:

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

=============================== ==============================================
``source``                      Name of the database collection consumed by the
                                resource.  If omitted, the resource name is
                                assumed to also be a valid collection name. See
                                :ref:`source`.

``filter``                      Database query used to retrieve and validate
                                data. If omitted, by default the whole
                                collection is retrieved. See :ref:`filter`.

``projection``                  Fieldset exposed by the endpoint. If omitted,
                                by default all fields will be returned to the
                                client. See :ref:`projection`.

``default_sort``                Default sorting for documents retrieved at the
                                endpoint. If omitted, documents will be
                                returned with the default database order.
                                A valid statement would be:

                                ``'datasource': {'default_sort': [('name',
                                1)]}``

                                For more information on sort and filters see
                                :ref:`filters`.

``aggregation``                 Aggregation pipeline and options. When used all
                                other ``datasource`` settings are ignored,
                                except ``source``. The endpoint will be
                                read-only and no item lookup will be available.
                                Defaults to ``None``.

                                This is a dictionary with one or more of the
                                following keys:

                                - ``pipeline``. The aggregation pipeline.
                                  Syntax must match the one supported by
                                  PyMongo. For more information see `PyMongo
                                  Aggregation Examples`_ and the official
                                  `MongoDB Aggregation Framework`_
                                  documentation.

                                - ``options``. Aggregation options. Must be
                                  a dictionary with one or more of these keys:

                                    - ``allowDiskUse`` (bool)
                                    - ``maxTimeMS`` (int)
                                    - ``batchSize`` (int)
                                    - ``useCursor`` (bool)

                                You only need to set ``options`` if you want to
                                change any of `PyMongo aggregation defaults`_.

=============================== ==============================================

.. _filter:

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

.. admonition:: Static vs Dynamic filters

    Predefined filters are static. You can also exploit the :ref:`eventhooks`
    system (specifically, ``on_pre_<METHOD>`` hooks) to set up dynamic filters
    instead.

.. _source:

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

.. _projection:

Limiting the Fieldset Exposed by the API Endpoint
'''''''''''''''''''''''''''''''''''''''''''''''''
By default API responses to GET requests will include all fields defined by the
corresponding resource schema_. The ``projection`` setting of the `datasource`
resource keyword allows you to redefine the fieldset.

When you want to hide some *secret fields* from client, you should use
inclusive projection setting and include all fields should be exposed. While,
when you want to limit default responses to certain fields but still allow them
to be accessible through client-side projections, you should use exclusive
projection setting and exclude fields should be omitted.

The following is an example for inclusive projection setting:

::

    people = {
        'datasource': {
            'projection': {'username': 1}
            }
        }

The above setting will expose only the `username` field to GET requests, no
matter the schema_ defined for the resource. And other fields **will not** be
exposed even by client-side projection. The following API call will not return
`lastname` or `born`.

.. code-block:: console

    $ curl -i http://myapi/people?projection={"lastname": 1, "born": 1}
    HTTP/1.1 200 OK

You can also exclude fields from API responses. But this time, the excluded
fields **will be** exposed to client-side projection. The following is an
example for exclusive projection setting:

::

    people = {
        'datasource': {
            'projection': {'username': 0}
            }
        }

The above will include all document fields but `username`. However, the
following API call will return `username` this time. Thus, you can exploit this
behaviour to serve media fields or other expensive fields.

In most cases, none or inclusive projection setting is preferred. With
inclusive projection, secret fields are taken care from server side, and default
fields returned can be defined by short-cut functions from client-side.

.. code-block:: console

    $ curl -i http://myapi/people?projection={"username": 1}
    HTTP/1.1 200 OK


Please note that POST and PATCH methods will still allow the whole schema to be
manipulated. This feature can come in handy when, for example, you want to
protect insertion and modification behind an :ref:`auth` scheme while leaving
read access open to the public.

.. admonition:: See also

    - :ref:`projections`
    - :ref:`projection_filestorage`

.. _Cerberus: http://python-cerberus.org
.. _`MongoDB URI`: http://docs.mongodb.org/manual/reference/connection-string/#Connections-StandardConnectionStringFormat
.. _ReadPreference: http://api.mongodb.org/python/current/api/pymongo/read_preferences.html#pymongo.read_preferences.ReadPreference
.. _PyMongo: http://api.mongodb.org/python/current/api/pymongo/collection.html#pymongo.collection.Collection.create_index
.. _`PyMongo Aggregation Examples`: http://api.mongodb.org/python/current/examples/aggregation.html#aggregation-framework
.. _`MongoDB Aggregation Framework`: https://docs.mongodb.org/v3.0/applications/aggregation/
.. _`PyMongo aggregation defaults`: http://api.mongodb.org/python/current/api/pymongo/collection.html#pymongo.collection.Collection.aggregate
.. _`PyMongo Authentication Mechanisms`: https://docs.mongodb.com/v3.0/core/authentication-mechanisms/
.. _`PyMongo mongo_client`: http://api.mongodb.com/python/current/api/pymongo/mongo_client.html
