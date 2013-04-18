# -*- coding: utf-8 -*-

"""
    eve.flaskapp
    ~~~~~~~~~~~~

    This module implements the central WSGI application object as a Flask
    subclass.

    :copyright: (c) 2012 by Nicola Iarocci.
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
from eve.utils import api_prefix


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


class Eve(Flask):
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
    :param kwargs: optional, standard, Flask parameters.
    """
    def __init__(self, import_name=__package__, settings='settings.py',
                 validator=Validator, data=Mongo, auth=None, **kwargs):
        """Eve main WSGI app is implemented as a Flask subclass. Since we want
        to be able to launch our API by simply invoking Flask's run() method,
        we need to enhance our super-class a little bit.

        The tasks we need to accomplish are:

            1. enbale regex routing
            2. load and validate custom API settings,
            3. enable API endpoints
            4. set the validator class used to validate incoming objects
            5. activate the chosen data layer
        """

        # TODO should we support standard Flask parameters as well?
        super(Eve, self).__init__(import_name, **kwargs)
        # enable regex routing
        self.url_map.converters['regex'] = RegexConverter
        self.validator = validator
        self.settings = settings

        self.load_config()
        self.validate_domain_struct()
        self.set_defaults()
        self.validate_config()
        #self.validate_schemas()
        self._add_url_rules()

        self.data = data(self)
        self.auth = auth() if auth else None

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
        """

        # load defaults
        self.config.from_object('eve.default_settings')

        # overwrite the defaults with custom user settings:

        # TODO perhaps we should support non-existing settings file, in order
        # to allow for envvar_only scenarios. However, we should probably
        # issue a warning
        if os.path.isabs(self.settings):
            pyfile = self.settings
        else:
            # assume the path is relative to the calling script folder
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

        .. versionchanged:: 0.0.4
           Support for 'allowed_roles' and 'allowed_item_roles'

        .. versionchanged:: 0.0.2
            Support for DELETE resource method.
        """

        supported_resource_methods = ['GET', 'POST', 'DELETE']
        supported_item_methods = ['GET', 'PATCH', 'DELETE']

        # make sure that global resource methods are supported.
        self.validate_methods(supported_resource_methods,
                              self.config.get('RESOURCE_METHODS'),
                              'resource')

        # make sure that global item methods are supported.
        self.validate_methods(supported_item_methods,
                              self.config.get('ITEM_METHODS'),
                              'item')

        # make sure that individual resource/item methods are supported.
        for resource, settings in self.config['DOMAIN'].items():
            self.validate_methods(supported_resource_methods,
                                  settings['resource_methods'],
                                  '[%s] resource ' % resource)
            self.validate_methods(supported_item_methods,
                                  settings['item_methods'],
                                  '[%s] item ' % resource)

            # while a resource schema is optional for read-only access,
            # it is mandatory for write-access to resource/items.
            if 'POST' in settings['resource_methods'] or \
               'PATCH' in settings['item_methods']:
                if len(settings['schema']) == 0:
                    raise ConfigException('A resource schema must be provided '
                                          'when POST or PATCH methods are '
                                          'allowed for a resource [%s].' %
                                          resource)

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
                                  % (resource, ', '.join(offenders)))

        for field, ruleset in schema.items():
            if 'data_relation' in ruleset:
                if 'collection' not in ruleset['data_relation']:
                    raise SchemaException("'collection' key is mandatory for "
                                          "the 'data_relation' rule in "
                                          "'%s: %s'" % (resource, field))

    def set_defaults(self):
        """ When not provided, fills individual resource settings with default
        or global configuration settings.

        .. versionchanged:: 0.0.6
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
            settings.setdefault('url', resource)
            settings.setdefault('resource_methods', self.config['RESOURCE_METHODS'])
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
            settings.setdefault('filters', self.config['FILTERS'])
            settings.setdefault('sorting', self.config['SORTING'])
            settings.setdefault('pagination', self.config['PAGINATION'])
            settings.setdefault('projection', self.config['PROJECTION'])
            # TODO make sure that this we really need the test below
            if settings['item_lookup']:
                item_methods = self.config['ITEM_METHODS']
            else:
                item_methods = eve.ITEM_METHODS
            settings.setdefault('item_methods', item_methods)
            settings.setdefault('auth_username_field',
                                self.config['AUTH_USERNAME_FIELD'])
            settings.setdefault('allow_unknown', self.config['ALLOW_UNKNOWN'])

            datasource = {}
            settings.setdefault('datasource', datasource)
            settings['datasource'].setdefault('source', resource)
            settings['datasource'].setdefault('filter', None)
            settings['datasource'].setdefault('projection', None)

            # empty schemas are allowed for read-only access to resources
            schema = settings.setdefault('schema', {})
            self.set_schema_defaults(schema)

            # `dates` helper set contains the names of the schema fields
            # defined as `datetime` types. It will come in handy when
            # we will be parsing incoming documents

            # TODO support date fields for embedded documents.
            settings['dates'] = \
                set(field for field, definition in schema.items()
                    if definition.get('type') == 'datetime')

            # 'defaults' helper set contains the names of fields with
            # default values in their schema definition.

            # TODO support default values for embedded documents.
            settings['defaults'] = \
                set(field for field, definition in schema.items()
                    if definition.get('default'))

    def set_schema_defaults(self, schema):
        """ When not provided, fills individual schema settings with default
        or global configuration settings.

        :param schema: the resoursce schema to be intialized with default
                       values

        .. versionadded: 0.0.5
        """
        # TODO fill schema{} defaults, like field type, etc.
        for field, ruleset in schema.items():
            if 'data_relation' in ruleset:
                ruleset['data_relation'].setdefault('field',
                                                    self.config['ID_FIELD'])

    def _add_url_rules(self):
        """ Builds the API url map. Methods are enabled for each mapped
        endpoint, as configured in the settings.

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
        resources = {}     # maps urls to resources (DOMAIN keys)
        urls = {}          # maps resources to urls
        datasources = {}   # maps resources to their datasources

        prefix = api_prefix(self.config['URL_PREFIX'],
                            self.config['API_VERSION'])

        # home page (API entry point)
        self.add_url_rule('%s/' % prefix, 'home', view_func=home_endpoint,
                          methods=['GET', 'OPTIONS'])

        for resource, settings in self.config['DOMAIN'].items():
            resources[settings['url']] = resource
            urls[resource] = settings['url']
            datasources[resource] = settings['datasource']

            # resource endpoint
            url = '%s/<regex("%s"):url>/' % (prefix, settings['url'])
            self.add_url_rule(url, view_func=collections_endpoint,
                              methods=settings['resource_methods'] + ['OPTIONS'])

            # item endpoint
            if settings['item_lookup']:
                item_url = '%s<regex("%s"):%s>/' % \
                    (url,
                     settings['item_url'],
                     settings['item_lookup_field'])

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
                add_lookup = settings.get('additional_lookup')
                if add_lookup:
                    item_url = '%s<regex("%s"):%s>/' % (url,
                                                        add_lookup['url'],
                                                        add_lookup['field'])
                    self.add_url_rule(item_url, view_func=item_endpoint,
                                      methods=['GET'])
        self.config['RESOURCES'] = resources
        self.config['URLS'] = urls
        self.config['SOURCES'] = datasources
