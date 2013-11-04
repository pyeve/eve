# -*- coding: utf-8 -*-

import eve
import os
from eve.flaskapp import RegexConverter
from eve.flaskapp import Eve
from eve.io.base import DataLayer
from eve.tests import TestBase
from eve.exceptions import ConfigException, SchemaException
from eve.io.mongo import Mongo, Validator


class TestConfig(TestBase):
    def test_default_import_name(self):
        self.assertEqual(self.app.import_name, eve.__package__)

    def test_custom_import_name(self):
        self.app = Eve('custom_import_name',
                       settings='eve/tests/test_settings.py')
        self.assertEqual(self.app.import_name, 'custom_import_name')

    def test_custom_kwargs(self):
        self.app = Eve('custom_import_name', static_folder='/',
                       settings='eve/tests/test_settings.py')
        self.assertEqual(self.app.static_folder, '/')

    def test_regexconverter(self):
        regex_converter = self.app.url_map.converters.get('regex')
        self.assertEqual(regex_converter, RegexConverter)

    def test_default_validator(self):
        self.assertEqual(self.app.validator, Validator)

    def test_default_datalayer(self):
        self.assertEqual(type(self.app.data), Mongo)

    def test_default_settings(self):
        self.assertEqual(self.app.settings, self.settings_file)

        # TODO add tests for other global default values
        self.assertEqual(self.app.config['RATE_LIMIT_GET'], None)
        self.assertEqual(self.app.config['RATE_LIMIT_POST'], None)
        self.assertEqual(self.app.config['RATE_LIMIT_PATCH'], None)
        self.assertEqual(self.app.config['RATE_LIMIT_DELETE'], None)

        self.assertEqual(self.app.config['MONGO_HOST'], 'localhost')
        self.assertEqual(self.app.config['MONGO_PORT'], 27017)
        self.assertEqual(self.app.config['MONGO_QUERY_BLACKLIST'], ['$where',
                                                                    '$regex'])
        self.assertEqual(self.app.config['MONGO_WRITE_CONCERN'], {'w': 1})

    def test_unexisting_pyfile_config(self):
        self.assertRaises(IOError, Eve, settings='an_unexisting_pyfile.py')

    def test_unexisting_env_config(self):
        env = os.environ
        try:
            os.environ = {'EVE_SETTINGS': 'an_unexisting_pyfile.py'}
            self.assertRaises(IOError, Eve)
        finally:
            os.environ = env

    def test_custom_validator(self):
        class MyTestValidator(Validator):
            pass
        self.app = Eve(validator=MyTestValidator,
                       settings=self.settings_file)
        self.assertEqual(self.app.validator, MyTestValidator)

    def test_custom_datalayer(self):
        class MyTestDataLayer(DataLayer):
            def init_app(self, app):
                pass
            pass
        self.app = Eve(data=MyTestDataLayer, settings=self.settings_file)
        self.assertEqual(type(self.app.data), MyTestDataLayer)

    def test_validate_domain_struct(self):
        del self.app.config['DOMAIN']
        self.assertValidateConfigFailure('missing')

        self.app.config['DOMAIN'] = []
        self.assertValidateConfigFailure('must be a dict')

        self.app.config['DOMAIN'] = {}
        self.assertValidateConfigFailure('must contain at least one')

    def test_validate_resource_methods(self):
        self.app.config['RESOURCE_METHODS'] = ['PUT', 'GET', 'DELETE', 'POST']
        self.assertValidateConfigFailure('PUT')

    def test_validate_item_methods(self):
        self.app.config['ITEM_METHODS'] = ['PUT', 'GET', 'POST', 'DELETE']
        self.assertValidateConfigFailure(['POST', 'PUT'])

    def test_validate_schema_methods(self):
        test = {
            'resource_methods': ['PUT', 'GET', 'DELETE', 'POST'],
        }
        self.app.config['DOMAIN']['test_resource'] = test
        self.assertValidateConfigFailure('PUT')

    def test_validate_schema_item_methods(self):
        test = {
            'resource_methods': ['GET'],
            'item_methods': ['POST'],
        }
        self.app.config['DOMAIN']['test_resource'] = test
        self.assertValidateConfigFailure('PUT')

    def test_validate_datecreated_in_schema(self):
        self.assertUnallowedField(eve.DATE_CREATED)

    def test_validate_lastupdated_in_schema(self):
        self.assertUnallowedField(eve.LAST_UPDATED)

    def test_validate_idfield_in_schema(self):
        self.assertUnallowedField(eve.ID_FIELD)

    def assertUnallowedField(self, field):
        self.domain.clear()
        schema = {field: {'type': 'datetime'}}
        self.domain['resource'] = {'schema': schema}
        self.app.set_defaults()
        self.assertValidateSchemaFailure('resource', schema, field)

    def test_validate_schema(self):
        # lack of 'collection' key for 'data_collection' rule
        schema = self.domain['invoices']['schema']
        del(schema['person']['data_relation']['resource'])
        self.assertValidateSchemaFailure('invoices', schema, 'resource')

    def test_set_schema_defaults(self):
        # default data_relation field value
        schema = self.domain['invoices']['schema']
        data_relation = schema['person']['data_relation']
        self.assertTrue('field' in data_relation)
        self.assertEqual(data_relation['field'], self.app.config['ID_FIELD'])

    def test_set_defaults(self):
        self.domain.clear()
        resource = 'plurals'
        self.domain[resource] = {}
        self.app.set_defaults()
        self._test_defaults_for_resource(resource)
        settings = self.domain[resource]
        self.assertEqual(len(settings['schema']), 0)

    def _test_defaults_for_resource(self, resource):
        settings = self.domain[resource]
        self.assertEqual(settings['url'], resource)
        self.assertEqual(settings['resource_methods'],
                         self.app.config['RESOURCE_METHODS'])
        self.assertEqual(settings['public_methods'],
                         self.app.config['PUBLIC_METHODS'])
        self.assertEqual(settings['allowed_roles'],
                         self.app.config['ALLOWED_ROLES'])
        self.assertEqual(settings['cache_control'],
                         self.app.config['CACHE_CONTROL'])
        self.assertEqual(settings['cache_expires'],
                         self.app.config['CACHE_EXPIRES'])
        self.assertEqual(settings['item_methods'],
                         self.app.config['ITEM_METHODS'])
        self.assertEqual(settings['public_item_methods'],
                         self.app.config['PUBLIC_ITEM_METHODS'])
        self.assertEqual(settings['allowed_item_roles'],
                         self.app.config['ALLOWED_ITEM_ROLES'])
        self.assertEqual(settings['item_lookup'],
                         self.app.config['ITEM_LOOKUP'])
        self.assertEqual(settings['item_lookup_field'],
                         self.app.config['ITEM_LOOKUP_FIELD'])
        self.assertEqual(settings['item_url'],
                         self.app.config['ITEM_URL'])
        self.assertEqual(settings['item_title'],
                         resource.rstrip('s').capitalize())
        self.assertEqual(settings['allowed_filters'],
                         self.app.config['ALLOWED_FILTERS'])
        self.assertEqual(settings['projection'], self.app.config['PROJECTION'])
        self.assertEqual(settings['sorting'], self.app.config['SORTING'])
        self.assertEqual(settings['embedding'], self.app.config['EMBEDDING'])
        self.assertEqual(settings['pagination'], self.app.config['PAGINATION'])
        self.assertEqual(settings['auth_field'],
                         self.app.config['AUTH_FIELD'])
        self.assertEqual(settings['allow_unknown'],
                         self.app.config['ALLOW_UNKNOWN'])
        self.assertEqual(settings['extra_response_fields'],
                         self.app.config['EXTRA_RESPONSE_FIELDS'])
        self.assertEqual(settings['mongo_write_concern'],
                         self.app.config['MONGO_WRITE_CONCERN'])

        self.assertNotEqual(settings['schema'], None)
        self.assertEqual(type(settings['schema']), dict)

    def test_datasource(self):
        self._test_datasource_for_resource('invoices')

    def _test_datasource_for_resource(self, resource):
        datasource = self.domain[resource]['datasource']
        schema = self.domain[resource]['schema']
        compare = [key for key in datasource['projection'] if key in schema]
        compare.extend([self.app.config['ID_FIELD'],
                        self.app.config['LAST_UPDATED'],
                        self.app.config['DATE_CREATED']])

        self.assertEqual(datasource['projection'],
                         dict((field, 1) for (field) in compare))
        self.assertEqual(datasource['source'], resource)
        self.assertEqual(datasource['filter'], None)

    def test_validate_roles(self):
        for resource in self.domain:
            self.assertValidateRoles(resource, 'allowed_roles')
            self.assertValidateRoles(resource, 'allowed_item_roles')

    def assertValidateRoles(self, resource, directive):
        self.domain[resource][directive] = 'admin'
        self.assertValidateConfigFailure(directive)
        self.domain[resource][directive] = []
        self.assertValidateConfigFailure(directive)
        self.domain[resource][directive] = ['admin', 'dev']
        self.assertValidateConfigSuccess()
        self.domain[resource][directive] = None
        self.assertValidateConfigSuccess()

    def assertValidateConfigSuccess(self):
        try:
            self.app.validate_domain_struct()
            self.app.validate_config()
        except ConfigException as e:
            self.fail('ConfigException not expected: %s' % e)

    def assertValidateConfigFailure(self, expected):
        try:
            self.app.validate_domain_struct()
            self.app.validate_config()
        except ConfigException as e:
            if isinstance(expected, str):
                expected = [expected]
            for exp in expected:
                self.assertTrue(exp.lower() in str(e).lower())
        else:
            self.fail("ConfigException expected but not raised.")

    def assertValidateSchemaFailure(self, resource, schema, expected):
        try:
            self.app.validate_schema(resource, schema)
        except SchemaException as e:
            self.assertTrue(expected.lower() in str(e).lower())
        else:
            self.fail("SchemaException expected but not raised.")

    def test_schema_defaults(self):
        self.domain.clear()
        self.domain['resource'] = {
            'schema': {
                'title': {
                    'type': 'string',
                    'default': 'Mr.',
                },
                'price': {
                    'type': 'integer',
                    'default': 100
                },
            }
        }
        self.app.set_defaults()
        settings = self.domain['resource']
        self.assertNotEqual(settings.get('defaults'), None)
        self.assertEqual(type(settings['defaults']), set)
        self.assertEqual(len(settings['defaults']), 2)

    def test_url_helpers(self):
        self.assertNotEqual(self.app.config.get('RESOURCES'), None)
        self.assertEqual(type(self.app.config['RESOURCES']), dict)

        self.assertNotEqual(self.app.config.get('URLS'), None)
        self.assertEqual(type(self.app.config['URLS']), dict)

        self.assertNotEqual(self.app.config.get('SOURCES'), None)
        self.assertEqual(type(self.app.config['SOURCES']), dict)

        for resource, settings in self.domain.items():
            self.assertEqual(settings['url'],
                             self.app.config['URLS'][resource])
            self.assertEqual(resource,
                             self.app.config['RESOURCES']['/' +
                                                          settings['url']])

            self.assertEqual(settings['datasource'],
                             self.app.config['SOURCES'][resource])

    def test_url_rules(self):
        map_adapter = self.app.url_map.bind(self.app.config.get(
            'SERVER_NAME', ''))

        for resource, settings in self.domain.items():
            for method in settings['resource_methods']:
                self.assertTrue(map_adapter.test('/%s/' % settings['url'],
                                                 method))

            # TODO test item endpoints as well. gonna be tricky since
            # we have to reverse regexes here. will be fun.

    def test_register_resource(self):
        resource = 'resource'
        settings = {
            'schema': {
                'title': {
                    'type': 'string',
                    'default': 'Mr.',
                },
                'price': {
                    'type': 'integer',
                    'default': 100
                },
            }
        }
        self.app.register_resource(resource, settings)
        self._test_defaults_for_resource(resource)
        self._test_datasource_for_resource(resource)
        self.test_validate_roles()
