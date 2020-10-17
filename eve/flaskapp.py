# -*- coding: utf-8 -*-
"""
    eve.flaskapp
    ~~~~~~~~~~~~

    This module implements the central WSGI application object as a Flask
    subclass.

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
import fnmatch
import os
import sys
import warnings

import copy
from events import Events
from flask import Flask
from werkzeug.routing import BaseConverter
from werkzeug.serving import WSGIRequestHandler

import eve
from eve import default_settings
from eve.endpoints import (
    collections_endpoint,
    item_endpoint,
    home_endpoint,
    error_endpoint,
    media_endpoint,
    schema_collection_endpoint,
    schema_item_endpoint,
)
from eve.exceptions import ConfigException, SchemaException
from eve.io.mongo import Mongo, Validator, GridFSMediaStorage, ensure_mongo_indexes
from eve.logging import RequestFilter
from eve.utils import api_prefix, extract_key_values


class EveWSGIRequestHandler(WSGIRequestHandler):
    """Extend werkzeug request handler to include current Eve version in all
    responses, which is super-handy for debugging.
    """

    @property
    def server_version(self):
        return (
            "Eve/%s " % eve.__version__
            + super(EveWSGIRequestHandler, self).server_version
        )


class RegexConverter(BaseConverter):
    """ Extend werkzeug routing by supporting regex for urls/API endpoints """

    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


class Eve(Flask, Events):
    """The main Eve object. On initialization it will load Eve settings, then
    configure and enable the API endpoints. The API is launched by executing
    the code below:::

        app = Eve()
        app.run()

    :param import_name: the name of the application package
    :param settings: the name of the settings file.  Defaults to `settings.py`.
    :param validator: custom validation class. Must be a
                      :class:`~cerberus.Validator` subclass. Defaults to
                      :class:`eve.io.mongo.Validator`.
    :param data: the data layer class. Must be a :class:`~eve.io.DataLayer`
                 subclass. Defaults to :class:`~eve.io.Mongo`.
    :param auth: the authentication class used to authenticate incoming
                 requests. Must be a :class: `eve.auth.BasicAuth` subclass.
    :param redis: the redis (pyredis) instance used by the Rate-Limiting
                  feature, if enabled.
    :param url_converters: dictionary of Flask url_converters to add to
                           supported ones (int, float, path, regex).
    :param json_encoder: custom json encoder class. Must be a
                         JSONEncoder subclass. You probably want it to be
                         as eve.io.base.BaseJSONEncoder subclass.
    :param media: the media storage class. Must be a
                  :class:`~eve.io.media.MediaStorage` subclass.
    :param kwargs: optional, standard, Flask parameters.

    .. versionchanged:: 0.6.1
       Fix: When `SOFT_DELETE` is active an exclusive `datasource.projection`
       causes a 500 error. Closes #752.

    .. versionchanged:: 0.6
       Add request metadata to default log record.

    .. versionchanged:: 0.4
       Ensure all errors returns a parseable body. Closes #365.
       'auth' argument can be either an instance or a callable. Closes #248.
       Made resource setup more DRY by calling register_resource.

    .. versionchanged:: 0.3
       Support for optional media storage system. Defaults to
       GridFSMediaStorage.

    .. versionchanged:: 0.2
       Support for additional Flask url converters.
       Support for optional, custom json encoder class.
       Support for endpoint-level authentication classes.
       New method Eve.register_resource() for registering new resource after
       initialization of Eve object. This is needed for simpler initialization
       API of all ORM/ODM extensions.

    .. versionchanged:: 0.1.0
       Now supporting both "trailing slashes" and "no-trailing slashes" URLs.

    .. versionchanged:: 0.0.7
       'redis' argument added to handle an accessory Redis server (currently
       used by the Rate-Limiting feature).

    .. versionchanged:: 0.0.6
       'Events' added to the list of super classes, allowing for the arbitrary
       raising of events within the application.

    .. versionchanged:: 0.0.4
       'auth' argument added to handle authentication classes
    """

    #: Allowed methods for resource endpoints
    supported_resource_methods = ["GET", "POST", "DELETE"]

    #: Allowed methods for item endpoints
    supported_item_methods = ["GET", "PATCH", "DELETE", "PUT"]

    def __init__(
        self,
        import_name=__package__,
        settings="settings.py",
        validator=Validator,
        data=Mongo,
        auth=None,
        redis=None,
        url_converters=None,
        json_encoder=None,
        media=GridFSMediaStorage,
        **kwargs
    ):
        """Eve main WSGI app is implemented as a Flask subclass. Since we want
        to be able to launch our API by simply invoking Flask's run() method,
        we need to enhance our super-class a little bit.
        """

        super(Eve, self).__init__(import_name, **kwargs)

        # add support for request metadata to the log record
        self.logger.addFilter(RequestFilter())

        self.validator = validator
        self.settings = settings

        self.load_config()
        self.validate_domain_struct()

        # enable regex routing
        self.url_map.converters["regex"] = RegexConverter

        # optional url_converters and json encoder
        if url_converters:
            self.url_map.converters.update(url_converters)

        self.data = data(self)
        if json_encoder:
            self.data.json_encoder_class = json_encoder

        self.media = media(self) if media else None
        self.redis = redis

        if auth:
            self.auth = auth() if callable(auth) else auth
        else:
            self.auth = None

        self._init_url_rules()

        if self.config["RETURN_MEDIA_AS_URL"]:
            self._init_media_endpoint()

        self._init_schema_endpoint()

        if self.config["OPLOG"] is True:
            self._init_oplog()

        # validate and set defaults for each resource

        # Use a snapshot of the DOMAIN setup for iteration so
        # further insertion of versioned resources do not
        # cause a RuntimeError due to the change of size of
        # the dict
        domain_copy = copy.deepcopy(self.config["DOMAIN"])
        for resource, settings in domain_copy.items():
            self.register_resource(resource, settings)

        # it seems like both domain_copy and config['DOMAIN']
        # suffered changes at this point, so merge them
        # self.config['DOMAIN'].update(domain_copy)

        self.register_error_handlers()

    def run(self, host=None, port=None, debug=None, **options):
        """
        Pass our own subclass of :class:`werkzeug.serving.WSGIRequestHandler
        to Flask.

        :param host: the hostname to listen on. Set this to ``'0.0.0.0'`` to
                     have the server available externally as well. Defaults to
                     ``'127.0.0.1'``.
        :param port: the port of the webserver. Defaults to ``5000``.
        :param debug: if given, enable or disable debug mode.
                      See :attr:`debug`.
        :param options: the options to be forwarded to the underlying
                        Werkzeug server.  See
                        :func:`werkzeug.serving.run_simple` for more
                        information."""

        options.setdefault("request_handler", EveWSGIRequestHandler)
        super(Eve, self).run(host, port, debug, **options)

    def load_config(self):
        """API settings are loaded from standard python modules. First from
        `settings.py`(or alternative name/path passed as an argument) and
        then, when defined, from the file specified in the
        `EVE_SETTINGS` environment variable.

        Since we are a Flask subclass, any configuration value supported by
        Flask itself is available (besides Eve's proper settings).

        .. versionchanged:: 0.6
           SchemaErrors raised during configuration
        .. versionchanged:: 0.5
           Allow EVE_SETTINGS envvar to be used exclusively. Closes #461.

        .. versionchanged:: 0.2
           Allow use of a dict object as settings.
        """

        # load defaults
        self.config.from_object("eve.default_settings")

        # overwrite the defaults with custom user settings
        if isinstance(self.settings, dict):
            self.config.update(self.settings)
        else:
            if os.path.isabs(self.settings):
                pyfile = self.settings
            else:

                def find_settings_file(file_name):
                    # check if we can locate the file from sys.argv[0]
                    abspath = os.path.abspath(os.path.dirname(sys.argv[0]))
                    settings_file = os.path.join(abspath, file_name)
                    if os.path.isfile(settings_file):
                        return settings_file
                    else:
                        # try to find settings.py in one of the
                        # paths in sys.path
                        for p in sys.path:
                            for root, dirs, files in os.walk(p):
                                for f in fnmatch.filter(files, file_name):
                                    if os.path.isfile(os.path.join(root, f)):
                                        return os.path.join(root, file_name)

                # try to load file from environment variable or settings.py
                pyfile = find_settings_file(
                    os.environ.get("EVE_SETTINGS") or self.settings
                )

            if not pyfile:
                raise IOError("Could not load settings.")

            try:
                self.config.from_pyfile(pyfile)
            except:
                raise

        # flask-pymongo compatibility
        self.config["MONGO_CONNECT"] = self.config["MONGO_OPTIONS"].get("connect", True)

        self.check_deprecated_features()

    def check_deprecated_features(self):
        """Method checks for usage of deprecated features."""

        def deprecated_renderers_settings():
            """Checks if JSON or XML setting is still being used instead of
            RENDERERS and if so, composes new settings.
            """
            msg = (
                "{} setting is deprecated and will be removed"
                " in future release. Please use RENDERERS instead."
            )

            if "JSON" in self.config or "XML" in self.config:
                self.config["RENDERERS"] = default_settings.RENDERERS[:]

            if "JSON" in self.config:
                warnings.warn(msg.format("JSON"))
                if not self.config["JSON"]:
                    self.config["RENDERERS"].remove("eve.render.JSONRenderer")

            if "XML" in self.config:
                warnings.warn(msg.format("XML"))
                if not self.config["XML"]:
                    self.config["RENDERERS"].remove("eve.render.XMLRenderer")

        deprecated_renderers_settings()

    def validate_domain_struct(self):
        """Validates that Eve configuration settings conform to the
        requirements.
        """
        try:
            domain = self.config["DOMAIN"]
        except:
            raise ConfigException("DOMAIN dictionary missing or wrong.")
        if not isinstance(domain, dict):
            raise ConfigException("DOMAIN must be a dict.")

    def validate_config(self):
        """Makes sure that REST methods expressed in the configuration
        settings are supported.

        .. versionchanged:: 0.2.0
           Default supported methods are now class-level attributes.
           Resource validation delegated to _validate_resource_settings().

        .. versionchanged:: 0.1.0
        Support for PUT method.

        .. versionchanged:: 0.0.4
           Support for 'allowed_roles' and 'allowed_item_roles'

        .. versionchanged:: 0.0.2
            Support for DELETE resource method.
        """
        # make sure that global resource methods are supported.
        self.validate_methods(
            self.supported_resource_methods,
            self.config.get("RESOURCE_METHODS"),
            "resource",
        )

        # make sure that global item methods are supported.
        self.validate_methods(
            self.supported_item_methods, self.config.get("ITEM_METHODS"), "item"
        )

        # make sure that individual resource/item methods are supported.
        for resource, settings in self.config["DOMAIN"].items():
            self._validate_resource_settings(resource, settings)

    def _validate_resource_settings(self, resource, settings):
        """Validates one resource in configuration settings.

        :param resource: name of the resource which settings refer to.
        :param settings: settings of resource to be validated.

        .. versionchanged:: 0.4
           validate that auth_field is not set to ID_FIELD. See #266.

        .. versionadded:: 0.2
        """
        self.validate_methods(
            self.supported_resource_methods,
            settings["resource_methods"],
            "[%s] resource " % resource,
        )
        self.validate_methods(
            self.supported_item_methods,
            settings["item_methods"],
            "[%s] item " % resource,
        )

        # while a resource schema is optional for read-only access,
        # it is mandatory for write-access to resource/items.
        if (
            "POST" in settings["resource_methods"]
            or "PATCH" in settings["item_methods"]
        ):
            if not settings["schema"]:
                raise ConfigException(
                    "A resource schema must be provided "
                    "when POST or PATCH methods are allowed "
                    "for a resource [%s]." % resource
                )

        self.validate_roles("allowed_roles", settings, resource)
        self.validate_roles("allowed_read_roles", settings, resource)
        self.validate_roles("allowed_write_roles", settings, resource)
        self.validate_roles("allowed_item_roles", settings, resource)
        self.validate_roles("allowed_item_read_roles", settings, resource)
        self.validate_roles("allowed_item_write_roles", settings, resource)

        if settings["auth_field"] == settings["id_field"]:
            raise ConfigException(
                '"%s": auth_field cannot be set to id_field '
                "(%s)" % (resource, settings["id_field"])
            )

        self.validate_schema(resource, settings["schema"])

    def validate_roles(self, directive, candidate, resource):
        """Validates that user role directives are syntactically and formally
        adequate.

        :param directive: either 'allowed_[read_|write_]roles' or
                          'allow_item_[read_|write_]roles'.
        :param candidate: the candidate setting to be validated.
        :param resource: name of the resource to which the candidate settings
                         refer to.

        .. versionadded:: 0.0.4
        """
        roles = candidate[directive]
        if not isinstance(roles, list):
            raise ConfigException("'%s' must be list" "[%s]." % (directive, resource))

    def validate_methods(self, allowed, proposed, item):
        """Compares allowed and proposed methods, raising a `ConfigException`
        when they don't match.

        :param allowed: a list of supported (allowed) methods.
        :param proposed: a list of proposed methods.
        :param item: name of the item to which the methods would be applied.
                     Used when raising the exception.
        """
        diff = set(proposed) - set(allowed)
        if diff:
            raise ConfigException(
                "Unallowed %s method(s): %s. "
                "Supported: %s" % (item, ", ".join(diff), ", ".join(allowed))
            )

    def validate_schema(self, resource, schema):
        """Validates a resource schema.

        :param resource: resource name.
        :param schema: schema definition for the resource.

        .. versionchanged:: 0.6.2
           Do not allow '$' and '.' in root and dict field names. #780.

        .. versionchanged:: 0.6
           ID_FIELD in the schema is not an offender anymore.

        .. versionchanged:: 0.5
           Add ETAG to automatic fields check.

        .. versionchanged:: 0.4
           Checks against offending document versioning fields.
           Supports embedded data_relation with version.

        .. versionchanged:: 0.2
           Allow ID_FIELD in resource schema if not of 'objectid' type.

        .. versionchanged:: 0.1.1
           'collection' setting renamed to 'resource' (data_relation).
           Fix order of string arguments in exception message.

        .. versionchanged:: 0.1.0
           Validation for 'embeddable' fields.

        .. versionchanged:: 0.0.5
           Validation of the 'data_relation' field rule.
           Now collecting offending items in a list and inserting results into
           the exception message.
        """

        def validate_field_name(field):
            forbidden = ["$", "."]
            if any(x in field for x in forbidden):
                raise SchemaException(
                    "Field '%s' cannot contain any of the following: '%s'."
                    % (field, ", ".join(forbidden))
                )

        resource_settings = self.config["DOMAIN"][resource]

        # ensure automatically handled fields aren't defined
        fields = [eve.DATE_CREATED, eve.LAST_UPDATED, eve.ETAG]

        if resource_settings["versioning"] is True:
            fields += [
                self.config["VERSION"],
                self.config["LATEST_VERSION"],
                resource_settings["id_field"] + self.config["VERSION_ID_SUFFIX"],
            ]
        if resource_settings["soft_delete"] is True:
            fields += [self.config["DELETED"]]

        offenders = [field for field in fields if field in schema]
        if offenders:
            raise SchemaException(
                'field(s) "%s" not allowed in "%s" schema '
                "(they will be handled automatically)."
                % (", ".join(offenders), resource)
            )

        if not isinstance(schema, dict):
            return

        for field, ruleset in schema.items():
            validate_field_name(field)
            if isinstance(ruleset, dict) and "dict" in ruleset.get("type", ""):
                for field_ in ruleset.get("schema", {}):
                    validate_field_name(field_)

            # check data_relation rules
            if "data_relation" in ruleset:
                if "resource" not in ruleset["data_relation"]:
                    raise SchemaException(
                        "'resource' key is mandatory for "
                        "the 'data_relation' rule in "
                        "'%s: %s'" % (resource, field)
                    )
                if ruleset["data_relation"].get("embeddable", False):

                    # special care for data_relations with a version
                    value_field = ruleset["data_relation"]["field"]
                    if ruleset["data_relation"].get("version", False):
                        if (
                            "schema" not in ruleset
                            or value_field not in ruleset["schema"]
                            or "type" not in ruleset["schema"][value_field]
                        ):
                            raise SchemaException(
                                "Must defined type for '%s' in schema when "
                                "declaring an embedded data_relation with"
                                " version." % value_field
                            )

        # TODO are there other mandatory settings? Validate them here

    def set_defaults(self):
        """When not provided, fills individual resource settings with default
        or global configuration settings.

        .. versionchanged:: 0.4
           `versioning`
           `VERSION` added to automatic projection (when applicable)

        .. versionchanged:: 0.2
           Setting of actual resource defaults is delegated to
           _set_resource_defaults().

        .. versionchanged:: 0.1.1
           'default' values that could be assimilated to None (0, None, "")
           would be ignored.
           'dates' helper removed as datetime conversion is now handled by
           the eve.methods.common.data_parse function.

        .. versionchanged:: 0.1.0
          'embedding'.
           Support for optional HATEOAS.

        .. versionchanged:: 0.0.9
           'auth_username_field' renamed to 'auth_field'.
           Always include automatic fields despite of datasource projections.

        .. versionchanged:: 0.0.8
           'mongo_write_concern'

        .. versionchanged:: 0.0.7
           'extra_response_fields'

        .. versionchanged:: 0.0.6
           'datasource[projection]'
           'projection',
           'allow_unknown'

        .. versionchanged:: 0.0.5
           'auth_username_field'
           'filters',
           'sorting',
           'pagination'.

        .. versionchanged:: 0.0.4
           'defaults',
           'datasource',
           'public_methods',
           'public_item_methods',
           'allowed_roles',
           'allowed_item_roles'.

        .. versionchanged:: 0.0.3
           `item_title` default value.
        """

        for resource, settings in self.config["DOMAIN"].items():
            self._set_resource_defaults(resource, settings)

    def _set_resource_defaults(self, resource, settings):
        """Low-level method which sets default values for one resource.

        .. versionchanged:: 1.1.0
           Added 'mongo_query_whitelist'.

        .. versionchanged:: 0.6.2
           Fix: startup crash when both SOFT_DELETE and ALLOW_UNKNOWN are True.

           (#722).
        .. versionchanged:: 0.6.1
           Fix: inclusive projection defined for a datasource is ignored
           (#722).

        .. versionchanged:: 0.6
           Support for 'mongo_indexes'.

        .. versionchanged:: 0.5
           Don't set default projection if 'allow_unknown' is active (#497).
           'internal_resource'

        .. versionchanged:: 0.3
           Set projection to None when schema is not provided for the resource.
           Support for '_media' helper.

        .. versionchanged:: 0.2
           'resource_title',
           'default_sort',
           'embedded_fields'.
           Support for endpoint-level authentication classes.
        """
        settings.setdefault("url", resource)
        settings.setdefault("resource_methods", self.config["RESOURCE_METHODS"])
        settings.setdefault("public_methods", self.config["PUBLIC_METHODS"])
        settings.setdefault("allowed_roles", self.config["ALLOWED_ROLES"])
        settings.setdefault("allowed_read_roles", self.config["ALLOWED_READ_ROLES"])
        settings.setdefault("allowed_write_roles", self.config["ALLOWED_WRITE_ROLES"])
        settings.setdefault("cache_control", self.config["CACHE_CONTROL"])
        settings.setdefault("cache_expires", self.config["CACHE_EXPIRES"])

        settings.setdefault("id_field", self.config["ID_FIELD"])
        settings.setdefault("item_lookup_field", self.config["ITEM_LOOKUP_FIELD"])
        settings.setdefault("item_url", self.config["ITEM_URL"])
        settings.setdefault("resource_title", settings["url"])
        settings.setdefault("item_title", resource.rstrip("s").capitalize())
        settings.setdefault("item_lookup", self.config["ITEM_LOOKUP"])
        settings.setdefault("public_item_methods", self.config["PUBLIC_ITEM_METHODS"])
        settings.setdefault("allowed_item_roles", self.config["ALLOWED_ITEM_ROLES"])
        settings.setdefault(
            "allowed_item_read_roles", self.config["ALLOWED_ITEM_READ_ROLES"]
        )
        settings.setdefault(
            "allowed_item_write_roles", self.config["ALLOWED_ITEM_WRITE_ROLES"]
        )
        settings.setdefault("allowed_filters", self.config["ALLOWED_FILTERS"])
        settings.setdefault("sorting", self.config["SORTING"])
        settings.setdefault("embedding", self.config["EMBEDDING"])
        settings.setdefault("embedded_fields", [])
        settings.setdefault("pagination", self.config["PAGINATION"])
        settings.setdefault("projection", self.config["PROJECTION"])
        settings.setdefault("versioning", self.config["VERSIONING"])
        settings.setdefault("soft_delete", self.config["SOFT_DELETE"])
        settings.setdefault("bulk_enabled", self.config["BULK_ENABLED"])
        settings.setdefault("internal_resource", self.config["INTERNAL_RESOURCE"])
        settings.setdefault("etag_ignore_fields", None)
        # TODO make sure that this we really need the test below
        if settings["item_lookup"]:
            item_methods = self.config["ITEM_METHODS"]
        else:
            item_methods = eve.ITEM_METHODS
        settings.setdefault("item_methods", item_methods)
        settings.setdefault("auth_field", self.config["AUTH_FIELD"])
        settings.setdefault("allow_unknown", self.config["ALLOW_UNKNOWN"])
        settings.setdefault(
            "extra_response_fields", self.config["EXTRA_RESPONSE_FIELDS"]
        )
        settings.setdefault(
            "mongo_query_whitelist", self.config["MONGO_QUERY_WHITELIST"]
        )
        settings.setdefault("mongo_write_concern", self.config["MONGO_WRITE_CONCERN"])
        settings.setdefault("mongo_indexes", {})
        settings.setdefault("hateoas", self.config["HATEOAS"])
        settings.setdefault("authentication", self.auth if self.auth else None)
        settings.setdefault(
            "merge_nested_documents", self.config["MERGE_NESTED_DOCUMENTS"]
        )
        settings.setdefault(
            "normalize_dotted_fields", self.config["NORMALIZE_DOTTED_FIELDS"]
        )
        settings.setdefault("normalize_on_patch", self.config["NORMALIZE_ON_PATCH"])
        # empty schemas are allowed for read-only access to resources
        schema = settings.setdefault("schema", {})
        self.set_schema_defaults(schema, settings["id_field"])

        self._set_resource_datasource(resource, schema, settings)

    def _set_resource_datasource(self, resource, schema, settings):
        """Set the default values for the resource 'datasource' setting.

        .. versionadded:: 0.7
        """

        settings.setdefault("datasource", {})

        ds = settings["datasource"]
        ds.setdefault("source", resource)
        ds.setdefault("filter", None)
        ds.setdefault("default_sort", None)

        self._set_resource_projection(ds, schema, settings)
        aggregation = ds.setdefault("aggregation", None)
        if aggregation:
            aggregation.setdefault("options", {})

            # endpoints serving aggregation queries are read-only and do not
            # support item lookup.
            settings["resource_methods"] = ["GET"]
            settings["item_lookup"] = False

    def _set_resource_projection(self, ds, schema, settings):
        """Set datasource projection for a resource

        .. versionchanged:: 0.6.3
           Fix: If datasource source is specified no fields are included by
           default. Closes #842.

        .. versionadded:: 0.6.2
        """
        # get existing or empty projection setting
        projection = ds.get("projection", {})

        # If exclusion projections are defined, they are use for
        # concealing fields (rather than actual mongo exlusions).
        # If inclusion projections are defined, exclusion projections are
        # just ignored.
        # Enhance the projection with automatic fields.
        if schema and settings["allow_unknown"] is False:
            inclusion_projection = dict(
                [(k, v) for k, v in projection.items() if v == 1]
            )
            exclusion_projection = dict(
                [(k, v) for k, v in projection.items() if v == 0]
            )
            # if inclusion project is empty, add all fields not excluded
            if not inclusion_projection:
                projection.update(
                    dict(
                        (field, 1)
                        for field in schema
                        if field not in exclusion_projection
                    )
                )
            # enable retrieval of actual schema fields only. Eventual db
            # fields not included in the schema won't be returned.
            # despite projection, automatic fields are always included.
            projection[settings["id_field"]] = 1
            projection[self.config["LAST_UPDATED"]] = 1
            projection[self.config["DATE_CREATED"]] = 1
            projection[self.config["ETAG"]] = 1
            if settings["versioning"] is True:
                projection[self.config["VERSION"]] = 1
                projection[settings["id_field"] + self.config["VERSION_ID_SUFFIX"]] = 1

        ds.setdefault("projection", projection)

        if settings["soft_delete"] is True and projection:
            projection[self.config["DELETED"]] = 1

        # set projection and projection is always a dictionary
        ds["projection"] = projection

        # list of all media fields for the resource
        if isinstance(schema, dict):
            settings["_media"] = [
                field
                for field, definition in schema.items()
                if isinstance(definition, dict)
                and (
                    definition.get("type") == "media"
                    or (
                        definition.get("type") == "list"
                        and definition.get("schema", {}).get("type") == "media"
                    )
                )
            ]
        else:
            settings["_media"] = []

        if settings["_media"] and not self.media:
            raise ConfigException(
                "A media storage class of type "
                " eve.io.media.MediaStorage must be defined "
                'for "media" fields to be properly stored.'
            )

    def set_schema_defaults(self, schema, id_field):
        """When not provided, fills individual schema settings with default
        or global configuration settings.

        :param schema: the resource schema to be initialized with default
                       values

        .. versionchanged: 0.6
           Add default ID_FIELD to the schema, so documents with an existing
           ID_FIELD can also be stored.

        .. versionchanged: 0.0.7
           Setting the default 'field' value would not happen if the
           'data_relation' was nested deeper than the first schema level (#60).

        .. versionadded: 0.0.5
        """

        # Don't set id_field 'unique' since we already handle
        # DuplicateKeyConflict in the mongo layer. This also
        # avoids a performance hit (with 'unique' rule set, we would
        # end up with an extra db loopback on every insert).
        if isinstance(schema, dict):
            schema.setdefault(id_field, {"type": "objectid"})

        # set default 'field' value for all 'data_relation' rulesets, however
        # nested
        for data_relation in list(extract_key_values("data_relation", schema)):
            data_relation.setdefault("field", id_field)

    @property
    def api_prefix(self):
        """Prefix to API endpoints.

        .. versionadded:: 0.2
        """
        return api_prefix(self.config["URL_PREFIX"], self.config["API_VERSION"])

    def _add_resource_url_rules(self, resource, settings):
        """Builds the API url map for one resource. Methods are enabled for
        each mapped endpoint, as configured in the settings.

        .. versionchanged:: 0.5
           Don't add resource to url rules if it's flagged as internal.
           Strip regexes out of config.URLS helper. Closes #466.

        .. versionadded:: 0.2
        """
        self.config["SOURCES"][resource] = settings["datasource"]

        if settings["internal_resource"]:
            return

        url = "%s/%s" % (self.api_prefix, settings["url"])

        pretty_url = settings["url"]
        if "<" in pretty_url:
            pretty_url = (
                pretty_url[: pretty_url.index("<") + 1]
                + pretty_url[pretty_url.rindex(":") + 1 :]
            )
        self.config["URLS"][resource] = pretty_url

        # resource endpoint
        endpoint = resource + "|resource"
        self.add_url_rule(
            url,
            endpoint,
            view_func=collections_endpoint,
            methods=settings["resource_methods"] + ["OPTIONS"],
        )

        # item endpoint
        if settings["item_lookup"]:
            item_url = "%s/<%s:%s>" % (
                url,
                settings["item_url"],
                settings["item_lookup_field"],
            )

            endpoint = resource + "|item_lookup"
            self.add_url_rule(
                item_url,
                endpoint,
                view_func=item_endpoint,
                methods=settings["item_methods"] + ["OPTIONS"],
            )
            if "PATCH" in settings["item_methods"]:
                # support for POST with X-HTTP-Method-Override header for
                # clients not supporting PATCH. Also see item_endpoint() in
                # endpoints.py
                endpoint = resource + "|item_post_override"
                self.add_url_rule(
                    item_url, endpoint, view_func=item_endpoint, methods=["POST"]
                )

            # also enable an alternative lookup/endpoint if allowed
            lookup = settings.get("additional_lookup")
            if lookup:
                l_type = settings["schema"][lookup["field"]]["type"]
                if l_type == "integer":
                    item_url = "%s/<int:%s>" % (url, lookup["field"])
                else:
                    item_url = "%s/<%s:%s>" % (url, lookup["url"], lookup["field"])
                endpoint = resource + "|item_additional_lookup"
                self.add_url_rule(
                    item_url,
                    endpoint,
                    view_func=item_endpoint,
                    methods=["GET", "OPTIONS"],
                )

    def _init_url_rules(self):
        """Builds the API url map. Methods are enabled for each mapped
        endpoint, as configured in the settings.

        .. versionchanged:: 0.4
           Renamed from '_add_url_rules' to '_init_url_rules' to make code more
           DRY. Individual resource rules get built from register_resource now.

        .. versionchanged:: 0.2
           Delegate adding of resource rules to _add_resource_rules().

        .. versionchanged:: 0.1.1
           Simplified URL rules. Not using regexes anymore to return the
           endpoint URL to the endpoint function. This allows for nested
           endpoints to function properly.

        .. versionchanged:: 0.0.9
           Handle the case of 'additional_lookup' field being an integer.

        .. versionchanged:: 0.0.5
           Support for Cross-Origin Resource Sharing. 'OPTIONS' method is
           explicitly routed to standard endpoints to allow for proper CORS
           processing.

        .. versionchanged:: 0.0.4
           config.SOURCES. Maps resources to their datasources.

        .. versionchanged:: 0.0.3
           Support for API_VERSION as an endpoint prefix.
        """
        # helpers
        self.config["URLS"] = {}  # maps resources to urls
        self.config["SOURCES"] = {}  # maps resources to their datasources

        # we choose not to care about trailing slashes at all.
        # Both '/resource/' and '/resource' will work, same with
        # '/resource/<id>/' and '/resource/<id>'
        self.url_map.strict_slashes = False

        # home page (API entry point)
        self.add_url_rule(
            "%s/" % self.api_prefix,
            "home",
            view_func=home_endpoint,
            methods=["GET", "OPTIONS"],
        )

    def register_resource(self, resource, settings):
        """Registers new resource to the domain.

        Under the hood this validates given settings, updates default values
        and adds necessary URL routes (builds api url map).

        If there exists some resource with given name, it is overwritten.

        :param resource: resource name.
        :param settings: settings for given resource.

        .. versionchanged:: 0.6
           Support for 'mongo_indexes'.

        .. versionchanged:: 0.4
           Support for document versioning.


        .. versionadded:: 0.2
        """

        # this line only makes sense when we call this function outside of the
        # standard Eve setup routine, but it doesn't hurt to still call it
        self.config["DOMAIN"][resource] = settings

        # set up resource
        self._set_resource_defaults(resource, settings)
        self._validate_resource_settings(resource, settings)
        self._add_resource_url_rules(resource, settings)

        # add rules for version control collections if appropriate
        if settings["versioning"] is True:
            versioned_resource = resource + self.config["VERSIONS"]
            self.config["DOMAIN"][versioned_resource] = copy.deepcopy(
                self.config["DOMAIN"][resource]
            )
            self.config["DOMAIN"][versioned_resource]["datasource"][
                "source"
            ] += self.config["VERSIONS"]
            self.config["SOURCES"][versioned_resource] = copy.deepcopy(
                self.config["SOURCES"][resource]
            )
            self.config["SOURCES"][versioned_resource]["source"] += self.config[
                "VERSIONS"
            ]
            # the new versioned resource also needs URL rules
            self._add_resource_url_rules(
                versioned_resource, self.config["DOMAIN"][versioned_resource]
            )

        # create the mongo db indexes
        ensure_mongo_indexes(self, resource)

        # flask-pymongo compatibility.
        if "MONGO_OPTIONS" in self.config["DOMAIN"]:
            connect = self.config["DOMAIN"]["MONGO_OPTIONS"].get("connect", True)
            self.config["DOMAIN"]["MONGO_CONNECT"] = connect

    def register_error_handlers(self):
        """Register custom error handlers so we make sure that all errors
        return a parseable body.

        .. versionchanged: 0.6.5
           Replace obsolete app.register_error_handler_spec() with
           register_error_handler(), which works with Flask>=0.11.1. Closes
           #904, #945.

        .. versionadded:: 0.4
        """
        for code in self.config["STANDARD_ERRORS"]:
            self.register_error_handler(code, error_endpoint)

    def _init_oplog(self):
        """If enabled, configures the OPLOG endpoint.

        .. versionchanged:: 0.7
           Add 'u' field to oplog audit schema. See #846.

        .. versionadded:: 0.5
        """
        name, endpoint, audit, extra = (
            self.config["OPLOG_NAME"],
            self.config["OPLOG_ENDPOINT"],
            self.config["OPLOG_AUDIT"],
            self.config["OPLOG_RETURN_EXTRA_FIELD"],
        )

        settings = self.config["DOMAIN"].setdefault(name, {})

        settings.setdefault("datasource", {"source": name})

        # this endpoint is always read-only
        settings["resource_methods"] = ["GET"]
        settings["item_methods"] = ["GET"]

        if endpoint:
            settings.setdefault("url", endpoint)
            settings["internal_resource"] = False
        else:
            # make it an internal resource
            settings["url"] = name
            settings["internal_resource"] = True

        # schema is also fixed. it is needed because otherwise we
        # would end up exposing the AUTH_FIELD when User-Restricted-
        # Resource-Access is enabled.
        settings["schema"] = {"r": {}, "o": {}, "i": {}}
        if extra:
            settings["schema"].update({"extra": {}})
        if audit:
            settings["schema"].update({"ip": {}, "c": {}, "u": {}})

    def _init_media_endpoint(self):
        endpoint = self.config["MEDIA_ENDPOINT"]

        if endpoint:
            media_url = "%s/%s/<%s:_id>" % (
                self.api_prefix,
                endpoint,
                self.config["MEDIA_URL"],
            )
            self.add_url_rule(
                media_url, "media", view_func=media_endpoint, methods=["GET", "OPTIONS"]
            )

    def _init_schema_endpoint(self):
        """Configures the schema endpoint if set in configuration."""
        endpoint = self.config["SCHEMA_ENDPOINT"]

        if endpoint:
            schema_url = "%s/%s" % (self.api_prefix, endpoint)
            # add schema collections url
            self.add_url_rule(
                schema_url,
                "schema_collection",
                view_func=schema_collection_endpoint,
                methods=["GET", "OPTIONS"],
            )
            # add schema item url
            self.add_url_rule(
                schema_url + "/<resource>",
                "schema_item",
                view_func=schema_item_endpoint,
                methods=["GET", "OPTIONS"],
            )

    def __call__(self, environ, start_response):
        """If HTTP_X_METHOD_OVERRIDE is included with the request and method
        override is allowed, make sure the override method is returned to Eve
        as the request method, so normal routing and method validation can be
        performed.
        """
        if self.config["ALLOW_OVERRIDE_HTTP_METHOD"]:
            environ["REQUEST_METHOD"] = environ.get(
                "HTTP_X_HTTP_METHOD_OVERRIDE", environ["REQUEST_METHOD"]
            ).upper()
        return super(Eve, self).__call__(environ, start_response)
