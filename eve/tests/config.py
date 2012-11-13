from eve.flaskapp import RegexConverter
from eve.flaskapp import Eve
from eve.io.base import DataLayer
from eve.tests import TestBase
from eve.exceptions import ConfigException
from eve.io.mongo import Mongo, Validator


class TestConfig(TestBase):

    def test_regexconverter(self):
        regex_converter = self.app.url_map.converters.get('regex')
        self.assertIs(regex_converter, RegexConverter)

    def test_default_validator(self):
        self.assertIs(self.app.validator, Validator)

    def test_default_datalayer(self):
        self.assertIs(type(self.app.data), Mongo)

    def test_default_settings(self):
        self.assertEqual(self.app.settings, 'tests/testsettings.py')

    def test_custom_validator(self):
        class MyTestValidator(Validator):
            pass
        self.app = Eve(validator=MyTestValidator,
                       settings='tests/testsettings.py')
        self.assertIs(self.app.validator, MyTestValidator)

    def test_custom_datalayer(self):
        class MyTestDataLayer(DataLayer):
            def init_app(self, app):
                pass
            pass
        self.app = Eve(data=MyTestDataLayer, settings='tests/testsettings.py')
        self.assertIs(type(self.app.data), MyTestDataLayer)

    def test_validate_config(self):
        del self.app.config['DOMAIN']
        self.assertValidateConfig('missing')

        self.app.config['DOMAIN'] = []
        self.assertValidateConfig('must be a dict')

        self.app.config['DOMAIN'] = {}
        self.assertValidateConfig('must contain at least one')

    def test_validate_resource_methods(self):
        self.app.config['RESOURCE_METHODS'] = ['PUT', 'GET', 'DELETE', 'POST']
        self.assertValidateConfig('PUT, DELETE')

    def test_validate_item_methods(self):
        self.app.config['ITEM_METHODS'] = ['PUT', 'GET', 'POST']
        self.assertValidateConfig('PUT, POST')

    def test_validate_schema_methods(self):
        test = {
            'methods': ['PUT', 'GET', 'DELETE', 'POST'],
        }
        self.app.config['DOMAIN']['test_resource'] = test
        self.assertValidateConfig('PUT, DELETE')

    def test_validate_schema_item_methods(self):
        test = {
            'methods': ['GET'],
            'item_methods': ['PUT'],
        }
        self.app.config['DOMAIN']['test_resource'] = test
        self.assertValidateConfig('PUT')

    def assertValidateConfig(self, expected):
        try:
            self.app.validate_config()
        except ConfigException, e:
            self.assertTrue(expected.lower() in str(e).lower())
        else:
            self.fail("ConfigException expected but not raised.")

    def test_set_defaults(self):
        self.domain.clear()
        self.domain['empty_resource'] = {}

        self.app.set_defaults()

        settings = self.domain['empty_resource']
        self.assertEqual(settings['url'], 'empty_resource')
        self.assertEqual(settings['methods'],
                         self.app.config['RESOURCE_METHODS'])
        self.assertEqual(settings['cache_control'],
                         self.app.config['CACHE_CONTROL'])
        self.assertEqual(settings['cache_expires'],
                         self.app.config['CACHE_EXPIRES'])
        self.assertEqual(settings['item_methods'],
                         self.app.config['ITEM_METHODS'])
        self.assertEqual(settings['item_lookup'],
                         self.app.config['ITEM_LOOKUP'])
        self.assertEqual(settings['item_lookup_field'],
                         self.app.config['ITEM_LOOKUP_FIELD'])
        self.assertEqual(settings['item_url'],
                         self.app.config['ITEM_URL'])
        self.assertEqual(settings['item_cache_control'],
                         self.app.config['ITEM_CACHE_CONTROL'])
        self.assertIsNotNone(settings['schema'])
        self.assertIs(type(settings['schema']), dict)
        self.assertEqual(len(settings['schema']), 0)

    def test_schema_dates(self):
        self.domain.clear()
        self.domain['resource'] = {
            'schema': {
                'born': {
                    'type': 'datetime',
                },
                'name': {
                    'type': 'string',
                },
                'another_date': {
                    'type': 'datetime',
                }
            }
        }
        self.app.set_defaults()
        settings = self.domain['resource']
        self.assertIsNotNone(settings.get('dates'))
        self.assertIs(type(settings['dates']), set)
        self.assertEqual(len(settings['dates']), 2)

    def test_url_helpers(self):
        self.assertIsNotNone(self.app.config.get('RESOURCES'))
        self.assertIs(type(self.app.config['RESOURCES']), dict)

        self.assertIsNotNone(self.app.config.get('URLS'))
        self.assertIs(type(self.app.config['URLS']), dict)

        for resource, settings in self.domain.items():
            self.assertEqual(settings['url'],
                             self.app.config['URLS'][resource])
            self.assertEqual(resource,
                             self.app.config['RESOURCES'][settings['url']])

    def test_url_rules(self):
        map_adapter = self.app.url_map.bind(self.app.config['BASE_URI'])

        for resource, settings in self.domain.items():
            for method in settings['methods']:
                self.assertTrue(map_adapter.test('/%s/' % settings['url'],
                                                 method))

            # TODO test item endpoints as well. gonna be tricky since
            # we have to reverse regexes here. will be fun.
