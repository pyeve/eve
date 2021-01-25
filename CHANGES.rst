Changelog
=========

Here you can see the full list of changes between each Eve release.

In Development
---------------

- hic sunt leones.

Version 1.1.5
-------------

Released on January 25, 2021.

Fixed
~~~~~

- Nested unique field validation still don't work (`#1435`_)
- Documentation: corrected variable name (`#1426`_)
- Versioning: support for dynamic datasources (`#1423`_)
- Disable MD5 support in GridFS, as it is deprecated (`#1410`_)
- Demo application has been terminated by Heroku. Dropped any reference to it.

.. _`#1435`: https://github.com/pyeve/eve/issues/1435
.. _`#1426`: https://github.com/pyeve/eve/pull/1426
.. _`#1423`: https://github.com/pyeve/eve/issues/1423
.. _`#1410`: https://github.com/pyeve/eve/issues/1410

Version 1.1.4
-------------

Released on October 22, 2020.

Fixed
~~~~~

- Error raised when using ``embedded`` with nested dict (`#1416`_)
- Expose media endpoint only if ``RETURN_MEDIA_AS_URL`` is set to ``True`` (`#1415`_)
- Use ``**mongo_options`` in ``with_options`` (`#1413`_)

.. _`#1416`: https://github.com/pyeve/eve/issues/1416
.. _`#1415`: https://github.com/pyeve/eve/pull/1415
.. _`#1413`: https://github.com/pyeve/eve/issues/1413

Version 1.1.3
-------------

Released on September 19, 2020.

Fixed
~~~~~

- Fix: Race condition in PATCH on newly created documents with clustered mongo (`#1411`_)

.. _`#1411`: https://github.com/pyeve/eve/issues/1411

Version 1.1.2
-------------

Released on July 9, 2020.

Fixed
~~~~~

- Add missed condition when projection is disabled per domain (`#1398`_)
- Removed unnecessary comprehension (`#1391`_)

.. _`#1398`: https://github.com/pyeve/eve/pull/1398
.. _`#1391`: https://github.com/pyeve/eve/pull/1391

Version 1.1.1
-------------

Released on May 10, 2020.

Fixed
~~~~~

- Disabling ``merge_nested_documents`` breaks versioning on PATCH (`#1389`_)
- Tests failing with Flask 1.1.2 (`#1378`_)
- ``BANDWIDTH_SAVER`` no longer works with ``resolve_resource_projection`` (`#1338`_)
- ``unique_within_resource`` rule used in resources without datasource filter (`#1368`_)
- dicts without ``schema`` rule are broken since ``b8d8fcd`` (`#1366`_)
- 403 Forrbidden added to ``STANDARD_ERRORS`` (`#1362`_)
- ``unique`` constraint doesn't work when inside of a dict or a list (`#1360`_)
- Documentation typos (`#1375`_)

.. _`#1389`: https://github.com/pyeve/eve/issues/1389
.. _`#1378`: https://github.com/pyeve/eve/pull/1378
.. _`#1375`: https://github.com/pyeve/eve/pull/1375
.. _`#1338`: https://github.com/pyeve/eve/issues/1338
.. _`#1368`: https://github.com/pyeve/eve/pull/1368
.. _`#1366`: https://github.com/pyeve/eve/pull/1366
.. _`#1362`: https://github.com/pyeve/eve/pull/1362
.. _`#1360`: https://github.com/pyeve/eve/issues/1360

Version 1.1
-----------

Released on February 7, 2020.

New
~~~
- ``MONGO_QUERY_WHITELIST`` and ``mongo_query_whitelist``. A list of extra Mongo
  query operators to allow besides the official list of allowed operators.
  Defaults to ``[]``. (`#1351`_)

Fixed
~~~~~
- Starup crash with Werkzeug 1.0 (`#1359`_)
- ``$eq`` is missing from supported query operators (`#1351`_)
- Documentation typos (`#1348`_, `#1350`_)

.. _`#1359`: https://github.com/pyeve/eve/issues/1359
.. _`#1351`: https://github.com/pyeve/eve/issues/1351
.. _`#1350`: https://github.com/pyeve/eve/pull/1350
.. _`#1348`: https://github.com/pyeve/eve/issues/1348

Version 1.0.1
-------------

Released on January 26, 2020.

- Fix: Mixing foreign and local object ids breaks querying (`#1345`_)

.. _`#1345`: https://github.com/pyeve/eve/issues/1345

Version 1.0
-----------

Released on December 19, 2019.

New
~~~
- Python 3.8 added to CI matrix (`#1326`_)
- Drop support for Python 3.4 (`#1297`_)
- ``unique_within_resource`` validation rule. Enforces the uniqueness of an
  attribute only at API resource level, contrasting with the ``unique`` rule
  that enforces uniqueness at database collection level (`#1291`_)
- Add doc8 to dev-requirements (`#1343`_)

.. _`#1343`: https://github.com/pyeve/eve/issues/1343
.. _`#1326`: https://github.com/pyeve/eve/issues/1326
.. _`#1297`: https://github.com/pyeve/eve/issues/1297
.. _`#1291`: https://github.com/pyeve/eve/issues/1291

Fixed
~~~~~
- Pin to Cerberus < 2.0 (`#1342`_)
- 500 error when PATCH or PUT are performed on Mongo 4.2 and ``_id`` is
  included with payload (`#1341`_)
- Minor style improvements and 2 test fixes (`#1330`_)
- Werkzeug 0.15.4 crashes with Python 3.8 (`#1325`_)
- Curl request in projection examples do not work (`#1298`_)
- Update installation instructions (`#1303`_)
- (*breaking*) Delete on empty resource returns 404, should return 204
  (`#1299`_)
- ``MONGO_REPLICA_SET`` ignored (`#1302`_)
- Documentation typo (`#1293`_, `#1315`_, `#1322`_, `#1324`_, `#1327`_)
- Flask 1.1.1 breaks ``test_logging_info`` test (`#1296`_)
- Display the full release number on Eve frontpage.
- Update link to EveGenie repository. New maintainer: David Zisky.

.. _`#1342`: https://github.com/pyeve/eve/issues/1342
.. _`#1341`: https://github.com/pyeve/eve/issues/1341
.. _`#1330`: https://github.com/pyeve/eve/pull/1330
.. _`#1327`: https://github.com/pyeve/eve/pull/1327
.. _`#1325`: https://github.com/pyeve/eve/pull/1325
.. _`#1324`: https://github.com/pyeve/eve/pull/1324
.. _`#1322`: https://github.com/pyeve/eve/pull/1322
.. _`#1315`: https://github.com/pyeve/eve/pull/1315
.. _`#1298`: https://github.com/pyeve/eve/issues/1298
.. _`#1303`: https://github.com/pyeve/eve/pull/1303
.. _`#1299`: https://github.com/pyeve/eve/issues/1299
.. _`#1302`: https://github.com/pyeve/eve/issues/1302
.. _`#1296`: https://github.com/pyeve/eve/issues/1296
.. _`#1293`: https://github.com/pyeve/eve/issues/1293

Version 0.9.2
-------------

Released on June 14, 2019.

Fixed
~~~~~


- Geo queries lack support for the ``$minDistance`` mongo operator (`#1281`_)
- Lookup argument does not get passed to ``pre_<event>`` hook with certain
  resource urls (`#1283`_)
- PUT requests doesn't set default values for fields that have one defined
  (`#1280`_)
- PATCH crashes when normalizing default fields (`#1275`_, `#1274`_)
- The condition that avoids returning ``X-Total-Count`` when counting is
  disabled also filters out the case where the resource is empty and count is
  0 (`#1279`_)
- First example of Eve use doesn't really work (`#1277`_)

.. _`#1283`: https://github.com/pyeve/eve/issues/1283
.. _`#1281`: https://github.com/pyeve/eve/issues/1281
.. _`#1280`: https://github.com/pyeve/eve/issues/1280
.. _`#1277`: https://github.com/pyeve/eve/issues/1277
.. _`#1275`: https://github.com/pyeve/eve/issues/1275
.. _`#1274`: https://github.com/pyeve/eve/issues/1274
.. _`#1279`: https://github.com/pyeve/eve/issues/1279

Version 0.9.1
-------------

Released on May 22, 2019.

New
~~~~~
- ``NORMALIZE_ON_PATCH`` switches normalization on patch requests (`#1234`_)

Fixed
~~~~~
- Document count broken with concurrent requests (`#1271`_)
- Document count broken when embedded resources are requested (`#1268`_)
- If ``ignore_fields`` contains a nested field, document is mutated (`#1266`_)
- Crash with Werzeug >= 0.15.3 (`#1267`_)
- Fix crash when trying to ignore a nested field that doesn't exist (`#1263`_)

Improved
~~~~~~~~
- Remove unsupported ``transparent_schema_rules`` option from docs (`#1264`_)
- Bump (and pin) Wekzeug to 0.15.4 (`#1267`_)
- Quickstart: a better ``MONGO_AUTH_SOURCE`` explanation (`#1168`_)

Breaking Changes
~~~~~~~~~~~~~~~~

No known breaking changes for the standard framework user. However, if you are
consuming the developer API:

- Be aware that ``io.base.DataLayer.find()`` signature has changed and an
  optional ``perform_count`` argument has been added. The method return value
  is now a tuple ``(cursor, count)``; ``cursor`` is the query result as
  before while ``count`` is the document count, which is expected to have a
  consistent value when ``perform_count = True``.

.. _`#1271`: https://github.com/pyeve/eve/issues/1271
.. _`#1268`: https://github.com/pyeve/eve/issues/1268
.. _`#1168`: https://github.com/pyeve/eve/issues/1168
.. _`#1266`: https://github.com/pyeve/eve/pull/1266
.. _`#1234`: https://github.com/pyeve/eve/issues/1234
.. _`#1267`: https://github.com/pyeve/eve/issues/1267
.. _`#1263`: https://github.com/pyeve/eve/pull/1263
.. _`#1264`: https://github.com/pyeve/eve/issues/1264

Version 0.9
-----------

Released on April 11, 2019.

Breaking changes
~~~~~~~~~~~~~~~~
- Werkzeug v0.15.1+ is required. You want to upgrade, otherwise your Eve
  environment is likely to break. For the full story, see `#1245`_ and
  `#1251`_.

New
~~~
- HATEOAS support added to aggregation results (`#1208`_)
- ``on_fetched_diffs`` event hooks (`#1224`_)
- Support for Mongo 3.6+ ``$expr`` query operator.
- Support for Mongo 3.6+ ``$center`` query operator.

Fixed
~~~~~
- Insertion failure when replacing unknown field with dbref value (`#1255`_,
  `#1257`_)
- ``max_results=1`` should be honored on aggregation endpoints (`#1250`_)
- PATCH incorrectly normalizes default values in subdocuments (`#1234`_)
- Unauthorized Exception not working with Werkzeug >= 15.0 (`#1245`_, `#1251`_)
- Embedded documents not being sorted correctly (`#1217`_)
- Eve crashes on malformed sort parameters (`#1248`_)
- Insertion failure when replacing a same document containing dbref (`#1216`_)
- Datasource projection is not respected for POST requests (`#1189`_)
- Soft delete removes ``auth_field`` from document (`#1188`_)
- On Mongo 3.6+, we don't return 400 'immutable field' on PATCH and PUT
  (`#1243`_)
- Expecting JSON response for rate limit exceeded scenario (`#1227`_)
- Multiple concurrent patches to the same record, from different processes,
  should result in at least one patch failing with a 412 error (Precondition
  Failed) (`#1231`_)
- Embedding only does not follow ``data_relation.field`` (`#1069`_)
- HATEOAS ``_links`` seems to get an extra ``&version=diffs`` (`#1228`_)
- Do not alter ETag when performing an oplog_push (`#1206`_)
- CORS response headers missing for media endpoint (`#1197`_)
- Warning: Unexpected keys present on black: ``python_version`` (`#1244`_)
- UserWarning: JSON setting is deprecated. Use RENDERERS instead (`#1241`_).
- DeprecationWarning: decodestring is deprecated, use decodebytes (`#1242`_)
- DeprecationWarning: count is deprecated. Use Collection.count_documents
  instead (`#1202`_)
- Documentation typos (`#1218`_, `#1240`_)

Improved
~~~~~~~~
- Eve package is now distributed as a Python wheel (`#1260`_)
- Bump Werkzeug version to v0.15.1+ (`#1245`_, `#1251`_)
- Bump PyMongo version to v3.7+ (`#1202`_)
- Python 3.7 added to the CI matrix (`#1199`_)
- Option to omit the aggregation stage when its parameter is empty/unset
  (`#1209`_)
- HATEOAS: now the ``_links`` dictionary may have a ``related`` dictionary
  inside, and each key-value pair yields the related links for a data relation
  field (`#1204`_)
- XML renderer now supports data field tag attributes such as ``href`` and
  ``title`` (`#1204`_)
- Make the parsing of ``req.sort`` and ``req.where`` easily reusable by moving
  their logic to dedicated methods (`#1194`_)
