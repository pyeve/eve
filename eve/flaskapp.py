# -*- coding: utf-8 -*-

"""
    eve.flaskapp
    ~~~~~~~~~~~~

    This module implements the central WSGI application object as a Flask
    subclass.

    :copyright: (c) 2013 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import eve
import sys
import os
from flask import Flask
from werkzeug.routing import BaseConverter
from werkzeug.serving import WSGIRequestHandler
from eve.io.mongo import Mongo, Validator
from eve.exceptions import ConfigException, SchemaException
from eve.endpoints import collections_endpoint, item_endpoint, home_endpoint
from eve.utils import api_prefix, extract_key_values
from events import Events


class EveWSGIRequestHandler(WSGIRequestHandler):
    """ Extend werkzeug request handler to include current Eve version in all
    responses, which is super-handy for debugging.
    """
    @property
    def server_version(self):
        return 'Eve/%s ' % eve.__version__ + super(EveWSGIRequestHandler,
                                                   self).server_version


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
    :param kwargs: optional, standard, Flask parameters.

    .. versionchanged:: 0.2
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
    supported_resource_methods = ['GET', 'POST', 'DELETE']

    #: Allowed methods for item endpoints
    supported_item_methods = ['GET', 'PATCH', 'DELETE', 'PUT']

    def __init__(self, import_name=__package__, settings='settings.py',
                 validator=Validator, data=Mongo, auth=None, redis=None,
                 **kwargs):
        """Eve main WSGI app is implemented as a Flask subclass. Since we want
        to be able to launch our API by simply invoking Flask's run() method,
        we need to enhance our super-class a little bit.

        The tasks we need to accomplish are:

            1. enbale regex routing
            2. load and validate custom API settings,
            3. enable API endpoints
            4. set the validator class used to validate incoming objects
            5. activate the chosen data layer
            6. instance the authentication layer if needed
            7. set the redis instance to be used by the Rate-Limiting feature

        .. versionchanged:: 0.2
           Validate and set defaults for each resource
        """

        # TODO should we support standard Flask parameters as well?
        super(Eve, self).__init__(import_name, **kwargs)
        # enable regex routing
        self.url_map.converters['regex'] = RegexConverter
        self.validator = validator
        self.settings = settings

        self.load_config()
        self.validate_domain_struct()
        # validate and set defaults for each resource
        for resource, settings in self.config['DOMAIN'].items():
            self._set_resource_defaults(resource, settings)
            self._validate_resource_settings(resource, settings)
        self._add_url_rules()

        self.data = data(self)
        self.auth = auth() if auth else None
        self.redis = redis

    def run(self, host=None, port=None, debug=None, **options):
        """Pass our own subclass of :class:`werkzeug.serving.WSGIRequestHandler
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
                        information.        """

        options.setdefault('request_handler', EveWSGIRequestHandler)
        super(Eve, self).run(host, port, debug, **options)

    def load_config(self):
        """API settings are loaded from standard python modules. First from
        `settings.py`(or alternative name/path passed as an argument) and
        then, when defined, from the file specified in the
        `EVE_SETTINGS` environment variable.

        Since we are a Flask subclass, any configuration value supported by
        Flask itself is available (besides Eve's proper settings).

        .. versionchanged:: 0.2
           Allow use of a dict object as settings.
        """

        # load defaults
        self.config.from_object('eve.default_settings')

        # overwrite the defaults with custom user settings
        if isinstance(self.settings, dict):
            self.config.update(self.settings)
        else:
            if os.path.isabs(self.settings):
                pyfile = self.settings
            else:
                abspath = os.path.abspath(os.path.dirname(sys.argv[0]))
                pyfile = os.path.join(abspath, self.settings)
            self.config.from_pyfile(pyfile)

        #overwrite settings with custom environment variable
        envvar = 'EVE_SETTINGS'
        if os.environ.get(envvar):
            self.config.from_envvar(envvar)

    def validate_domain_struct(self):
        """ Validates that Eve configuration settings conform to the
        requirements.
        """
        try:
            domain = self.config['DOMAIN']
        except:
            raise ConfigException('DOMAIN dictionary missing or wrong.')
        if not isinstance(domain, dict):
            raise ConfigException('DOMAIN must be a dict.')
        if len(domain) == 0:
            raise ConfigException('DOMAIN must contain at least one resource.')

    def validate_config(self):
        """ Makes sure that REST methods expressed in the configuration
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
        self.validate_methods(self.supported_resource_methods,
                              self.config.get('RESOURCE_METHODS'),
                              'resource')

        # make sure that global item methods are supported.
        self.validate_methods(self.supported_item_methods,
                              self.config.get('ITEM_METHODS'),
                              'item')

        # make sure that individual resource/item methods are supported.
        for resource, settings in self.config['DOMAIN'].items():
            self._validate_resource_settings(resource, settings)

    def _validate_resource_settings(self, resource, settings):
        """ Validates one resource in configuration settings.

        :param resource: name of the resource which settings refer to.
        :param settings: settings of resource to be validated.

        .. versionadded:: 0.2
        """
        self.validate_methods(self.supported_resource_methods,
                              settings['resource_methods'],
                              '[%s] resource ' % resource)
        self.validate_methods(self.supported_item_methods,
                              settings['item_methods'],
                              '[%s] item ' % resource)

        # while a resource schema is optional for read-only access,
        # it is mandatory for write-access to resource/items.
        if 'POST' in settings['resource_methods'] or \
           'PATCH' in settings['item_methods']:
            if len(settings['schema']) == 0:
                raise ConfigException('A resource schema must be provided '
                                      'when POST or PATCH methods are allowed'
                                      'for a resource [%s].' % resource)

        self.validate_roles('allowed_roles', settings, resource)
        self.validate_roles('allowed_item_roles', settings, resource)
        self.validate_schema(resource, settings['schema'])

    def validate_roles(self, directive, candidate, resource):
        """ Validates that user role directives are syntactically and formally
        adeguate.

        :param directive: either 'allowed_roles' or 'allow_item_roles'.
        :param candidate: the candidate setting to be validated.
        :param resource: name of the resource to which the candidate settings
                         refer to.

        .. versionadded:: 0.0.4
        """
        roles = candidate[directive]
        if roles is not None and (not isinstance(roles, list) or not
                                  len(roles)):
            raise ConfigException("'%s' must be a non-empty list, or None "
                                  "[%s]." % (directive, resource))

    def validate_methods(self, allowed, proposed, item):
        """ Compares allowed and proposed methods, raising a `ConfigException`
        when they don't match.

        :param allowed: a list of supported (allowed) methods.
        :param proposed: a list of proposed methods.
        :param item: name of the item to which the methods would be applied.
                     Used when raising the exception.
        """
        diff = set(proposed) - set(allowed)
        if diff:
            raise ConfigException('Unallowed %s method(s): %s. '
                                  'Supported: %s' %
                                  (item, ', '.join(diff),
                                   ', '.join(allowed)))

    def validate_schema(self, resource, schema):
        """ Validates a resource schema.

        :param resource: resource name.
        :param schema: schema definition for the resource.

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
        # TODO are there other mandatory settings? Validate them here
        offenders = []
        if eve.DATE_CREATED in schema:
            offenders.append(eve.DATE_CREATED)
        if eve.LAST_UPDATED in schema:
            offenders.append(eve.LAST_UPDATED)
        if eve.ID_FIELD in schema:
            offenders.append(eve.ID_FIELD)
        if offenders:
            raise SchemaException('field(s) "%s" not allowed in "%s" schema '
                                  '(they will be handled automatically).'
                                  % (', '.join(offenders), resource))

        for field, ruleset in schema.items():
            if 'data_relation' in ruleset:
                if 'resource' not in ruleset['data_relation']:
                    raise SchemaException("'resource' key is mandatory for "
                                          "the 'data_relation' rule in "
                                          "'%s: %s'" % (resource, field))
                # If the field is listed as `embeddable`
                # it must be type == 'objectid'
                # TODO: allow serializing a list( type == 'objectid')
                if ruleset['data_relation'].get('embeddable', False):
                    if ruleset['type'] != 'objectid':
                        raise SchemaException(
                            "In order for the 'data_relation' rule to be "
                            "embeddable it must be of type 'objectid'"
                        )

    def set_defaults(self):
        """ When not provided, fills individual resource settings with default
        or global configuration settings.

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

        for resource, settings in self.config['DOMAIN'].items():
            self._set_resource_defaults(resource, settings)

    def _set_resource_defaults(self, resource, settings):
        """ Low-level method which sets default values for one resource. """
        settings.setdefault('url', resource)
        settings.setdefault('resource_methods',
                            self.config['RESOURCE_METHODS'])
        settings.setdefault('public_methods',
                            self.config['PUBLIC_METHODS'])
        settings.setdefault('allowed_roles', self.config['ALLOWED_ROLES'])
        settings.setdefault('cache_control', self.config['CACHE_CONTROL'])
        settings.setdefault('cache_expires', self.config['CACHE_EXPIRES'])

        settings.setdefault('item_lookup_field',
                            self.config['ITEM_LOOKUP_FIELD'])
        settings.setdefault('item_url', self.config['ITEM_URL'])
        settings.setdefault('item_title',
                            resource.rstrip('s').capitalize())
        settings.setdefault('item_lookup', self.config['ITEM_LOOKUP'])
        settings.setdefault('public_item_methods',
                            self.config['PUBLIC_ITEM_METHODS'])
        settings.setdefault('allowed_item_roles',
                            self.config['ALLOWED_ITEM_ROLES'])
        settings.setdefault('allowed_filters',
                            self.config['ALLOWED_FILTERS'])
        settings.setdefault('sorting', self.config['SORTING'])
        settings.setdefault('embedding', self.config['EMBEDDING'])
        settings.setdefault('pagination', self.config['PAGINATION'])
        settings.setdefault('projection', self.config['PROJECTION'])
        # TODO make sure that this we really need the test below
        if settings['item_lookup']:
            item_methods = self.config['ITEM_METHODS']
        else:
            item_methods = eve.ITEM_METHODS
        settings.setdefault('item_methods', item_methods)
        settings.setdefault('auth_field',
                            self.config['AUTH_FIELD'])
        settings.setdefault('allow_unknown', self.config['ALLOW_UNKNOWN'])
        settings.setdefault('extra_response_fields',
                            self.config['EXTRA_RESPONSE_FIELDS'])
        settings.setdefault('mongo_write_concern',
                            self.config['MONGO_WRITE_CONCERN'])
        settings.setdefault('hateoas',
                            self.config['HATEOAS'])

        # empty schemas are allowed for read-only access to resources
        schema = settings.setdefault('schema', {})
        self.set_schema_defaults(schema)

        datasource = {}
        settings.setdefault('datasource', datasource)
        settings['datasource'].setdefault('source', resource)
        settings['datasource'].setdefault('filter', None)

        # enable retrieval of actual schema fields only. Eventual db
        # fields not included in the schema won't be returned.
        default_projection = {}
        default_projection.update(dict((field, 1) for (field) in schema))
        projection = settings['datasource'].setdefault('projection',
                                                       default_projection)
        # despite projection, automatic fields are always included.
        projection[self.config['ID_FIELD']] = 1
        projection[self.config['LAST_UPDATED']] = 1
        projection[self.config['DATE_CREATED']] = 1

        # 'defaults' helper set contains the names of fields with
        # default values in their schema definition.

        # TODO support default values for embedded documents.
        settings['defaults'] = \
            set(field for field, definition in schema.items()
                if 'default' in definition)

    def set_schema_defaults(self, schema):
        """ When not provided, fills individual schema settings with default
        or global configuration settings.

        :param schema: the resource schema to be initialized with default
                       values

        .. versionchanged: 0.0.7
           Setting the default 'field' value would not happen if the
           'data_relation' was nested deeper than the first schema level (#60).

        .. versionadded: 0.0.5
        """
        # TODO fill schema{} defaults, like field type, etc.

        # set default 'field' value for all 'data_relation' rulesets, however
        # nested
        for data_relation in list(extract_key_values('data_relation', schema)):
            data_relation.setdefault('field', self.config['ID_FIELD'])

    @property
    def api_prefix(self):
        """
        Prefix to API endpoints.

        .. versionadded:: 0.2
        """
        return api_prefix(self.config['URL_PREFIX'],
                          self.config['API_VERSION'])

    def _add_resource_url_rules(self, resource, settings):
        """ Builds the API url map for one resource. Methods are enabled for
        each mapped endpoint, as configured in the settings.

        .. versionadded:: 0.2
        """
        url = '%s/%s' % (self.api_prefix, settings['url'])
        self.config['RESOURCES'][url] = resource
        self.config['URLS'][resource] = settings['url']
        self.config['SOURCES'][resource] = settings['datasource']

        # resource endpoint
        self.add_url_rule(url, view_func=collections_endpoint,
                          methods=settings['resource_methods'] +
                          ['OPTIONS'])

        # item endpoint
        if settings['item_lookup']:
            item_url = '%s/<regex("%s"):%s>' % \
                (url, settings['item_url'], settings['item_lookup_field'])

            self.add_url_rule(item_url, view_func=item_endpoint,
                              methods=settings['item_methods']
                              + ['OPTIONS'])
            if 'PATCH' in settings['item_methods']:
                # support for POST with X-HTTM-Method-Override header
                # for clients not supporting PATCH. Also see
                # item_endpoint() in endpoints.py
                self.add_url_rule(item_url, view_func=item_endpoint,
                                  methods=['POST'])

            # also enable an alternative lookup/endpoint if allowed
            lookup = settings.get('additional_lookup')
            if lookup:
                l_type = settings['schema'][lookup['field']]['type']
                if l_type == 'integer':
                    item_url = '%s/<int:%s>' % (url, lookup['field'])
                else:
                    item_url = '%s/<regex("%s"):%s>' % (url,
                                                        lookup['url'],
                                                        lookup['field'])
                self.add_url_rule(item_url, view_func=item_endpoint,
                                  methods=['GET', 'OPTIONS'])

    def _add_url_rules(self):
        """ Builds the API url map. Methods are enabled for each mapped
        endpoint, as configured in the settings.

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
        self.config['RESOURCES'] = {}  # maps urls to resources (DOMAIN keys)
        self.config['URLS'] = {}       # maps resources to urls
        self.config['SOURCES'] = {}    # maps resources to their datasources

        # we choose not to care about trailing slashes at all.
        # Both '/resource/' and '/resource' will work, same with
        # '/resource/<id>/' and '/resource/<id>'
        self.url_map.strict_slashes = False

        # home page (API entry point)
        self.add_url_rule('%s/' % self.api_prefix, 'home',
                          view_func=home_endpoint, methods=['GET', 'OPTIONS'])

        for resource, settings in self.config['DOMAIN'].items():
            self._add_resource_url_rules(resource, settings)

    def register_resource(self, resource, settings):
        """ Registers new resource to the domain.

        Under the hood this validates given settings, updates default values
        and adds necessary URL routes (builds api url map).

        If there exists some resource with given name, it is overwritten.

        :param resource: resource name.
        :param settings: settings for given resource.

        .. versionadded:: 0.2
        """
        self.config['DOMAIN'][resource] = settings
        self._set_resource_defaults(resource, settings)
        self._validate_resource_settings(resource, settings)
        self._add_resource_url_rules(resource, settings)
