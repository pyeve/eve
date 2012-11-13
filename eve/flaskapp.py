"""
    eve.flaskapp
    ~~~~~~~~~~~~

    This module implements the central WSGI application object as a Flask
    subclass.

    :copyright: (c) 2012 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""

import eve
from io.mongo import Mongo, Validator
from flask import Flask
from werkzeug.routing import BaseConverter
from exceptions import ConfigException
from endpoints import collections_endpoint, item_endpoint, home_endpoint


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

    :param settings: the name of the settings file.  Defaults to `settings.py`.
    :param validator: custom validation class. Must be a
                      :class:`~cerberus.Validator` subclass. Defaults to
                      :class:`eve.io.mongo.Validator`.
    :param data: the data layer class. Must be a :class:`~eve.io.DataLayer`
                 subclass. Defaults to :class:`~eve.io.Mongo`.
    """
    def __init__(self, settings='settings.py', validator=Validator,
                 data=Mongo):
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
        super(Eve, self).__init__(__package__)
        # enable regex routing
        self.url_map.converters['regex'] = RegexConverter

        self.settings = settings
        self.validator = validator

        self.load_config()
        self.set_defaults()
        self.validate_config()
        self.add_url_rules()

        # instantiate the data layer. Defaults to eve.io.Mongo
        self.data = data(self)

    def load_config(self):
        """API settings are loaded from standard python modules. First from
        `settings.py`(or alternative name/path provided as class argument) and
        then, when defined and if available, from the file specified in the
        `EVE_SETTINGS` environment variable.

        Since we are a Flask subclass, any configuration value supported by
        Flask itself is available (besides Eve's proper settings).
        """

        # load defaults
        self.config.from_object(eve)

        try:
            # settings in these files will replace the defaults. The same
            # will happen to values loaded from `settings.py` and then
            # overridden by the contents of the `EVE_SETTINGS` file.
            self.config.from_pyfile(self.settings)
            self.config.from_envvar('EVE_SETTINGS')
        except:
            pass

    def validate_config(self):
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

        self.validate_config_methods()
        self.validate_schemas()

    def validate_config_methods(self):
        """ Makes sure that REST methods expressed in the configuration
        settings are supported.
        """

        supported_resource_methods = ['GET', 'POST']
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
                                  settings['methods'],
                                  '[%s] resource ' % resource)
            self.validate_methods(supported_item_methods,
                                  settings['item_methods'],
                                  '[%s] item ' % resource)

            # while a resource schema is optional for read-only access,
            # it is mandatory for write-access resource/items.
            if 'POST' in settings['methods'] or \
               'PATCH' in settings['item_methods']:
                if len(settings['schema']) == 0:
                    print settings['methods'], settings['item_methods']
                    raise ConfigException('A resource schema must be provided '
                                          'when POST or PATCH methods are '
                                          'allowed for a resource (%s).' %
                                          resource)

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

    def validate_schemas(self):
        # TODO are there other mandatory settings items? Validate them here
        pass

    def set_defaults(self):
        """ When not provided, fills individual resource settings with default
        or global configuration settings.
        """

        for resource, settings in self.config['DOMAIN'].items():
            settings.setdefault('url', resource)
            settings.setdefault('methods', self.config['RESOURCE_METHODS'])
            settings.setdefault('cache_control', self.config['CACHE_CONTROL'])
            settings.setdefault('cache_expires', self.config['CACHE_EXPIRES'])

            settings.setdefault('item_lookup_field',
                                self.config['ITEM_LOOKUP_FIELD'])
            settings.setdefault('item_url', self.config['ITEM_URL'])
            settings.setdefault('item_cache_control',
                                self.config['ITEM_CACHE_CONTROL'])
            settings.setdefault('item_lookup', self.config['ITEM_LOOKUP'])
            if settings['item_lookup']:
                item_methods = self.config['ITEM_METHODS']
            else:
                item_methods = eve.ITEM_METHODS
            settings.setdefault('item_methods', item_methods)

            # empty schemas are allowed for read-only access to resources
            schema = settings.setdefault('schema', {})

            # TODO fill schema{} defaults, like field type, etc.

            # the `dates` helper set contains the names of the schema fields
            # definited as `datetime` types. It will come in handy when
            # we will be parsing incoming documents
            settings['dates'] = \
                set(field for field, definition in schema.items()
                    if definition.get('type') == 'datetime')

    def add_url_rules(self):
        """ Builds the API url map. Methods are enabled for each mapped
        endpoint, as configured in the settings.
        """
        # helpers
        resources = dict()     # maps urls to resources (DOMAIN keys)
        urls = dict()          # maps resources to urls

        # general API prefix
        url_prefix = self.config['URL_PREFIX']

        # home page (API entry point)
        self.add_url_rule('%s/' % url_prefix, 'home', home_endpoint)

        for resource, settings in self.config['DOMAIN'].items():
            resources[settings['url']] = resource
            urls[resource] = settings['url']

            # resource endpoint
            url = '/<regex("%s"):url>/' % settings['url']
            url = '%s%s' % (url_prefix.rstrip('/'), url)
            self.add_url_rule(url, view_func=collections_endpoint,
                              methods=settings['methods'])

            # item endpoint
            if settings['item_lookup'] is True:
                item_url = '%s<regex("%s"):%s>/' % \
                    (url,
                     settings['item_url'],
                     settings['item_lookup_field'])

                self.add_url_rule(item_url, view_func=item_endpoint,
                                  methods=settings['item_methods'])
                if 'PATCH' in settings['item_methods']:
                    # support for POST with X-HTTM-Method-Override header,
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
