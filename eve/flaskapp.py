import eve
from eve.io import Mongo
from eve.validation import Validator
from flask import Flask
from werkzeug.routing import BaseConverter
from exceptions import ConfigException
from endpoints import collections_endpoint, item_endpoint, home_endpoint


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


class Eve(Flask):
    def __init__(self, *args, **kwargs):

        validator_cls = kwargs.get('validator', None)
        try:
            kwargs.pop('validator')
        except KeyError:
            pass

        datalayer_cls = kwargs.get('data', None)
        try:
            kwargs.pop('data')
        except KeyError:
            pass

        self.settings = kwargs.get('settings', 'settings.py')
        try:
            kwargs.pop('settings')
        except KeyError:
            pass

        super(Eve, self).__init__(__package__, **kwargs)

        self.url_map.converters['regex'] = RegexConverter

        self.load_config()
        self.set_defaults()
        self.validate_config()
        self.add_url_rules()

        # these must stay at the bottom
        self.validator = validator_cls if validator_cls else Validator
        self.data = datalayer_cls(self) if datalayer_cls else Mongo(self)

    def load_config(self):
        self.config.from_object(eve)

        try:
            self.config.from_pyfile(self.settings)
            self.config.from_envvar('EVE_SETTINGS')
        except:
            pass

    def validate_config(self):
        try:
            domain = self.config['DOMAIN']
        except:
            raise ConfigException('DOMAIN dictionary missing or wrong.')
        if not isinstance(domain, dict):
            raise ConfigException('DOMAIN must be a dict.')
        if len(domain) == 0:
            raise ConfigException('DOMAIN must contain at least one resource.')

        self.validate_config_methods()
        #self.validate_schemas()

    def validate_config_methods(self):
        supported_resource_methods = ['GET', 'POST']
        supported_item_methods = ['GET', 'PATCH', 'DELETE']

        self.validate_methods(supported_resource_methods,
                              self.config.get('RESOURCE_METHODS'),
                              'resource')

        self.validate_methods(supported_item_methods,
                              self.config.get('ITEM_METHODS'),
                              'item')

        for resource, settings in self.config['DOMAIN'].items():
            self.validate_methods(supported_resource_methods,
                                  settings['methods'],
                                  '[%s] resource ' % resource)
            self.validate_methods(supported_item_methods,
                                  settings['item_methods'],
                                  '[%s] item ' % resource)

            if 'POST' in settings['methods'] or \
               'PATCH' in settings['item_methods']:
                if len(settings['schema']) == 0:
                    print settings['methods'], settings['item_methods']
                    raise ConfigException('A resource schema must be provided '
                                          'when POST or PATCH methods are '
                                          'allowed for a resource (%s).' %
                                          resource)

    def validate_methods(self, allowed, proposed, word):
        diff = set(proposed) - set(allowed)
        if diff:
            raise ConfigException('Unallowed %s method(s): %s. '
                                  'Supported: %s' %
                                  (word, ', '.join(diff),
                                   ', '.join(allowed)))

    def validate_schemas(self):
        # TODO are there other mandatory settings items? Validate them here
        pass

    def set_defaults(self):
        # TODO fill schema{} defaults, like data type, etc.
        for resource, settings in self.config['DOMAIN'].items():
            settings.setdefault('url', resource)
            settings.setdefault('methods',
                                self.config['RESOURCE_METHODS'])
            settings.setdefault('cache_control',
                                self.config['CACHE_CONTROL'])
            settings.setdefault('cache_expires',
                                self.config['CACHE_EXPIRES'])
            settings.setdefault('item_lookup_field',
                                self.config['ITEM_LOOKUP_FIELD'])
            settings.setdefault('item_url',
                                self.config['ITEM_URL'])
            settings.setdefault('item_cache_control',
                                self.config['ITEM_CACHE_CONTROL'])
            settings.setdefault('item_lookup',
                                self.config['ITEM_LOOKUP'])

            if settings['item_lookup']:
                item_methods = self.config['ITEM_METHODS']
            else:
                item_methods = eve.ITEM_METHODS
            settings.setdefault('item_methods', item_methods)

            schema = settings.setdefault('schema', {})
            settings['dates'] = \
                set(field for field, definition in schema.items()
                    if definition.get('type') == 'datetime')

    def add_url_rules(self):
        # helpers
        resources = dict()     # maps urls to resources (DOMAIN keys)
        urls = dict()          # maps resources to urls

        url_prefix = self.config['URL_PREFIX']
        self.add_url_rule('%s/' % url_prefix, 'home', home_endpoint)

        for resource, settings in self.config['DOMAIN'].items():
            resources[settings['url']] = resource
            urls[resource] = settings['url']

            url = '/<regex("%s"):url>/' % settings['url']
            url = '%s%s' % (url_prefix.rstrip('/'), url)
            self.add_url_rule(url, view_func=collections_endpoint,
                              methods=settings['methods'])

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

            add_lookup = settings.get('additional_lookup')
            if add_lookup:
                item_url = '%s<regex("%s"):%s>/' % (url,
                                                    add_lookup['url'],
                                                    add_lookup['field'])
                self.add_url_rule(item_url, view_func=item_endpoint,
                                  methods=['GET'])
        self.config['RESOURCES'] = resources
        self.config['URLS'] = urls
