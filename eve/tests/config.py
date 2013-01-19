# -*- coding: utf-8 -*-

import eve
import os
from eve.flaskapp import RegexConverter
from eve.flaskapp import Eve
from eve.io.base import DataLayer
from eve.tests import TestBase
from eve.exceptions import ConfigException
from eve.io.mongo import Mongo, Validator


class TestConfig(TestBase):

    def test_regexconverter(self):
        regex_converter = self.app.url_map.converters.get('regex')
        self.assertEqual(regex_converter, RegexConverter)

    def test_default_validator(self):
        self.assertEqual(self.app.validator, Validator)

    def test_default_datalayer(self):
        self.assertEqual(type(self.app.data), Mongo)

    def test_default_settings(self):
        self.assertEqual(self.app.settings, self.settings_file)

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
        self.assertValidateConfig('missing')

        self.app.config['DOMAIN'] = []
        self.assertValidateConfig('must be a dict')

        self.app.config['DOMAIN'] = {}
        self.assertValidateConfig('must contain at least one')

    def test_validate_resource_methods(self):
        self.app.config['RESOURCE_METHODS'] = ['PUT', 'GET', 'DELETE', 'POST']
        self.assertValidateConfig('PUT')

    def test_validate_item_methods(self):
        self.app.config['ITEM_METHODS'] = ['PUT', 'GET', 'POST', 'DELETE']
        self.assertValidateConfig('PUT, POST')

    def test_validate_schema_methods(self):
        test = {
            'methods': ['PUT', 'GET', 'DELETE', 'POST'],
        }
        self.app.config['DOMAIN']['test_resource'] = test
        self.assertValidateConfig('PUT')

    def test_validate_schema_item_methods(self):
        test = {
            'methods': ['GET'],
            'item_methods': ['PUT'],
        }
        self.app.config['DOMAIN']['test_resource'] = test
        self.assertValidateConfig('PUT')

    def test_validate_datecreated_in_schema(self):
        self.assertUnallowedField(eve.DATE_CREATED)

    def test_validate_lastupdated_in_schema(self):
        self.assertUnallowedField(eve.LAST_UPDATED)

    def test_validate_idfield_in_schema(self):
        self.assertUnallowedField(eve.ID_FIELD)

    def assertUnallowedField(self, field):
        self.domain.clear()
        self.domain['resource'] = {
            'schema': {
                field: {'type': 'datetime'}
            }
        }
        self.app.set_defaults()
        self.assertValidateConfig('automatically')

    def assertValidateConfig(self, expected):
        try:
            self.app.validate_domain_struct()
            self.app.validate_config()
        except ConfigException, e:
            self.assertTrue(expected.lower() in str(e).lower())
        else:
            self.fail("ConfigException expected but not raised.")

    def test_set_defaults(self):
        self.domain.clear()
        resource = 'plurals'
        self.domain[resource] = {}

        self.app.set_defaults()

        settings = self.domain[resource]
        self.assertEqual(settings['url'], resource)
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
        self.assertEqual(settings['item_title'],
                         resource.rstrip('s').capitalize())
        self.assertEqual(settings['item_cache_control'],
                         self.app.config['ITEM_CACHE_CONTROL'])
        self.assertNotEqual(settings['schema'], None)
        self.assertEqual(type(settings['schema']), dict)
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
        self.assertNotEqual(settings.get('dates'), None)
        self.assertEqual(type(settings['dates']), set)
        self.assertEqual(len(settings['dates']), 2)

    def test_url_helpers(self):
        self.assertNotEqual(self.app.config.get('RESOURCES'), None)
        self.assertEqual(type(self.app.config['RESOURCES']), dict)

        self.assertNotEqual(self.app.config.get('URLS'), None)
        self.assertEqual(type(self.app.config['URLS']), dict)

        for resource, settings in self.domain.items():
            self.assertEqual(settings['url'],
                             self.app.config['URLS'][resource])
            self.assertEqual(resource,
                             self.app.config['RESOURCES'][settings['url']])

    def test_url_rules(self):
        map_adapter = self.app.url_map.bind(self.app.config['SERVER_NAME'])

        for resource, settings in self.domain.items():
            for method in settings['methods']:
                self.assertTrue(map_adapter.test('/%s/' % settings['url'],
                                                 method))

            # TODO test item endpoints as well. gonna be tricky since
            # we have to reverse regexes here. will be fun.