- Add a "Python 3 is highly preferred" note on the homepage (`#1198`_)
- Drop sphinx-contrib-embedly when building docs.

.. _`#1260`: https://github.com/pyeve/eve/issues/1260
.. _`#1208`: https://github.com/pyeve/eve/issues/1208
.. _`#1257`: https://github.com/pyeve/eve/issues/1257
.. _`#1255`: https://github.com/pyeve/eve/issues/1255
.. _`#1250`: https://github.com/pyeve/eve/issues/1250
.. _`#1234`: https://github.com/pyeve/eve/issues/1234
.. _`#1251`: https://github.com/pyeve/eve/pull/1251
.. _`#1245`: https://github.com/pyeve/eve/pull/1245
.. _`#1217`: https://github.com/pyeve/eve/pull/1217
.. _`#1248`: https://github.com/pyeve/eve/issues/1248
.. _`#1234`: https://github.com/pyeve/eve/issues/1234
.. _`#1216`: https://github.com/pyeve/eve/issues/1216
.. _`#1244`: https://github.com/pyeve/eve/issues/1244
.. _`#1189`: https://github.com/pyeve/eve/issues/1189
.. _`#1188`: https://github.com/pyeve/eve/issues/1188
.. _`#1198`: https://github.com/pyeve/eve/issues/1198
.. _`#1199`: https://github.com/pyeve/eve/issues/1199
.. _`#1243`: https://github.com/pyeve/eve/issues/1243
.. _`#1241`: https://github.com/pyeve/eve/issues/1241
.. _`#1242`: https://github.com/pyeve/eve/issues/1242
.. _`#1202`: https://github.com/pyeve/eve/issues/1202
.. _`#1240`: https://github.com/pyeve/eve/issues/1240
.. _`#1227`: https://github.com/pyeve/eve/issues/1227
.. _`#1231`: https://github.com/pyeve/eve/issues/1231
.. _`#1069`: https://github.com/pyeve/eve/issues/1069
.. _`#1224`: https://github.com/pyeve/eve/pull/1224
.. _`#1228`: https://github.com/pyeve/eve/pull/1228
.. _`#1218`: https://github.com/pyeve/eve/pull/1218
.. _`#1209`: https://github.com/pyeve/eve/issues/1209
.. _`#1206`: https://github.com/pyeve/eve/issues/1206
.. _`#1204`: https://github.com/pyeve/eve/pull/1204
.. _`#1194`: https://github.com/pyeve/eve/pull/1194
.. _`#1197`: https://github.com/pyeve/eve/issues/1197

Version 0.8.1
-------------

Released on October 4, 2018.

New
~~~
- Add support for Mongo ``$centerSphere`` query operator (`#1181`_)
- ``NORMALIZE_DOTTED_FIELDS``. If ``True``, dotted fields are parsed and
  processed as subdocument fields. If ``False``, dotted fields are left
  unparsed and unprocessed and the payload is passed to the underlying
  data-layer as-is. Please note that with the default Mongo layer, setting this
  to ``False`` will result in an error. Defaults to ``True``. (`#1173`_)
- ``normalize_dotted_fields``. Endpoint-level override
  for ``NORMALIZE_DOTTED_FIELDS``. (`#1173`_)

Fixed
~~~~~
- ``mongo_indexes``: "OperationFailure" when changing the keys of an existing
  index (`#1180`_)
- v0.8: "OperationFailure" performing MongoDB full text searches (`#1176`_)
- "AttributeError" on Python 2.7 when obsolete ``JSON`` or ``XML`` settings
  are used (`#1175`_).
- "TypeError argument of type 'NoneType' is not iterable" error when using
  document embedding in conjuction with soft deletes (`#1120`_)
- ``allow_unknown`` validation rule fails with nested dict fields (`#1163`_)
- Updating a field with a nullable data relation fails when value is null
  (`#1159`_)
- "cerberus.schema.SchemaError" when ``VALIDATE_FILTERS = True``. (`#1154`_)
- Serializers fails when array of types is in schema. (`#1112`_)
- Replace the broken ``make audit`` shortcut with ``make check``, add the
  command to ``CONTRIBUTING.rst`` it was missing.  (`#1144`_)

Improved
~~~~~~~~
- Perform lint checks and fixes on staged files, as a pre-commit hook.
  (`#1157`_)
- On CI, perform linting checks first. If linting checks are successful,
  execute the test suite on the whole matrix. (`#1156`_)
- Reformat code to match Black code-style. (`#1155`_)
- Use ``simplejson`` everywhere in the codebase. (`#1148`_)
- Install a bot that flags and closes stale issues/pull requests. (`#1145`_)
- Only set the package version in ``__init__.py``. (`#1142`_)

Docs
~~~~
- Typos (`#1183`_, `#1184`_, `#1185`_)
- Add ``MONGO_AUTH_SOURCE`` to Quickstart. (`#1168`_)
- Fix Sphinx-embedly error when embedding speakerdeck.com slide deck (`#1158`_)
- Fix broken link to the Postman app. (`#1150`_)
- Update obsolete PyPI link in docs sidebar. (`#1152`_)
- Only display the version number on the docs homepage. (`#1151`_)
- Fix documentation builds on Read the Docs. (`#1147`_)
- Add a ``ISSUE_TEMPLATE.md`` GitHub template file. (`#1146`_)
- Improve changelog format to reduce noise and increase readability. (`#1143`_)

.. _`#1185`: https://github.com/pyeve/eve/pull/1185
.. _`#1184`: https://github.com/pyeve/eve/pull/1184
.. _`#1183`: https://github.com/pyeve/eve/pull/1183
.. _`#1181`: https://github.com/pyeve/eve/issues/1181
.. _`#1180`: https://github.com/pyeve/eve/issues/1180
.. _`#1176`: https://github.com/pyeve/eve/issues/1176
.. _`#1175`: https://github.com/pyeve/eve/issues/1175
.. _`#1173`: https://github.com/pyeve/eve/issues/1173
.. _`#1168`: https://github.com/pyeve/eve/issues/1168
.. _`#1142`: https://github.com/pyeve/eve/issues/1142
.. _`#1143`: https://github.com/pyeve/eve/issues/1143
.. _`#1144`: https://github.com/pyeve/eve/issues/1144
.. _`#1145`: https://github.com/pyeve/eve/issues/1145
.. _`#1146`: https://github.com/pyeve/eve/issues/1146
.. _`#1147`: https://github.com/pyeve/eve/issues/1147
.. _`#1148`: https://github.com/pyeve/eve/issues/1148
.. _`#1151`: https://github.com/pyeve/eve/issues/1151
.. _`#1152`: https://github.com/pyeve/eve/issues/1152
.. _`#1150`: https://github.com/pyeve/eve/issues/1150
.. _`#1112`: https://github.com/pyeve/eve/issues/1112
.. _`#1154`: https://github.com/pyeve/eve/issues/1154
.. _`#1155`: https://github.com/pyeve/eve/issues/1155
.. _`#1156`: https://github.com/pyeve/eve/issues/1156
.. _`#1157`: https://github.com/pyeve/eve/issues/1157
.. _`#1158`: https://github.com/pyeve/eve/issues/1158
.. _`#1159`: https://github.com/pyeve/eve/issues/1159
.. _`#1163`: https://github.com/pyeve/eve/issues/1163
.. _`#1120`: https://github.com/pyeve/eve/issues/1120

Version 0.8
-----------

Released on May 10, 2018.

.. note::

    Make sure you read the :ref:`Breaking Changes <breaking_changes>` section below.

- New: support for `partial media requests`_. Clients can request partial file
  downloads by adding a ``Range`` header to their media request (`#1050`_).
- New: `Renderer classes`_. ``RENDERER`` allows to change enabled renderers.
  Defaults to ``['eve.render.JSONRenderer', 'eve.render.XMLRenderer']``. You
  can create your own renderer by subclassing ``eve.render.Renderer``. Each
  renderer should set valid mime attr and have ``.render()`` method
  implemented. Please note that at least one renderer must always be enabled
  (`#1092`_).
- New: ``on_delete_resource_originals`` fired when soft deletion occurs
  (`#1030`_).
- New: ``before_aggregation`` and ``after_aggregation`` event hooks allow to
  attach `custom callbacks to aggregation endpoints`_ (`#1057`_).
- New: ``JSON_REQUEST_CONTENT_TYPES`` or supported JSON content types. Useful
  when you need support for vendor-specific json types. Please note: responses
  will still carry the standard ``application/json`` type. Defaults to
  ``['application/json']`` (`#1024`_).
- New: when the media endpoint is enabled, the default authentication class
  will be used to secure  it. (`#1083`_; `#1049`_).
- New: ``MERGE_NESTED_DOCUMENTS``. If ``True``, updates to nested fields are
  merged with the current data on ``PATCH``. If ``False``, the updates
  overwrite the current data. Defaults to ``True`` (`#1140`_).
- New: support for MongoDB decimal type ``bson.decimal128.Decimal128``
  (`#1045`_).
- New: Support for ``Feature`` and ``FeatureCollection`` GeoJSON objects
  (`#769`_).
- New: Add support for MongoDB ``$box`` geo query operator (`#1122`_).
- New: ``ALLOW_CUSTOM_FIELDS_IN_GEOJSON`` allows custom fields in GeoJSON
  (`#1004`_).
- New: Add support for MongoDB ``$caseSensitive`` and ``$diactricSensitive``
  query operators (`#1126`_).
- New: Add support for MongoDB bitwise query operators ``$bitsAllClear``,
  ``$bitsAllSet``, ``$bitsAnyClear``, ``$bitsAnySet`` (`#1053`_).
- New: support for ``MONGO_AUTH_MECHANISM`` and
  ``MONGO_AUTH_MECHANISM_PROPERTIES``.
- New: ``MONGO_DBNAME`` can now be used in conjuction with ``MONGO_URI``.
  Previously, if ``MONGO_URI`` was missing the database name, an exception
  would be rised (`#1037`_).
- Fix: OPLOG skipped even if ``OPLOG = True`` (`#1074`_).
- Fix: Cannot define default projection and request specific field. (`#1036`_).
- Fix: ``VALIDATE_FILTERS`` and ``ALLOWED_FILTERS`` do not work with
  sub-document fields. (`#1123`_).
- Fix: Aggregation query parameter does not replace keys in the lists
  (`#1025`_).
- Fix: serialization bug that randomly skips fields if "x_of" is encountered
  (`#1042`_)
- Fix: PUT behavior with User Restricted Resource Access. Ensure that, under
  every circumstance, users are unable to overwrite items owned by other users
  (`#1130`_).
- Fix: Crash with Cerberus 1.2 (`#1137`_).
- Fix documentation typos (`#1114`_, `#1102`_)
- Fix: broken documentation links to Cerberus validation rules.
- Fix: add sphinxcontrib-embedly to dev-requirements.txt.
- Fix: Removed OrderedDict dependency; use ``OrderedDict`` from
  ``backport_collections`` instead (`#1070`_).
- Performance improved on retrieving a list of embedded documents (`#1029`_).
- Dev: Refactor index creation. We now have a new
  ``eve.io.mongo.ensure_mongo_indexes()`` function which ensures that eventual
  ``mongo_indexes`` defined for a resource are created on the active database.
  The function can be imported and invoked, for example in multi-db workflows
  where a db is activated based on the authenticated user performing the
  request (via custom auth classes).
- Dev: Add a `Makefile with shortcuts`_ for testing, docs building, and
  development install.
- Dev: Switch to pytest as the standard testing tool.
- Dev: Drop ``requiments.txt`` and ``dev-requirements.txt``. Use ``pip install
  -e .[dev|tests|docs]`` instead.
- Tests: finally acknowledge the existence of modern APIs for both Mongo and
  Python (get rid of most deprecation warnings).
- Change: Support for Cerberus 1.0+ (`#776`_).
- Change: ``JSON`` and ``XML`` settings are deprecated and will be removed in
  a future update. Use ``RENDERERS`` instead (`#1092`_).
- Flask dependency set to >=1.0 (`#1111`_).
- PyMongo dependency set to >=3.5.
- Events dependency set to >=v0.3.
- Drop Flask-PyMongo dependency, use custom code instead (`#855`_).
- Docs: Comprehensive rewrite of the `How to contribute`_ page.
- Docs: Drop the testing page; merge its contents with `How to contribute`_.
- Docs: Add link to the `Eve course`_. It was authored by the project author,
  and it is hosted by TalkPython Training.
- Docs: code snippets are now Python 3 compatibile (Pahaz Blinov).
- Dev: Delete and cleanup of some unnecessary code.
- Dev: after the latest update (May 4th) travis-ci would not run tests on
  Python 2.6.
- Dev: all branches are now tested on travis-ci. Previously, only 'master' was
  being tested.
- Dev: fix insidious bug in ``tests.methods.post.TestPost`` class.

.. _breaking_changes:

