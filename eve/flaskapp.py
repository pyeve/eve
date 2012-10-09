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

        validator_cls = None
        if 'validator' in kwargs:
            validator_cls = kwargs['validator']
            kwargs.pop('validator')

        datalayer_cls = None
        if 'data' in kwargs:
            datalayer_cls = kwargs['data']
            kwargs.pop('data')

        super(Eve, self).__init__(__package__, **kwargs)

        self.url_map.converters['regex'] = RegexConverter

        self.load_config()
        self.validate_config()
        self.set_defaults()
        self.add_url_rules()

        self.validator = validator_cls if validator_cls else Validator
        self.data = datalayer_cls(self) if datalayer_cls else Mongo(self)

    def load_config(self):
        self.config.from_object(eve)

        try:
            self.config.from_pyfile('settings.py')
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

        # TODO are there other mandatory settings items? Validate them.
        # TODO DOMAIN methods must match the supported schema (res/item)
        # TODO resources allowing POST and PATCH methods must have a schema{}
        # definition

    def set_defaults(self):
        # TODO fill schema{} defaults, such as DATE_CREATED, DATE_UPDATED,
        # data_type, etc.
        for resource, settings in self.config['DOMAIN'].items():
            settings.setdefault('url', resource)
            settings.setdefault('methods',
                                self.config['RESOURCE_METHODS'])
            settings.setdefault('cache_control',
                                self.config['CACHE_CONTROL'])
            settings.setdefault('cache_expires',
                                self.config['CACHE_EXPIRES'])
            settings.setdefault('item_methods',
                                self.config['ITEM_METHODS'])
            settings.setdefault('item_lookup',
                                self.config['ITEM_LOOKUP'])
            settings.setdefault('item_lookup_field',
                                self.config['ITEM_LOOKUP_FIELD'])
            settings.setdefault('item_url',
                                self.config['ITEM_URL'])
            settings.setdefault('item_cache_control',
                                self.config['ITEM_CACHE_CONTROL'])

            schema = settings.get('schema')
            if schema:
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