Breaking Changes
~~~~~~~~~~~~~~~~
- Python 2.6 and Python 3.3 are no longer supported (`#1129`_).
- Eve now relies on `Cerberus`_ 1.1+  (`#776`_). It allows for many new
  powerful validation and trasformation features (like `schema registries`_),
  improved performance and, in general, a more streamlined API. It also brings
  some notable breaking changes.

    - ``keyschema`` was renamed to ``valueschema``, and ``propertyschema`` to
      ``keyschema``.
    - A PATCH on a document which misses a field having a default value will
      now result in setting this value, even if the field was not provided in
      the PATCH's payload.
    - Error messages for ``keyschema`` are now returned as dictionary. Example:
      ``{'a_dict': {'a_field': "value does not match regex '[a-z]+'"}}``.
    - Error messages for type validations are `different now`_.
    - It is no longer valid to have a field with ``default = None`` and
      ``nullable = False`` (see
      *patch.py:test_patch_nested_document_nullable_missing*).
    - And more. A complete list of breaking changes  is available here_. For
      detailed upgrade instructions, see Cerberus `upgrade notes`_. An in-depth
      analysis of changes made to the codebase (useful if you wrote a custom
      validator which needs to be upgraded) is available with `this commit
      message`_.
    - Special thanks to Dominik Kellner and Brad P. Crochet for the amazing job
      done on this upgrade.

- Config setting ``MONGO_AUTHDBNAME`` renamed into ``MONGO_AUTH_SOURCE`` for
  naming consistency with PyMongo.
- Config options ``MONGO_MAX_POOL_SIZE``, ``MONGO_SOCKET_TIMEOUT_MS``,
  ``MONGO_CONNECT_TIMEOUT_MS``, ``MONGO_REPLICA_SET``,
  ``MONGO_READ_PREFERENCE`` removed. Use ``MONGO_OPTIONS`` or ``MONGO_URI``
  instead.
- Be aware that ``DELETE`` on sub-resource endpoint will now only delete the
  documents matching endpoint semantics. A delete operation on
  ``people/51f63e0838345b6dcd7eabff/invoices`` will delete all documents
  matching the followig query: ``{'contact_id': '51f63e0838345b6dcd7eabff'}``
  (`#1010`_).

.. _#1140: https://github.com/pyeve/eve/pull/1140
.. _#1111: https://github.com/pyeve/eve/issues/1111
.. _#1129: https://github.com/pyeve/eve/issues/1129
.. _#1057: https://github.com/pyeve/eve/issues/1057
.. _#1137: https://github.com/pyeve/eve/issues/1137
.. _#1122: https://github.com/pyeve/eve/issues/1122
.. _#1050: https://github.com/pyeve/eve/pull/1050
.. _#1130: https://github.com/pyeve/eve/pull/1130
.. _#1074: https://github.com/pyeve/eve/issues/1074
.. _#1036: https://github.com/pyeve/eve/issues/1036
.. _#1128: https://github.com/pyeve/eve/pull/1128
.. _#1126: https://github.com/pyeve/eve/pull/1126
.. _#1123: https://github.com/pyeve/eve/issues/1123
.. _#1102: https://github.com/pyeve/eve/pull/1102
.. _#1114: https://github.com/pyeve/eve/pull/1114
.. _#1092: https://github.com/pyeve/eve/pull/1092
.. _#1083: https://github.com/pyeve/eve/issues/1083
.. _#1049: https://github.com/pyeve/eve/issues/1049
.. _#1053: https://github.com/pyeve/eve/issues/1053
.. _#1070: https://github.com/pyeve/eve/pull/1070
.. _#1045: https://github.com/pyeve/eve/issues/1045
.. _#1042: https://github.com/pyeve/eve/pull/1042
.. _#1030: https://github.com/pyeve/eve/pull/1030
.. _#1037: https://github.com/pyeve/eve/issues/1037
.. _#1029: https://github.com/pyeve/eve/issues/1029
.. _#1024: https://github.com/pyeve/eve/issues/1024
.. _#769: https://github.com/pyeve/eve/issues/769
.. _#1004: https://github.com/pyeve/eve/issues/1004
.. _#776: https://github.com/pyeve/eve/issues/776
.. _#855: https://github.com/pyeve/eve/issues/855
.. _#1010: https://github.com/pyeve/eve/issues/1010
.. _#1025: https://github.com/pyeve/eve/issues/1025
.. _Cerberus: http://python-cerberus.org
.. _`schema registries`: http://docs.python-cerberus.org/en/stable/schemas.html#registries
.. _`different now`: http://docs.python-cerberus.org/en/stable/upgrading.html#data-types
.. _here: http://docs.python-cerberus.org/en/stable/changelog.html#breaking-changes
.. _`upgrade notes`: http://python-cerberus.org/en/stable/upgrading.html
.. _`this commit message`: https://github.com/pyeve/eve/pull/1001/commits/1110f807b478efa9f13ad1d217d22ceaa2a9e42d
.. _`partial media requests`: http://python-eve.org/features.html#partial-media-downloads
.. _`custom callbacks to aggregation endpoints`: http://python-eve.org/features.html#aggregation-event-hooks
.. _`Renderer classes`: http://python-eve.org/features.html#rendering
.. _`makefile with shortcuts`: http://python-eve.org/contributing.html#make-targets
.. _`How to contribute`: http://python-eve.org/contributing.html
.. _`Eve course`: https://training.talkpython.fm/courses/explore_eve/eve-building-restful-mongodb-backed-apis-course

Version 0.7.10
~~~~~~~~~~~~~~

Released on July 15, 2018.

- Fix: Pin Flask-PyMongo dependency to avoid crash with Flask-PyMongo 2.
  Closes #1172.

Version 0.7.9
~~~~~~~~~~~~~

Released on May 10, 2018

- Python 2.6 and Python 3.3 are deprecated. Closes #1129.

Version 0.7.8
~~~~~~~~~~~~~

Released on 7 February, 2018

- Fix: breaking syntax error in v0.7.7

Version 0.7.7
~~~~~~~~~~~~~

Released on 7 February, 2018

- Fix: geo queries now properly support ``$geometry`` and ``$maxDistance``
  operators. Closes #1103.

Version 0.7.6
~~~~~~~~~~~~~

Released on 14 January, 2018

- Improve query parsing robustness.

Version 0.7.5
~~~~~~~~~~~~~

Released on 4 December, 2017

- Fix: A query was not fully traversed in the sanitization. Therefore the
  blacklist for mongo wueries could be bypassed, allowing for dangerous
  ``$where`` queries (Moritz Schneider).

Version 0.7.4
~~~~~~~~~~~~~

Released on 24 May, 2017

- Fix: ``post_internal`` fails when using ``URL_PREFIX`` or ``API_VERSION``.
  Closes #810.

Version 0.7.3
~~~~~~~~~~~~~

Released on 3 May, 2017

- Eve and Cerberus are now collaboratively funded projects, see:
  https://nicolaiarocci.com/eve-and-cerberus-funding-campaign/
- Fix: Internal resource, oplog enabled: a ``*_internal`` method defined in
  ``OPLOG_METHODS`` triggers keyerror (Einar Huseby).
- Dev: use official Alabaster theme instead of custom fork.
- Fix: docstrings typos (Martin Fous).
- Docs: explain that ``ALLOW_UNKNOWN`` can also be used to expose the whole
  document as found in the database, with no explicit validation schema.
  Addresses #995.
- Docs: add Eve-Healthcheck to extensions list (Luis Fernando Gomes).

Version 0.7.2
~~~~~~~~~~~~~

Released on 6 March, 2017

- Fix: Validation exceptions are returned in ``doc_issues['validator
  exception']`` across all edit methods (POST, PUT, PATCH). Closes #994.
- Fix: When there is ``MONGO_URI`` defined it will be used no matter if the
  resource is using a prefix or not (Petr Jašek).
- Docs: Add code snippet with an example of how to implement a simple list of
  items that supports both list-level and item-level CRUD operations (John
  Chang).

Version 0.7.1
~~~~~~~~~~~~~

Released on 14 February, 2017

- Fix: "Cannot create a consistent method resolution order" on Python 3.5.2 and
  3.6 since Eve 0.7. Closes #984.

- Docs: update README with svg bade (Sobolev Nikita).
- Docs: fix typo and dead link to Nicola's website (Dominik Kellner).

- ``develop`` branch has been dropped. ``master`` is now the default project
  branch.

Version 0.7
~~~~~~~~~~~

Released on 6 February, 2017

- New: Add Python 3.6 as a supported interpreter.

- New: ``OPTIMIZE_PAGINATION_FOR_SPEED``. Set this to ``True`` to improve
  pagination performance. When optimization is active no count operation, which
  can be slow on large collections, is performed on the database. This does
  have a few consequences. Firstly, no document count is returned. Secondly,
  ``HATEOAS`` is less accurate: no last page link is available, and next page
  link is always included, even on last page. On big collections, switching
  this feature on can greatly improve performance. Defaults to ``False``
  (slower performance; document count included; accurate ``HATEOAS``). Closes
  #944 and #853.


- New: ``Location`` header is returned on ``201 Created`` POST responses. If
  will contain the URI to the created document. If bulk inserts are enabled,
  only the first document URI is returned. Closes #795.

- New: Pretty printing.You can pretty print the response by specifying a query
  parameter named ``?pretty`` (Hasan Pekdemir).

- New: ``AUTO_COLLAPSE_MULTI_KEYS``. If set to ``True``, multiple values sent
  with the same key, submitted using the ``application/x-www-form-urlencoded``
  or ``multipart/form-data`` content types, will automatically be converted to
  a list of values. When using this together with ``AUTO_CREATE_LISTS`` it
  becomes possible to use lists of media fields. Defaults to ``False``. Closes
  #932 (Conrad Burchert).

- New: ``AUTO_CREATE_LISTS``. When submitting a non ``list`` type value for
  a field with type ``list``, automatically create a one element list before
  running the validators. Defaults to ``False`` (Conrad Burchert).

- New: Flask-PyMongo compatibility for for ``MONGO_CONNECT`` config setting
  (Massimo Scamarcia).

- New: Add Python 3.5 as a supported interpreter (Mattias Lundberg).

- New: ``MONGO_OPTIONS`` allows MongoDB arguments to be passed to the
  MongoClient object. Defaults to ``{}`` (Massimo Scamarcia).

- New: Regexes are allowed by setting ``X_DOMAINS_RE`` values. This allows CORS
  to support websites with dynamic ranges of subdomains. Closes #660 and #974.

- New: If ``ENFORCE_IF_MATCH`` option is active, then all requests are expected
  to include the ``If-Match`` or they will be rejected (same as old behavior).
  However, if ``ENFORCE_IF_MATCH`` is disabled, then client determines whether
  request is conditional. When ``If-Match`` is included, then request is
  conditional, otherwise the request is processed with no conditional checks.
  Closes #657 (Arthur Burkart).

- New: Allow old document versions to be cache validated using ETags (Nick
  Park).

- New: Support weak ETags, commonly applied by servers transmitting gzipped
  content (Nick Park).

- New: ``on_oplog_push`` event is fired when OPLOG is about to be updated.
  Callbacks receive two arguments: ``resource`` (resource name) and ``entries``
  (list of oplog entries which are about to be written).

- New: optional ``extra`` field is available for OPLOG entries. Can be updated
  by callbacks hooked to the new ``on_oplog_push`` event.

- New: OPLOG audit now include the username or token when available. Closes
  #846.

- New ``get_internal`` and ``getitem_internal`` functions can be used for
  internal GET calls. These methods are not rate limited, authentication is not
  checked and pre-request events are not raised.

- New: Add support for MongoDB ``DBRef`` fields (Roman Gavrilov).

- New: ``MULTIPART_FORM_FIELDS_AS_JSON``. In case you are submitting your
  resource as ``multipart/form-data`` all form data fields will be submitted as
  strings, breaking any validation rules you might have on the resource fields.
  If you want to treat all submitted form data as JSON strings you will have to
  activate this setting. Closes #806 (Stratos Gerakakis).

- New: Support for MongoDB Aggregation Framework. Endpoints can respond with
  aggregation results. Clients can optionally influence aggregation
  results by using the new ``aggregate`` option: ``aggregate={"$year": 2015}``.

- New: Flask views (``@app.route``) can now set ``mongo_prefix`` via Flask's
  ``g`` object: ``g.mongo_prefix = 'MONGO2'`` (Gustavo Vargas).

- New: Query parameters not recognised by Eve are now returned in HATEOAS URLs
  (Mugur Rus).

- New: ``OPLOG_CHANGE_METHODS`` is a list of HTTP methods which operations will
  include changes into the OpLog (mmizotin).

- Change: Return ``428 Precondition Required`` instead of a generic ``403
  Forbidden`` when the ``If-Match`` request header is missing (Arnau Orriols).

- Change: ETag response header now conforms to RFC 7232/2.3 and is surrounded
  by double quotes. Closes #794.

- Fix: Better locating of ``settings.py``. On startup, if settings flag is
  omitted in constructor, Eve will try to locate file named settings.py, first
  in the application folder and then in one of the application's subfolders.
  You can choose an alternative filename/path, just pass it as an argument when
  you instantiate the application. If the file path is relative, Eve will try
  to locate it recursively in one of the folders in your sys.path, therefore
  you have to be sure that your application root is appended to it. This is
  useful, for example, in testing environments, when settings file is not
  necessarily located in the root of your application. Closes #820 (Mario
  Kralj).

- Fix: Versioning does not work with User Restricted Resource Access. Closes
  #967 (Kris Lambrechts)

- Fix: ``test_create_indexes()`` typo. Closes 960.

- Fix: fix crash when attempting to modify a document ``_id`` on MongoDB 3.4
  (Giorgos Margaritis)

- Fix: improve serialization of boolean values. Closes #947 (NotSpecial).

- Fix: fix intermittently failing test. Closes #934 (Conrad Burchert).

- Fix: Multiple, fast (within a 1 second window) and neutral (no actual
  changes) PATCH requests should not raise ``412 Precondition Failed``.
  Closes #920.

- Fix: Resource titles are not properly escaped during the XML rendering of the
  root document (Kris Lambrechts).

- Fix: ETag request headers which conform to RFC 7232/2.3 (double quoted value)
  are now properly processed. Addresses #794.

- Fix: Deprecation warning from Flask. Closes #898 (George Lestaris).

- Fix: add Support serialization on lists using anyof, oneof, allof, noneof.
  Closes #876 (Carles Bruguera).

- Fix: update security example snippets to match with current API (Stanislav
  Filin).

- Fix: ``notifications.py`` example snippet crashes due to lack of ``DOMAIN``
  setting (Stanislav Filin).

- Docs: clarify documentation for custom validators: Cerberus dependency is
  still pinned to version 0.9.2. Upgrade to Cerberus 1.0+ is planned with v0.8.
  Closes #796.
- Docs: remove the deprecated ``--ditribute`` virtualenv option (Eugene
  Prikazchikov).
- Docs: add date and subdocument fields filtering examples. Closes #924.
- Docs: add Eve-Neo4j to the extensions page (Rodrigo Rodriguez).
- Docs: stress that alternate backends are supported via community extensions.
- Docs: clarify that Redis is an optional dependency (Mateusz Łoskot).

- Update license to 2017. Closes #955.
- Update: Flask 0.12. Closes #945, #904 and #963.
- Update: PyMongo 3.4 is now required. Closes #964.

Version 0.6.4
~~~~~~~~~~~~~

Released on 8 June, 2016

- Fix: Cannot serialize data when a field that has a ``valueschema`` that is of
  ``dict`` type. Closes #874.
- Fix: Authorization header bearer tokens not parsed correctly. Closes #866
  (James Stewart).
- Fix: TokenAuth prevents base64 decoding of Tokens. Closes #840.
- Fix: If datasource source is specified no fields are included by default.
  Closes #842.

- Docs: streamline Quickstart guide. Closes #868.
- Docs: fix broken link in Installation page. Closes #861.
- Docs: Resource configuration doesn't mention ``versioning`` override. Closes
  #845.

Version 0.6.3
~~~~~~~~~~~~~

Released on 16 March, 2016

- Fix: Since 0.6.2, static projections are not honoured. Closes #837.


Version 0.6.2
~~~~~~~~~~~~~

Released on 14 March, 2016

- Fix: ``Access-Control-Allow-Max-Age`` should actually be
  ``Access-Control-Max-Age``. Closes #829.
- Fix: ``unique`` validation rule is checked against soft deleted documents.
  Closes #831.
- Fix: Mongo does not allow ``$`` and ``.`` in field names. Apply this
  validation in schemas and dict fields. Closes #780.
- Fix: Remove "ensure uniqueness of (custom) id fields" feature. Addresses
  #788.
- Fix: ``409 Conflict`` not reported since upgrading to PyMongo 3. Closes #680.
- Fix: when a document is soft deleted, the OPLOG `_updated` field is not the
  time of the deletion but the time of the previous last update (Cyril
  Bonnard).
- Fix: TokenAuth. When the tokens are passed as "Authorization: " or
  "Authorization: Token " headers, werkzeug does not recognize them as valid
  authorization header, therefore the ``request.authorization`` field is empty
  (Luca Di Gaspero).
- Fix: ``SCHEMA_ENDPOINT`` does not work when schema has lambda function as
  ``coerce`` rule. Closes #790.
- Fix: CORS pre-flight requests malfunction on ``SCHEMA_ENDPOINT`` endpoint
  (Valerie Coffman).
- Fix: do not attempt to parse ``number`` values as strings when they are
  numerical (Nick Park).
- Fix: the ``__init__.py`` ``ITEM_URL`` does not match default_settings.py.
  Closes #786 (Ralph Smith).
- Fix: startup crash when both ``SOFT_DELETE`` and ``ALLOW_UNKNOWN`` are
  enabled. Closes #800.
- Fix: Serialize inside ``of`` and ``of_type`` rules new in Cerberus 0.9.
  Closes #692 (Arnau Orriols).
- Fix: In ``put_internal`` Validator is not set when ``skip_validation`` is
  ``true`` (Wei Guan).
- Fix: In ``patch_internal`` Validator is not set when ``skip_validation`` is
  ``true`` (Stratos Gerakakis).
- Fix: Add missing serializer for fields of type ``number`` (Arnau Orriols).
- Fix: Skip any null value from serialization (Arnau Orriols).
- Fix: When ``SOFT_DELETE`` is active an exclusive ``datasource.projection``
  causes a ``500`` error. Closes #752.

- Update: PyMongo 3.2 is now required.
- Update: Flask-PyMongo 0.4+ is now required.
- Update: Werkzeug up to 0.11.4 is now required
- Change: simplejson v3.8.2 is now required.

- Docs: fix some typos (Manquer, Patrick Decat).
- Docs: add missing imports to authentication docs (Hamdy)
- Update license to 2016 (Prayag Verma)

Version 0.6.1
~~~~~~~~~~~~~

Released on 29 October, 2015

- New: ``BULK_ENABLED`` enables/disables bulk insert. Defaults to ``True``
  (Julian Hille).
- New: ``VALIDATE_FILTERS`` enables/disables validating of query filters
  against resource schema. Closes #728 (Stratos Gerakakis).
- New: ``TRANSPARENT_SCHEMA_RULES`` enables/disables schema validation globally
  and ``transparent_schema_rules`` per resource (Florian Rathgeber).
- New: ``ALLOW_OVERRIDE_HTTP_METHOD`` enables/disables support for overriding
  request methods with ``X-HTTP-Method-Override`` headers (Julian Hille).

- Fix: flake8 fails on Python 3. Closes #747 (Simon Schönfeld).
- Fix: recursion for dotted field normalization (Matt Tucker).
- Fix: dependendencies on sub-document fields always return 422. Closes #706.
- Fix: invoking ``post_internal`` with ``skpi_validation = True`` causes
  a ``422`` response. Closes #726.
- Fix: explict inclusive datasource projection is ignored. Closes #722.

- Dev: fix rate limiting tests so they don't occasionally fail.
- Dev: make sure connections opened by test suite are properly closed on
  teardown.
- Dev: use middleware to parse overrides and eventually update request method
  (Julian Hille).
- Dev: optimize versioning by building specific versions without deepcopying
  the root document (Nick Park).
- Dev: ``_client_projection`` method has been moved up from the mongo layer to
  the base DataLayer class. It is now available for other data layers
  implementations, such as Eve-SQLAlchemy (Gonéri Le Bouder).

- Docs: add instructions for installing dependencies and building docs (Florian
  Rathgeber).
- Docs: fix link to contributing guidelines (Florian Rathgeber).
- Docs: fix some typos (Stratos Gerakakis, Julian Hille).
- Docs: add Eve-Swagger to Extensions page.
- Docs: fix broken link to Mongo's capped collections (Nathan Reynolds).


Version 0.6
~~~~~~~~~~~

Released on 28 September, 2015

- New: support for embedding simple ObjectId fields: you can now use the
  ``data_relation`` rule on them (Gonéri Le Bouder).
- New: support for multiple layers of embedding (Gonéri Le Bouder).
- New: ``SCHEMA_ENDPOINT`` allows resource schema to be returned from an API
  endpoint (Nick Park).
- New: HATEOAS links can be customized from within callback functions (Magdas
  Adrian).
- New: ``_INFO``: string value to include an info section, with the given INFO
  name, at the Eve homepage (suggested value ``_info``). The info section will
  include Eve server version and API version (API_VERSION, if set).  ``None``
  otherwise, if you do not want to expose any server info. Defaults to ``None``
  (Stratos Gerakakis).
- New: ``id_field`` sets a field used to uniquely identify resource items
  within the database. Locally overrides ``ID_FIELD`` (Dominik Kellner).
- New: ``UPSERT_ON_PUT`` allows document creation on PUT if the document does
  not exist. Defaults to ``True``. See below for details.
- New: PUT attempts to create a document if it does not exist. The URL endpoint
  will be used as ``ID_FIELD`` value (if ``ID_FIELD`` is included with the
  payload, it will be ignored). Normal validation rules apply. The response
  will be a ``201 Created`` on successful creation. Response payload will be
  identical the one you would get by performing a single document POST to the
  resource endpoint. Set ``UPSET_ON_PUT`` to ``False`` to disable this
  behaviour, and get a ``404`` instead.  Closes #634.
- New: POST accepts documents which include ``ID_FIELD`` (``_id``) values. This
  is in addition to the old behaviour of auto-generating ``ID_FIELD`` values
  when the submitted document does not contain it. Please note that, while you
  can add ``ID_FIELD`` to the schema (previously not allowed), you don't really
  have to, unless its type is different from the ``ObjectId`` default. This
  means that in most cases you can start storing ``ID_FIELD``-included
  documents right away, without making any changes.
- New: Log MongoDB and HTTP methods exceptions (Sebastien Estienne).
- New: Enhanced Logging.
- New: ``VALIDATION_ERROR_AS_LIST``. If ``True`` even single field errors will
  be returned in a list. By default single field errors are returned as strings
  while multiple field errors are bundled in a list. If you want to standardize
  the field errors output, set this setting to ``True`` and you will always get
  a list of field issues. Defaults to ``False``. Closes #536.
- New: ``STANDARD_ERRORS`` is a list of HTTP codes that will be served with the
  canonical API response format, which includes a JSON body providing both
  error code and description. Addresses #586.
- New: ``anyof`` validation rule allows you to list multiple sets of rules to
  validate against.
- New: ``alloff`` validation rule, same as ``anyof`` except that all rule
  collections in the list must validate.
- New: ``noneof`` validation rule. Same as ``anyof`` except that it requires no
  rule collections in the list to validate.
- New: ``oneof`` validation rule. Same as ``anyof`` except that only one rule
  collections in the list can validate.
- New: ``valueschema`` validation rules replaces the now deprecated
  ``keyschema`` rule.
- New: ``propertyschema`` is the counterpart to ``valueschema`` that validates
  the keys of a dict.
- New: ``coerce`` validation rule. Type coercion allows you to apply a callable
  to a value before any other validators run.
- New: ``MONGO_AUTHDBNAME`` allows to specify a MongoDB authorization database.
  Defaults to ``None`` (David Wood).
- New: ``remove`` method in Mongo data layer now returns the deletion status or
  ``None`` if write acknowledgement is disabled (Mayur Dhamanwala).
- New: ``unique_to_user`` validation rule allows to validate that a field value
  is unique to the user. Different users can share the same value for the
  field. This is useful when User Restricted Resource Access is enabled on an
  endpoint. If URRA is not active on the endpoint, this rule behaves like
  ``unique``. Closes #646.
- New: ``MEDIA_BASE_URL`` allows to set a custom base URL to be used when
  ``RETURN_MEDIA_AS_URL`` is active (Henrique Barroso).
- New: ``SOFT_DELETE`` enables soft deletes when set to ``True`` (Nick Park.)
- New: ``mongo_indexes`` allows for creation of MongoDB indexes at application
  launch (Pau Freixes.)
- New: clients can opt out of default embedded fields:
  ``?embedded={"author":0}`` would cause the embedded author not to be included
  with response payload. (Tobias Betz.)
- New: CORS: Support for ``X-ALLOW-CREDENTIALS`` (Cyprien Pannier.)
- New: Support for dot notation in POST, PATCH and PUT methods. Be aware that,
  for PATCH and PUT, if dot notation is used even on just one field, the whole
  sub-document will be replaced. So if this document is stored:

  ``{"name": "john", "location": {"city": "New York", "address": "address"}}``

  A PATCH like this:

    ``{"location.city": "Boston"}``

  (which is exactly equivalent to:)

    ``{"location": {"city": "a nested city"}}``

  Will update the document to:

  ``{"name": "john", "location": {"city": "Boston"}}``

- New: JSONP Support (Tim Jacobi.)
- New: Support for multiple MongoDB databases and/or servers.

  - ``mongo_prefix`` resource setting allows overriding of the default
    ``MONGO`` prefix used when retrieving MongoDB settings from configuration.
    For example, set a resource ``mongo_prefix`` to ``MONGO2`` to read/write
    from the database configured with that prefix in your settings file
    (``MONGO2_HOST``, ``MONGO2_DBNAME``, etc.)
  - ``set_mongo_prefix()`` and ``get_mongo_prefix()`` have been added to
    ``BasicAuth`` class and derivates. These can be used to arbitrarily set
    the target database depending on the token/client performing the request.

  Database connections are cached in order to not to loose performance. Also,
  this change only affects the MongoDB engine, so extensions currently
  targetting other databases should not need updates (they will not inherit
  this feature however.)
- New: Enable ``on_pre_GET`` hook for HEAD requests (Daniel Lytkin.).
- New: Add ``X-Total-Count`` header for collection GET/HEAD requests (Daniel
  Lytkin.).
- New: ``RETURN_MEDIA_AS_URL``, ``MEDIA_ENDPOINT`` and ``MEDIA_URL`` allow for
  serving files at a dedicated media endpoint while urls are returned in
  document media fields (Daniel Lytkin.)
- New: ``etag_ignore_fields``. Resource setting with a list of fields belonging
  to the schema that won't be used to compute the ETag value. Defaults to
  ``None`` (Olivier Carrère.)

- Change: when HATEOAS is off the home endpoint will respond with ``200 OK``
  instead of ``404 Not Found`` (Stratos Gerakakis).
- Change: PUT does not return ``404`` if a document URL does not exist. It will
  attempt to create the document instead. Set ``UPSET_ON_PUT`` to ``False`` to
  disable this behaviour and get a ``404`` instead.
- Change: A PATCH including an ``ID_FIELD`` field which value is different than
  the original will get a ``400 Bad Request``, along with an explanation in the
  message body that the field is immutable. Previously, it would get an
  ``unknown field`` validation error.

- Dev: Improve GET perfomance on large versioned documents (Nick Park.)
- Dev: The ``MediaStorage`` base class now accepts the active resource as an
  argument for its methods. This allows data-layers to avoid resorting to the
  Flask request object to determine the active resource. To preserve backward
  compatibility the new ``resource`` argument defaults to ``None`` (Magdas
  Adrian).
- Dev: The Mongo data-layer is not dependant on the Flask request object
  anymore. It will still fallback to it if the ``resource`` argument is
  ``None``. Closes #632. (Magdas Adrian).

- Fix: store versions in the same mongo collection when ``datasource`` is used
  (Magdas Adrian).
- Fix: Update ``serialize`` to gracefully handle non-dictionary values in dict
  type fields (Nick Park).
- Fix: changes to the ``updates`` argument, applied by callbacks hooked to the
  ``on_updated`` event, were not persisted to the database (Magdas Adrian).
  Closes #682.
- Fix: Changes applied to the ``updates`` argument``on_updated`` returns the
  whole updated document. Previously, it was only returning the updates sent
  with the request. Closes #682.
- Fix: Replace the Cerberus rule ``keyschema``, now deprecated, with the new
  ``propertyschema`` (Julian Hille).
- Fix: some error message are not filtered out of debug mode anymore, as they
  are useful for users and do not leak information. Closes #671 (Sebastien
  Estienne).
- Fix: reinforce Content-Type Header handling to avoid possible crash when it
  is missing (Sebastien Estienne).
- Fix: some schema errors were not being reported as SchemaError exceptions.
  A more generic 'DOMAIN missing or wrong' message was returned instead.
- Fix: When versioning is enabled on a resource with a custom ID_FIELD,
  versioning documents will inherit their ID from the versioned document,
  making any update of the document result in a DuplicateKeyError (Matthieu
  Prat).
- Fix: Filter validation fails to validate query selectors that contain a value
  of the list data-type, which is not a list of sub-queries. See #674 (Matthieu
  Prat).
- Fix: ``_validate_dependencies`` always returns ``None``.
- Fix: ``412 Precondition Failed`` does not return a JSON body. Closes #661.
- Fix: ``embedded_fields`` may point on a field that come from another embedded
  document. For example, ``['a.b.c', 'a.b', 'a']`` (Gonéri Le Bouder).
- Fix: add handling of sub-resource resolving for PUT method (Olivier Poitrey).
- Fix: ``dependencies`` rule would mistakenly validate documents when target
  fields happened to also have a ``default`` value.
- Fix: According to RFC2617 the separator should be (=) instead of (:). This
  caused at least Chrome not to prompt user for the credentials, and not to
  send the Authorization header even when credentials were in the url (Samuli
  Tuomola).
- Fix: make sure ``unique`` validation rule is consistent between HTTP methods.
  A field value must be unique within the datasource, regardless of the user
  who created it. Closes #646.
- Fix: OpLog domain entry is not created if ``OPLOG_ENDPOINT`` is ``None``.
  Closes #628.
- Fix: Do not overwrite ``ID_FIELD`` as it is not a sub resource. See #641 for
  details (Olivier Poitrey).
- Fix: ETag computation crash when non-standard json serializers are used
  (Kevin Roy.)
- Fix: Remove duplicate item in Mongo operators list. Closes #619.
- Fix: Versioning: invalidate cache when ``_latest_version`` changes in
  versioned doc (Nick Park.)
- Fix: snippet in account management tutorial (xgddsg.)
- Fix: ``MONGO_REPLICA_SET`` and other significant Flask-PyMongo settings have
  been added to the documentation. Closes #615.
- Fix: Serialization of lists of lists (Nick Park.)
- Fix: Make sure ``original`` is not modified during ``PATCH``. Closes #611
  (Petr Jašek.)
- Fix: Route parameters are applied to new documents before they are validated.
  This ensures that documents with required fields will be populated before
  they are validated. Addresses #354. (Matthew Ellison.)
- Fix: ``GridFSMediaStorage`` does not save filename. Closes #605 (Sam Luu).
- Fix: Reinforce GeoJSON validation (Joakim Uddholm.)
- Fix: Geopoint coordinates do not accept integers. Closes #591 (Joakim
  Uddholm.)
- Fix: OpLog enabled makes PUT return wrong Etag. Closes #590.

- Update: Cerberus 0.9.2 is now required.
- Update: PyMongo 2.8 is now required (which in turn supports MongoDB 3.0)

Version 0.5.3
~~~~~~~~~~~~~

Released on 17 March, 2015.

- Fix: Support for Cerberus 0.8.1.
- Fix: Don't block on first field serialization exception. Closes #568.
- Fix: Ignore read-only fields in ``PUT`` requests when their values aren't
  changed compared to the stored document (Bjorn Andersson.)

- Docs: replace ``file`` with ``media`` type. Closes #566.

Version 0.5.2
~~~~~~~~~~~~~

Released on 23 Feb, 2015.
Codename: 'Giulia'.

- Fix: hardening of database concurrency checks. See #561 (Olivier Carrère.)
- Fix: ``PATCH`` and ``PUT`` do not include Etag header (Marcus Cobden.)
- Fix: endpoint-level authentication crash when a callable is passed. Closes
  #558.
- Fix: serialization of ``keyschema`` fields with ``objetid`` values. Closes
  #525.
- Fix: typos in schema rules might lead to arbitrary payloads being validated
  (Emmanuel Leblond.)
- Fix: ObjectId value in ID field of type string (Jaroslav Semančík.)
- Fix: User Restricted Resource Access does not work with HMAC Auth classes.
- Fix: Crash when ``embedded`` is used on subdocument with a missing field
  (Emmanuel Leblond.)

- Docs: add ``MONGO_URI`` as an alternative to other MongoDB connection
  options. Closes #551.

- Change: Werkzeug 0.10.1 is now required.
- Change: ``DataLayer`` API methods ``update()`` and ``replace()`` have a new
  ``original`` argument.

Version 0.5.1
~~~~~~~~~~~~~

Released on 16 Jan, 2015.

- Fix: dependencies with value checking seem broken (#547.)
- Fix: documentation typo (Marc Abramowitz.)
- Fix: pretty url for regex with a colon in the expression (Magdas Adrian.)

Version 0.5
~~~~~~~~~~~

Released on 12 Jan, 2015.

- New: Operations Log (http://python-eve.org/features#operations-log.)
- New: GeoJSON (http://python-eve.org/features.html#geojson) (Juan Madurga.)
- New: Internal Resources (http://python-eve.org/features#internal-resources) (Magdas Adrian.)
- New: Support for multiple origins when using CORS (Josh Villbrandt, #532.)
- New: Regexes are stripped out of HATEOAS urls when present. You now get
  ``games/<game_id>/images`` where previously you would get
  ``games/<regex('[a-f0-9]{24}'):game_id>/images``). Closes #466.
- New: ``JSON_SORT_KEYS`` enables JSON key sorting (Matt Creenan).
- New: Add the current query string to the self link for responses with
  multiple documents. Closes #464 (Jen Montes).
- New: When document versioning is on, add ``?version=<version_num>`` to
  HATEOAS self links. Also adds pagination links for ``?version=all`` and
  ``?version=diffs`` requests when the number exceeds the max results.
  Partially addresses #475 (Jen Montes).
- New: ``QUERY_WHERE`` allows to set the query parameter key for filters.
  Defaults to ``where``.
- New: ``QUERY_SORT`` allows to set the query parameter key for sorting.
  Defaults to ``sort``.
- New: ``QUERY_PAGE`` allows to set the query parameter key for pagination.
  Defaults to ``page``.
- New: ``QUERY_PROJECTION`` allows to set the query parameter key for
  projections. Defaults to ``projection``.
- New: ``QUERY_MAX_RESULTS`` allows to set the query parameter key for max
  results. Defaults to ``max_results``.
- New: ``QUERY_EMBEDDED`` allows to set the query parameter key embedded
  documents. Defaults to ``embedded``.
- New: Fire ``on_fetched`` events for ``version=all`` requests (Jen Montes).
- New: Support for CORS ``Access-Control-Expose-Headers`` (Christian Henke).
- New: ``post_internal()`` can be used for intenral post calls. This method is
  not rate limited, authentication is not checked and pre-request events are
  not raised (Magdas Adrian).
- New: ``put_internal()`` can be used for intenral PUT calls. This method is
  not rate limited, authentication is not checked and pre-request events are
  not raised (Kevin Funk).
- New: ``patch_internal()`` can be used for intenral PATCH calls. This method
  is not rate limited, authentication is not checked and pre-request events are
  not raised (Kevin Funk).
- New: ``delete_internal()`` can be used for intenral DELETE calls. This method
  is not rate limited, authentication is not checked and pre-request events are
  not raised (Kevin Funk).
- New: Add an option to ``_internal`` methods to skip payload validation
  (Olivier Poitrey).
- New: Comma delimited sort syntax in queries. The MongoDB data layer now also
  supports queries like ``?sort=lastname,-age``. Addresses #443.
- New: Add extra 4xx response codes for proper handling. Only ``405`` Method
  not allowed, ``406`` Not acceptable, ``409`` Conflict, and ``410`` Gone have
  been added to the list (Kurt Doherty).
- New: Add serializers for integer and float types (Grisha K.)
- New: dev-requirements.txt added to the repo.
- New: Embedding of documents by references located in any subdocuments. For
  example, query ``embedded={"user.friends":1}`` will return a document with
  "user" and all his "friends" embedded, but only if ``user`` is a subdocument
  and ``friends`` is a list of references (Dmitry Anoshin).
- New: Allow mongoengine to work properly with cursor counts (Johan Bloemberg)
- New: ``ALLOW_UNKNOWN`` allows unknown fields to be read, not only written as
  before. Closes #397 and #250.
- New: ``VALIDATION_ERROR_STATUS`` allows setting of the HTTP status code to
  use for validation errors. Defaults to ``422`` (Olivier Poitrey).
- New: Support for sub-document projections. Fixes #182 (Olivier Poitrey).
- New: Return ``409 Conflict`` on pymongo ``DuplicateKeyError`` for ``POST``
  requests, as already happens with ``PUT`` requests (Matt Creenan, #537.)

- Change: ``DELETE`` returns ``204 NoContent`` on a successful delete.
- Change: SERVER_NAME removed as it is not needed anymore.
- Change: URL_PROTOCOL removed as it is not needed anymore.
- Change: HATEOAS links are now relative to the API root. Closes #398 #401.
- Change: If-Modified-Since has been disabled on resource (collections)
  endpoints. Same functionality is available with a ``?where={"_udpated":
  {"$gt": "<RFC1123 date>"}}`` request. The OpLog also allows retrieving
  detailed changes happened at any endpoint, deleted documents included.
  Closes #334.
- Change: etags are now persisted with the documents. This ensures that etags
  are consistent across queries, even when projection queries are issued.
  Please note that etags will only be stored along with new documents created
  and/or edited via API methods (POST/PUT/PATCH). Documents inserted by other
  means and those stored with v0.4 and below will keep working as previously:
  their etags will be computed on-the-fly and you will get still be getting
  inconsistent etags when projection queries are issued. Closes #369.
- Change: XML item, meta and link nodes are now ordered. Closes #441.
- Change: ``put`` method signature for ``MediaStorage`` base class has been
  updated. ``filemame`` is now optional. Closes #414.
- Change: CORS behavior to be compatible with browsers (Chrome). Eve is now
  echoing back the contents of the Origin header if said content is whitelisted
  in X_DOMAINS. This also safer as it avoids exposing internal server
  configuration. Closes #408. This commit was carefully handcrafed on a flight
  to EuroPython 2014.
- Change: Specify a range of dependant package versions. #379 (James Stewart).
- Change: Cerberus 0.8 is now required.
- Change: pymongo v2.7.2 is now required.
- Change: simplejson v3.6.5 is now required.
- Change: update ``dev-requirements.txt`` to most recent tools available.

- Fix: add ``README.rst`` to ``MANIFEST.in`` (Niall Donegan.)
- Fix: ``LICENSE`` variable in ``setup.py`` should be "shortstring". Closes
  #540 (Niall Donegan.)
- Fix: ``PATCH`` on fields with original value of ``None`` (Marcus Cobden,
  #534).
- Fix: Fix impossible version ranges in setup.py (Marcus Cobden, #531.)
- Fix: Bug with expanding lists of roles, compromising authorization (Mikael
  Berg, #527)
- Fix: ``PATCH`` on subdocument fields does not overwrite the whole
  subdocument anymore. Closes #519.
- Fix: Added support for validation on field attribute with type list (Jorge
  Morales).
- Fix: Fix a serialization bug with integer and float when value is
  0 (Olivier Poitrey).
- Fix: Custom ID fields tutorial: if custom ID fields are being used, then
  MongoDB/Eve won't be able to create them automatically as it does with the
  `ObjectId` default type. Closes #511.
- Fix: Dependencies with default values were reported as missing if omitted.
  Closes #353.
- Fix: Dependencies always fails on PATCH if dependent field isn't part of
  the update. #363.
- Fix: client projections work when ``allow_unknown`` is active. Closes #497.
- Fix: datasource projections are active when ``allow_unknown`` is active.
  closes #497.
- Fix: Properly serialize nullable floats and integers. Closes #469.
- Fix: ``_mongotize()`` turns non-ObjectId strings (but not unicode) into
  ObjectIds. Closes #508 (Or Neeman).
- Fix: Fix validation of read-only fields inside dicts. Closes #474 (Arnau
  Orriols).
- Fix: Parent and collection links follow the scheme described in #475 (Jen
  Montes).
- Fix: Ignore read-only fields in ``PATCH`` requests when their values aren't
  changed compared to the stored document. Closes #479.
- Fix: Allow ``EVE_SETTINGS`` envvar to be used exclusively. Previously,
  a settings file in the working directory was always required. Closes #461.
- Fix: exception when trying to set nullable media field to null (Daniel
  Lytkin)
- Fix: Add missing ``$options`` and ``$list`` MongoDB operators to the
  allowed list (Jaroslav Semančík).
- Fix: Get document when it is missing embedded media. In case you try to
  embedd a document which has media fields and that document has been deleted,
  you would get an error (Petr Jašek).
- Fix: fix additional lookup regex in  RESTful Account Management tutorial
  (Ashley Roach).
- Fix: ``utils.weak_date`` always returns a RFC-1123 date (Petr Jašek).
- Fix: Can't embed a ressource with a custom _id (non ObjectId). Closes #427.
- Fix: Do not follow DATE_FORMAT for HTTP headers. Closes #429 (Olivier
  Poitrey).
- Fix: Fix app initialization with resource level versioning #409 (Sebastián
  Magrí).
- Fix: KeyError when trying to use embedding on a field that is missing from
  document. It was fixed earlier in #319, but came back again after new
  embedding mechanism (Daniel Lytkin).
- Fix: Support for list of strings as default value for fields (hansotronic).
- Fix: Media fields are now properly returned even in embedded documents.
  Closes #305.
- Fix: auth in domain configuration can be either a callable or a class
  instance (Gino Zhang).
- Fix: Schema definition: a default value of [] for a list causes IndexError.
  Closes #417.
- Fix: Close file handles in setup.py (Harro van der Klauw)
- Fix: Querying a collection should always return pagination information (even
  when no data is being returned). Closes #415.
- Fix: Recursively validate the whole query string.
- Fix: If the data layer supports a list of allowed query operators, take
  them into consideration when validating a query string. Closes #388.
- Fix: Abort with 400 if unsupported query operators are used. Closes #387.
- Fix: Return the error if a blacklisted MongoDB operator is used in a query
  (debug mode).
- Fix: Invalid sort syntax raises 500 instead of 400. Addresses #378.
- Fix: Fix serialization when `type` is missing in schema. #404 (Jaroslav
  Semančík).
- Fix: When PUTting or PATCHing media fields, they would not be properly
  replaced as needed (Stanislav Heller).
- Fix: ``test_get_sort_disabled`` occasional failure.
- Fix: A POST with an empty array leads to a server crash. Now returns a 400
  error isntead and ensure the server won't crash in case of mongo invalid
  operations (Olivier Poitrey).
- Fix: PATCH and PUT don't respect flask.abort() in a pre-update event. Closes
  #395 (Christopher Larsen).
- Fix: Validating keyschema rules would cause a TypeError since 0.4. Closes
  pyeve/cerberus#48.
- Fix: Crash if client projection is not a dict #390 (Olivier Poitrey).
- Fix: Server crash in case of invalid "where" syntax #386 (Olivier Poitrey).


Version 0.4
~~~~~~~~~~~

Released on 20 June, 2014.

- [new] You can now start the app without any resource defined and use
  ``app.register_resource`` later as needed (Petr Jašek).
- [new] Data layer is now usable outside request context, for example within
  a Celery task where there's no request context (Petr Jašek).
- [new][change] Add pagination info to get results whatever the HATEOAS status.
  Closes #355 (Olivier Poitrey).
- [new] Ensure all errors return a parseable body (JSON or XML). Closes #365
  (Olivier Poitrey).
- [new] Apply sub-request route's params to the created document if matching
  the schema, e.g. a POST on ``/people/1234…/invoices`` will set the
  ``contact_id`` field to 1234… so created invoice is automatically associated
  with the parent resource (Olivier Poitrey).
- [new] Allow some more HTTP errors (403 and 404) to be thrown from db hooks
  (Olivier Poitrey).
- [new] ``ALLOWED_READ_ROLES``. A list of allowed `roles` for resource
  endpoints with GET and OPTIONS methods (Olivier Poitrey).
- [new] ``ALLOWED_WRITE_ROLES``. A list of allowed `roles` for resource
  endpoints with POST, PUT and DELETE methods (Olivier Poitrey).
- [new] ``ALLOWED_ITEM_READ_ROLES``. A list of allowed `roles` for item
  endpoints with GET and OPTIONS methods (Olivier Poitrey).
- [new] ``ALLOWED_ITEM_WRITE_ROLES``. A list of allowed `roles` for item
  endpoints with PUT, PATCH and DELETE methods (Olivier Poitrey).
- [new] 'dependencies' validation rule.
- [new] 'keyschema' validation rule.
- [new] 'regex' validation rule.
- [new] 'set' as a core data type.
- [new] 'min' and 'max' now apply to floats and numbers too.
- [new] File Storage. ``EXTENDED_MEDIA_INFO`` allows a list of meta fields
  (file properties) to forward from the file upload driver (Ben Demaree).
- [new] Python 3.4 is now supported.
- [new] Support for default values in documents with more than one level of
  data (Javier Gonel).
- [new] Ability to send entire document in write responses. ``BANDWITH_SAVER``
  aka Coherence Mode (Josh Villbrandt).
- [new] ``on_pre_<METHOD>`` events expose the `lookup` dictionary which allows
  for setting up dynamic database lookups on both resource and item endpoints.
- [new] Return a 400 response on pymongo DuplicateKeyError, with exception
  message if debug mode is on (boosh).
- [new] PyPy officially supported and tested (Javier Gonel).
- [new] tox support (Javier Gonel).
- [new] Post database events (Javier Gonel). Addresses #272.
- [new] Versioned Documents (Josh Villbrandt). Closes #224.
- [new] Python trove classifiers added to setup.py.
- [new] Client projections are also honored at item endpoints.
- [new] validate that ID_FIELD is not set as a resource ``auth_field``.
  Addresses #266.
- [new] ``URL_PROTOCOL`` defines the HTTP protocol used when building HATEOAS
  links. Defaults to ``''`` for relative paths (Junior Vidotti).
- [new] ``on_delete_item`` and ``on_deleted_item`` is raised on DELETE requests
  sent to document endpoints. Addresses #232.
- [new] ``on_delete_resource`` and ``on_deleted_resource`` is raised on DELETE
  requests sent to resource endpoints. Addresses #232.
- [new] ``on_update`` is raised on PATCH requests, when a document is about to
  be updated on the database. Addresses #232.
- [new] ``on_replace`` is raised on PUT requests, when a document is about to
  be replaced on the database. Addresses #232.
- [new] ``auth`` constructor argument accepts either a class instance or
  a callable. Closes #248.

- [change] Cerberus 0.7.2 is now required.
- [change] Jinja2 2.7.3 is now required.
- [change] Werkzeug 0.9.6 is now required.
- [change] simplejson 3.5.2 is now required.
- [change] itsdangerous 0.24 is now required. Addresses #378.
- [change] Events 0.2.1 is now required.
- [change] MarkupSafe 0.23 is now required.
- [change] For bulk and non-bulk inserts, response status now always either 201
  when everything was ok or 400 when something went wrong. For bulk inserts, if
  at least one document doesn't validate, the whole request is rejected, and
  none of the documents are inserted into the database. Additionnaly, this
  commit adopts the same response format as collections: responses are always
  a dict with a ``_status`` field at its root and an eventual ``_error`` object
  if ``_status`` is ``ERR`` to comply with #366. Documents status are stored in
  the ``_items`` field (Olivier Poitrey).
- [change] Callbacks get whole json response on ``on_fetched``. This allows for
  callbacks functions to alter the whole payload, even when HATEOAS is enabled
  and ``_items`` and ``_links`` metafields are present.
- [change] ``on_insert`` is not raised anymore on PUT requests (replaced by
  above mentioned ``on_replace``).
- [change] ``auth.request_auth_value`` is no more. Yay. See below.
- [change] ``auth.set_request_auth_value()`` allows to set the ``auth_field``
  value for the current request.
- [change] ``auth.get_request_auth_value()`` allows to retrieve the
  ``auth_field`` value for the current request.
- [change] ``on_update(ed)`` and ``on_replace(ed)`` callbacks now receive both
  the original document and the updates (Jaroslav Semančík).
- [change] Review event names (Javier Gonel).

- [fix] return 500 instead of 404 if CORS is enabled. Closes #381.
- [fix] Crash on GET requests on resource endpoints when ID_FIELD is missing on
  one or more documents. Closes #351.
- [fix] Cannot change a nullable objectid type field to contain null. Closes
  #341.
- [fix] HATEOAS links as business unit values even when regexes are configured
  for the endpoint.
- [fix] Documentation improvements (Jen Montes).
- [fix] KeyError exception was raised when field specified in schema as
  embeddable was missing in a particular document (Jaroslav Semančík).
- [fix] Tests on HEAD requests would very occasionally fail. See #316.
- [change] PyMongo 2.7.1 is now required.
- [fix] Automatic fields such as ``DATE_CREATD`` and ``DATE_CREATED`` are
  correctly handled in client projections (Josh Villbrandt). Closes #282.
- [fix] Make codebase compliant with latest PEP8/flake8 release (Javier Gonel).
- [fix] If you had a media field, and set datasource projection to 0 for that
  field, the media would not be deleted. Closes #284.
- [fix] tests cleanup (Javier Gonel).
- [fix] tests now run on any system without needing to set ``ulimit`` to
  a higher value (Javier Gonel).
- [fix] media files: don't try to delete a field that does not exist (Taylor
  Brown).
- [fix] Occasional KeyError while building ``_media`` helper dict. See #271
  (Alexander Hendorf).
- [fix] ``If-Modified-Since`` misbehaviour when a datasource filter is set.
  Closes #258.
- [fix] Trouble serializing list of dicts. Closes #265 and #244.
- [fix] ``HATEOAS`` item links are now coherent actual endpoint URL even when
  natural immutable keys are used in URLs (Junior Vidotti). Closes #256.
- [fix] Replaced ``ID_FIELD`` by ``item_lookup_field`` on self link.
  item_lookup_field will default to ``ID_FIELD`` if blank.

Version 0.3
~~~~~~~~~~~

Released on 14 February, 2014.

- [fix] Serialization of sub-documents (Hannes Tiede). Closes #244.
- [new] ``X_MAX_AGE`` allows to configure CORS Access-Control-Max-Age (David
  Buchmann).
- [fix] ``GET`` with ``If-Modified-Since`` on list endpoint returns incorrect
  304 if resource is empty. Closes #243.
- [change] ``POST`` will return ``201 Created`` if at least one document was
  accepted for insertion; ``200 OK`` otherwise (meaning the request was
  accepted and processed). It is still client's responsability to parse the
  response payload to check if any document did not pass validation. Addresses
  #201 #202 #215.
- [new] ``number`` data type. Allows both integers and floats as field values.
- [fix] Using primary keys other than _id. Closes #237.
- [fix] Add tests for ``PUT`` when User Restricted Resource Access is active.
- [fix] Auth field not set if resource level authentication is set. Fixes #231.
- [fix] RateLimit check was occasionally failing and returning a 429 (John
  Deng).
- [change] Jinja2 2.7.2 is now required.
- [new] media files (images, pdf, etc.) can be uploaded as ``media`` document
  fields. When a document is requested, eventual media files will be returned
  as Base64 strings. Upload is done via ``POST``, ``PUT`` and ``PATCH`` using
  the ``multipart/form-data`` content-type. For optmized performance, by
  default files are stored in GridFS, however custom ``MediaStorage`` classes
  can be provided to support alternative storage systems. Clients and API
  maintainers can exploit the projections feature to include/exclude media
  fields from requests. For example, a request like
  ``/url/<id>?projection={"image": 0}`` will return the document without the
  image field. Also, while setting a resource ``datasource`` it is possible to
  explicitly exclude media fields from standard responses (clients will need to
  explicitly add them to the payload with ``?projection={"image": 1}``).
- [new] ``media`` type for schema fields.
- [new] ``media`` application argument. Allows to specify a media storage class
  to be used to store media files. Defaults to ``GridFSMediaStorage``.
- [new] ``GridFSMediaStorage`` class. Stores files into GridFS.
- [new] ``MediaStorage`` class provides a standardized API for storing files,
  along with a set of default behaviors that all other storage systems can
  inherit or override as necessary.
- [new] ``file`` data type support and validation for resource schema.
- [new] ``multipart/form-data`` content-type is now supported for requests.
- [fix] Field exclusion (``?projection={"fieldname": 0}``) now supported in
  client projections. Remember, mixing field inclusion and exclusion is still
  not supported by MongoDB.
- [fix] ``URL_PREFIX`` and ``API_VERSION`` are correctly reported in HATOEAS
  links.
- [fix] ``DELETE`` on sub-resources should only delete documents referenced by
  the parent. Closes #212.
- [fix] ``DELETE`` on a resource endpoint honors User-Restricted Resource
  Access. Closes #213.
- [new] ``JSON`` allows to enable/disable JSON responses. Defaults to ``True``
  (JSON enabled).
- [new] ``XML`` allows to enable/disable XML responses. Defaults to ``True``
  (XML enabled).
- [fix] XML properly honors ``_LINKS`` and ``_ITEMS`` settings.
- [fix] return all document fields when resource schema is empty.
- [new] pytest.ini for pytest support.
- [fix] All tests should now run with nose and pytest. Closes #209.
- [new] ``query_objectid_as_string`` resource setting. Defaults to ``False``.
  Addresses #207.
- [new] ``ETAG`` allows to customize the etag field. Defaults to ``_etag``.
- [change] ``etag`` is now ``_etag`` in all default response payloads (see
  above).
- [change] ``STATUS`` defaults to '_status'.
- [change] ``ISSUES`` defaults to '_issues'.
- [change] ``DATE_CREATED`` defaults to '_created'. Upgrade existing
  collections by running ``db.<collection>.update({}, { $rename: { "created":
  "_created" } }, { multi: true })`` in the mongo shell. If an index exists on
  the field, drop it and create a new one using the new field name.
- [change] ``LAST_UPDATED`` defaults to '_updated'. Upgrade existing
  collections by running ``db.<collection>.update({}, { $rename: { "updated":
  "_updated" } }, { multi: true })`` in the mongo shell. If an index exists on
  the field, drop it and create a new one usung the new field name.
- [change] Exclude ``etag`` from both response payload and headers if
  concurrency control is disabled (``IF_MATCH`` = ``False``). Closes #205.
- [fix] Custom ``ID_FIELD`` would fail on update/insert methods. Fixes #203
  (Jaroslav Semančík).
- [change] GET: when If-Modified-Since header is present, either no documents
  (304) or all documents (200) are sent per the HTTP spec. Original behavior
  can be achieved with:
  ``/resource?where={"updated":{"$gt":"if-modified-since-date"}}`` (Josh
  Villbrandt).
- [change] Validation errors are now reported as a dictionary with offending
  fields as keys and issues descriptions as values.
- [change] Cerberus v0.6 is now required.

Version 0.2
~~~~~~~~~~~

Released on 30 November, 2013.

- [new] Sub-Resources. It is now possible to configure endpoints such as:
  ``/companies/<company_id>/invoices``. Also, the corresponding item endpoints,
  such as ``/companies/<company_id>/invoices/<invoice_id>``, are available. All
  CRUD operations on these endpoints are allowed. Closes 156.
- [new] ``resource_title`` allows to customize the endpoint title (HATEOAS).
- [new][dev] ``extra`` cursor property, when present, will be added to ``GET``
  responses (with same key). This feature can be used by Eve extensions to
  inject proprietary data into the response stream (Petr Jašek).
- [new] ``IF_MATCH`` allows to disable checks for ETag matches on edit, replace
  and delete requests. If disabled, requests without an If-Match header will be
  honored without returning a 403 error. Defaults to True (enabled by default).
- [new] ``LINKS`` allows to customize the links field. Default to '_links'.
- [new] ``ITEMS`` allows to customize the items field. Default to '_items'.
- [new] ``STATUS`` allows to customize the status field. Default to 'status'.
- [new] ``ISSUES`` allows to customize the issues field. Default to 'issues'.
- [new] Handling custom ID fields tutorial.
- [new] A new ``json_encoder`` initialization argument is available. It allows
  to pass custom JSONEncoder or eve.io.BaseJSONEncoder to the Eve instance.
- [new] A new ``url_converters`` initialization argument is available. It
  allows to pass custom Flask url converters to the Eve constructor.
- [new] ID_FIELD fields can now be of arbitrary types, not only ObjectIds.
  Thanks to Kelvin Hammond for contributing to this one.  Closes #136.
- [new] ``pre_<method>`` and ``pre_<method>_<resource>`` event hooks are now
  available. They are raised when a request is received and before processing
  it. The resource involved and the Flask request object are returned to the
  callback function (dccrazyboy).
- [new] ``embedded_fields`` activates default Embedded Resource Serialization
  on a list of selected document fields. Eventual embedding requests by clients
  will be processed along with default embedding. In order for default
  embedding to work, the field must be defined as embeddable, and embedding
  must be active for the resource (with help from Christoph Witzany).
- [new] ``default_sort`` option added to the ``datasource`` resource setting.
  It allows to set default sorting for the endpoint. Default sorting will be
  overriden by a client request that happens to include a ``?sort`` argument
  within the query string (with help from Christoph Witzany).
- [new] You can now choose to provide custom settings as a Python dictionary.
- [new] New method ``Eve.register_resource()`` for registering new resource
  after initialization of Eve object. This is needed for simpler initialization
  API of all ORM/ODM extensions (Stanislav Heller).
- [change] Rely on Flask endpoints to map urls to resources.
- [change] For better consistency with new ``pre_<method>`` hooks,
  ``on_<method>`` event hooks have been renamed to ``on_post_<method>``.
- [change] Custom authentication classes can now be set at endpoint level. When
  set, an endpoint-level auth class will override the eventual global level
  auth class.  Authentication docs have been updated (and greatly revised)
  accordingly.  Closes #89.
- [change] JSON encoding is now handled at the DataLayer level allowing for
  specialized, granular, data-aware encoding. Also, since the JSON encoder is
  now a class attribute, extensions can replace the pre-defined data layer
  encoder with their own implementation. Closes #102.
- [fix] HMAC example and docs updated to align with new hmac in Python 2.7.3,
  which is only accepting bytes string. Closes #199.
- [fix] Properly escape leaf values in XML responses (Florian Rathgeber).
- [fix] A read-only field with a default value would trigger a validation error
  on POST and PUT methods.

Version 0.1.1
~~~~~~~~~~~~~

Released on October 31th, 2013.

- DELETE now uses the original document ID_FIELD when issuing the delete
  command to the underlying data layer (Xavi Cubillas).
- Embedded Resource Serialization also available at item endpoints
  (``/invoices/<id>/?embedded={'person':1}``),
- ``collection`` (used when setting up a data relation, see Embedded Resource
  Serialization) has been renamed to ``resource`` in order to avoid confusion
  between the Eve schema and underlying MongoDB collections.
- Nested endpoints. Endpoints with deep paths like ``/contacts/overseas`` can
  now function in conjuction with top-level endpoints (``/contacts``).
  Endpoints are completely independent: each can allow item lookups
  (``/contacts/<id>`` and ``contacts/overseas/<id>``) and different access
  methods. Previously, while you could have complex urls, you could not get
  nested endpoints to work properly.
- PyMongo 2.6.3 is now supported.
- item-id wrappers have been removed from POST/PATCH/PUT requests and
  responses. Requests for single document insertion/edition are now performed
  by just submitting the relevant document. Bulk insert requests are performed
  by submitting a list of documents. The response to bulk requests is a list
  itself in which every list item contains the state of the corresponding
  request document. Please note that this is a breaking change. Also be aware
  that when the request content-type is ``x-www-form-urlencoded``, single
  document insert is performed. Closes #139.
- ObjectId are properly serialized on POST/PATCH/PUT methods.
- Queries on ObjectId and datetime values in nested documents.
- ``auth.user_id`` renamed to ``auth.request_auth_value`` for better
  consistency with the ``auth_field`` setting. Closes #132 (Ryan Shea).
- Same behavior as Flask, SERVER_NAME now defaults to None. It allows much
  easier development on distant machine that may changes IP (Ronan Delacroix).

- CORS support was not available for ``additional_lookup`` urls (Petr Jašek.)
- 'default' field values that could be assimilated to ``None`` (0, None, "")
  would be ignored.
- POST and PUT would fail with 400 if there was no auth class while
  ``auth_field`` was set for a resource.
- Fix order of string arguments in exception message in
  flaskapp.validate_schema() (Roy Smith).

Version 0.1
~~~~~~~~~~~

Released on September 30th, 2013.

- ``PUT`` method for completely replace a document while keeping the same
  unique identifier. Closes #96.
- Embedded Resource Serialization. If a document field is referencing
  a document in another resource, clients can request the referenced document
  to be embedded within the requested document (Bryan Cattle).  Closes #68.
- "No trailing slash" URLs are now supported. Closes #118.
- HATEOAS is now optional and can be disabled both at global and resource
  level.
- ``X-HTTP-Method-Override`` supported for all HTTP Methods. Closes #95.
- HTTP method is now passed into ``authenticate()`` and ``check_auth()`` (Ken
  Carpenter). Closes #90 .
- Cleanup and hardening of User-Restricted Resource Access Edit (Bryan Cattle).
- Account Management tutorial updated to reflect the event hooks naming update
  introduced in v0.0.9.
- Some more Python 3 refactoring (Dong Wei Ming).
- Events 0.2.0 is now supported.
- PyMongo 2.6.2 is now supported.
- Cerberus 0.4.0 is now supported.

- Item ``GET`` on documents with non-existent 'created' field (because
  stored outside of API context) were not returning a default value for the
  field.
- Edits on documents with non-existent 'created' or 'updated' fields
  (because stored outside of the API context) were returning ``412 Precondition
  Failed``. Closes #123.
- ``on_insert`` is raised when a ``PUT`` (replace action) is about to be
  performed. Closes #120.
- Installation on Windows with Python 3 was returning encoding errors.
- Fixed #99: malformed XML render when href includes forbidden URI/URL chars.
- Fixed a bug introduced with 0.0.9 and Python 3 support. Filters (``?where``)
  on datetime values were not working when running on Python 2.x.
- Fixed some typos and minor grammatical errors all across the documentation
  (Ken Carpenter, Jean Boussier, Kracekumar, Francisco Corrales Morales).

Version 0.0.9
~~~~~~~~~~~~~

Released on August 29, 2013

- PyMongo 2.6 is now supported.
- ``FILTERS`` boolean replaced by ``ALLOWED_FILTERS`` list which allows for
  explicit whitelisting of filter-enabled fields (Bryan Cattle). Closes #78.
- Custom user ids for User-Restricted Resource Access, allowing for more
  flexibility and token revocation with token-based authentication. Closes #73.
- ``AUTH_USERNAME_FIELD`` renamed to ``AUTH_FIELD``.
- ``auth_username_field`` renamed to ``auth_field``.
- BasicAuth and subclasses now support ``user_id`` property.
- Updated the event hooks naming system to be more robuts and consistent.
  Closes #80.
- To emphasize the fact that they are tied to a method, all ``on_<method>``
  hooks now have ``<method>`` in uppercase.
- ``on_getting`` hook renamed to ``on_fetch_resource``.
- ``on_getting_<resource>`` hook renamed to ``on_fetch_resource_<resource>``
- ``on_getting_item`` hook renamed to ``on_fetch_item``.
- ``on_getting_item_<item_title>`` hook renamed to
  ``on_fetch_item_<item_title>``.
- ``on_posting`` hook renamed to ``on_insert``.
- Datasource  projections always include automatic fields (``ID_FIELD``,
  ``LAST_UPDATED``, ``DATE_CREATED``). Closes #85.
- Public HTTP methods now override `auth_username_field` Edit. Closes #70
  (Bryan Cattle).
- Response date fields are now using GMT instead of UTC. Closes #83.
- Handle the case of 'additional_lookup' field being an integer. If this is the
  case you can omit the 'url' key, as it will be ignored, and the integer value
  correctly parsed.
- More informative HTTP error messages. Some more informative error messages
  have been added for HTTP 400/3/12 and 500 errors. The error messages only
  show if DEBUG==True (Bryan Cattle).
- ``on_getting(resource, documents)`` is now ``on_getting_resource(resource,
  documents)``; ``on_getting_<resource>(documents) is now known as
  ``on_getting_resource_<resource>(documents)`` (Ryan Shea).
- Added a new event hook: ``on_getting_item_<title>(_id, document)`` (Ryan
  Shea).
- Allow ``auth_username_field`` to be set to ``ID_FIELD`` (Bryan Cattle).
- Python 3.3 is now supported.
- Flask 0.10.1 is now supported.
- Werkzeug 0.9.4 is now supported.
- Copyright finally updated to 2013.

Version 0.0.8
~~~~~~~~~~~~~

Released on July 25th 2013.

- Only run RateLimiting tests if redis-py is installed and redis-server is
  running.
- CORS ``Access-Control-Allow-Headers`` header support (Garrin Kimmell).
- CORS ``OPTIONS`` support for resource and items endpoints (Garrin Kimmell).
- ``float`` is now available as a data-type in the schema definition ruleset.
- ``nullable`` field schema rule is now available. If ``True`` the field value
  can be set to null. Defaults to ``False``.
- v0.3.0 of Cerberus is now a requirement.
- ``on_getting``, ``on_getting_<resource>`` and ``on_getting_item`` event
  hooks. These events are raised when documents have just been read from the
  database and are about to be sent to the client. Registered callback
  functions can eventually manipulate the documents as needed. Please be aware
  that ``last_modified`` and ``etag`` headers will always be consistent with
  the state of the documents on the database (they  won't be updated to reflect
  changes eventually applied by the callback functions). Closes #65.
- Documentation fix: ``AUTH_USERFIELD_NAME`` renamed to ``AUTH_USERNAME_FIELD``
  (Julien Barbot).
- Responses to GET requests for resource endpoints now include a ``last`` item
  in the `_links` dictionary. The value is a link to the last page available.
  The item itself is only provided if pagination is enabled and the page being
  requested isn't the last one. Closes #62.
- It is now possible to set the MongoDB write concern level at both global
  (``MONGO_WRITE_CONCERN``) and endpoint (``mongo_write_concern``) levels. The
  value is a dictionary with all valid MongoDB write_concern settings (w,
  wtimeout, j and fsync) as keys. ``{'w': 1}`` is the default, which is also
  MongoDB's default setting.
- ``TestMininal`` class added to the test suite. This will allow to start the
  building of the tests for an application based on Eve, by subclassing the
  TestMinimal class (Daniele Pizzolli).

Version 0.0.7
~~~~~~~~~~~~~

Released on June 18th 2013.

- Pinned Werkzeug requirement to v0.8.3 to avoid issues with the latest release
  which breaks backward compatibility (actually a Flask 0.9 requirements issue,
  which backtracked to Eve).
- Support for Rate Limiting on all HTTP methods. Closes #58. Please note: to
  successfully execute the tests in 'eve.tests.methods.ratelimit.py`, a running
  redis server is needed.
- ``utils.request_method`` internal helper function added, which allowed  for
  some nice code cleanup (DRY).
- Setting the default 'field' value would not happen if a 'data_relation' was
  nested deeper than the first schema level. Fixes #60.
- Support for ``EXTRA_RESPONSE_FIELDS``. It is now possible to configure a list
  of additonal document fields that should be provided with POST responses.
  Normally only automatically handled fields (``ID_FIELD``, ``LAST_UPDATED``,
  ``DATE_CREATED``, ``etag``) are included in POST payloads.
  ``EXTRA_RESPONSE_FIELDS`` is a global setting that will apply to all resource
  endpoint . Defaults to ``[]``, effectively disabling the feature.
  ``extra_response_fields`` is a local resource setting and will override
  ``EXTRA_RESPONSE_FIELDS`` when present.
- ``on_posting`` and ``on_posting_<resource>`` event hooks. ``on_posting`` and
  ``on_posting_<resource>`` events are raised when documents are about to be
  stored. Among other things this allows callback functions to arbitrarily
  update the documents being inserted. ``on_posting(resource, documents)`` is
  raised on every successful POST while ``on_posting_<resource>(documents)`` is
  only raised when <resource> is being updated. In both circumstances events
  will be raised only if at least one document passed validation and is going
  to be inserted.
- Flask native ``request.json`` is now used when decoding request payloads.
- *resource* argument added to Authorization classes. The ``check_auth()``
  method of all classes in the ``eve.auth`` package (``BasicAuth``,
  ``HMACAuth``, ``TokenAuth``) now supports the *resource* argument. This
  allows subclasses to eventually build their custom authorization logic around
  the resource being accessed.
- ``MONGO_QUERY_BLACKLIST`` option added. Allows to blacklist mongo query
  operators that should not be allowed in resource queries (``?where=``).
  Defaults to ['$where', '$regex']. Mongo Javascript operators are disabled by
  default as they might be used as vectors for injection attacks. Javascript
  queries also tend to be slow and generally can be easily replaced with the
  (very rich) Mongo query dialect.
- ``MONGO_HOST`` defaults to 'localhost'.
- ``MONGO_PORT`` defaults to 27017.
- Support alternative hosts/ports for the test suite (Paul Doucet).

Version 0.0.6
~~~~~~~~~~~~~

Released on May 13th 2013.

- Content-Type header now properly parsed when additional arguments are
  included (Ondrej Slinták).
- Only fields defined in the resource schema are now returned from the
  database. Closes #52.
- Default ``SERVER_NAME`` is now set to ``127.0.0.1:5000``.
- ``auth_username_field`` is honored even when there is no query in the request
  (Thomas Sileo).
- Pagination links in XML payloads are now properly escaped. Fixes #49.
- HEAD requests supported. Closes #48.
- Event Hooks. Each time a GET, POST, PATCH, DELETE method has been executed,
  both global ``on_<method>`` and resource-level ``on_<method>_<resource>``
  events will be raised. You can subscribe to these events with multiple
  callback functions. Callbacks will receive the original flask.request object
  and the response payload as arguments.
- Proper ``max_results`` handling in ``eve.utils.parse_request``, refactored
  tests (Tomasz Jezierski).
- Projections. Projections are conditional queries where the client dictates
  which fields should be returned by the API (Nicolas Bazire).
- ``ALLOW_UNKNOWN`` option, and the corresponding ``allow_options`` local
  setting, allow for a less strict schema validation. Closes #34.
- ETags are now provided with POST responses. Closes #36.
- PATCH performance improvement: ETag is now computed in memory; performing an
  extra database lookup is not needed anymore.
- Bulk Inserts on the database. POST method heavily refactored to take
  advantage of MongoDB native support for Bulk Inserts. Please note: validation
  constraints are checked against the database, and not between the payload
  documents themselves. This causes an interesting corner case: in the event of
  a multiple documents payload where two or more documents carry the same value
  for a field where the ``unique`` constraint is set, the payload will validate
  successfully, as there are no duplicates in the database (yet). If this is an
  issue, the client can always send the documents once at a time for insertion,
  or validate locally before submitting the payload to the API.
- Responses to document GET requests now include the ETag in both the header
  and the payload. Closes #29.
- ``methods`` settings keyword renamed to ``resource_methods`` for coherence
  with the global ``RESOURCE_METHODS`` (Nicolas Carlier).

Version 0.0.5
~~~~~~~~~~~~~

Released on April 11th 2013.

- Fixed an issue that apparently caused the test suite to only run successfully
  on the dev box. Thanks Chronidev for reporting this.
- Referential integrity validation via the new ``data_relation`` schema
  keyword.  Closes #25.
- Support for ``Content-Type: application/json`` for POST and PATCH methods.
  Closes #28.
- User-restricted resource access. Works in conjunction with Authentication.
  When enabled, users can only read/update/delete resource items created by
  themselves. Can be switched on and off at global level via the
  ``AUTH_USERFIELD_NAME`` keywork, or at single resource endpoints with the
  user_userfield_name keyword (the latter will override the former). The
  keyword contains the actual name of the field used to store the username of
  the user who created the resource item. Defaults to '', which disables the
  feature (Thomas Sileo).
- ``PAGING_LIMIT`` keyword setting renamed to ``PAGINATION_LIMIT`` for better
  coherency with the new ``PAGINATION`` keyword. This could break backward
  compatibility in some cases.
- ``PAGING_DEFAULT`` keyword settings renamed to ``PAGINATION_DEFAULT`` for
  better coherence with the new ``PAGINATION`` keyword. This could break
  backward compatibility in some cases.
- ``ITEM_CACHE_CONTROL`` removed as it seems unnecessary at the moment.
- Added an example on how to handle events to perform custom actions. Closes
  #23 and #22.
- ``eve.validation_schema()`` now collects offending items and returns all of
  them into the exception message. Closes #24.
- Filters (``?where=``), sorting (``?sort=``) and pagination (``?page=10``) can
  now be be disabled at both global and endpoint level. Closes #7.
- CORS (Cross-Origin Resource Sharing) support. The new ``X-DOMAINS`` keywords
  allows API maintainers to specify which domains are allowed to perform CORS
  requests. Allowed values are: None, a list of domains, or '*' for a wide-open
  API. Closes #1.
- HMAC (Hash Message Authentication Code) based Autentication.
- Token Based Authentication, a variation of Basic Authentication. Closes #20.
- Orphan function removed (``eve.methods.get.standard_links`` ).
- ``DATE_CREATED`` and ``LAST_UPDATED`` fields now show default values for
  documents created outside the API context. Fixes #18.

Version 0.0.4
~~~~~~~~~~~~~

Released on February 25th 2013.

- Consistent ETag computation between runs/instances. Closes #16.
- Support for Basic Authentication (RFC2617).
- Support for fine-tuning authentication with ``PUBLIC_METHODS`` and
  ``PUBLIC_ITEM_METHODS``. By default, access is restricted to *all* endpoints,
  for *all* HTTP verbs (methods), effectively locking down the whole API.
- Supporto for role-based access control with ``ALLOWED_ROLES`` and
  ``allowed_roles``.
- Support for all standard Flask initialization parameters.
- Support for default values in resource fields. The new ``default`` keyword
  can now be used when defining a field rule set.  Please note: currently
  default values are supported only for main document fields. Default values
  for fields in embedded documents will be ignored.
- Multiple API endpoints can now target the same database collection. For
  example now you can set both ``/admins/`` and ``/users/`` to read and write
  from the same collection on the db, *people*.  The new ``datasource`` setting
  allows to explicitly link API resources to database collections. It is
  a dictionary with two allowed keys: *source* and *filter*. *source* dictates
  the database collection consumed by the resource.  *filter* is the underlying
  query, applied by the API when retrieving and validating data for the
  resource.  Previously, the resource name would dictate the linked datasource
  (and of course you could not have two resources with the same name). This
  remains the default behaviour: if you omit the ``datasource`` setting for
  a resource, its name will be used to determine the database collection.
- It is now possibile to set predefined db filters for each resource.
  Predefined filters run on top of user queries (GET requests with ``where``
  clauses) and standard conditional requests (``If-Modified-Since``, etc.)
  Please note that datasource filters are applied on GET, PATCH and DELETE
  requests. If your resource allows for POST requests (document insertions),
  then you will probably want to set the validation rules accordingly (in our
  example, 'username' should probably be a required field).
- JSON-Datetime dependency removed.
- Support for Cerberus v0.0.3 and later.
- Support for Flask-PyMongo v0.2.0 and later.
- Repeated XML requests to the same endpoint could occasionally return an
  Internal Server Error (Fixes #8).

Version 0.0.3
~~~~~~~~~~~~~

Released on January 22th 2013.

- XML rendering love. Lots of love.
- JSON links are always wrapped in a ``_links`` dictionary. Key values match
  the relation between the item being represented and the linked resource.
- Streamlined JSON responses. Superflous ``response`` root key has been removed
  from JSON payloads. GET requests to resource endpoints: items are now wrapped
  with an ``_items`` list. GET requests to item endpoints: item is now at root
  level, with no wrappers around it.
- Support for API versioning through the new API_VERSION configuration setting.
- Boolean values in request forms are now correctly parsed.
- Tests now run under Python 2.6.


Version 0.0.2
~~~~~~~~~~~~~

Released on November 27th 2012.

- Homepage/api entry point resource links fixed. They had bad 'href'
  tags which also caused XML validation issues when processing responses
  (especially when accessing the API via browser).
- Version number in 'Server' response headers.
- Added support for DELETE at resource endpoints. Expected behavior:
  will delete all items in the collection. Disabled by default.
- :class:`eve.io.mongo.Validator` now supports :class:`~cerberus.Validator`
  signature, allowing for further subclassing.

Version 0.0.1
~~~~~~~~~~~~~

Released on November 20th 2012.

- First public preview release.
