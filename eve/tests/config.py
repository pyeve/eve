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
    def test_allow_unknown_with_soft_delete(self):
        my_settings = {
            'ALLOW_UNKNOWN': True,
            'SOFT_DELETE': True,
            'DOMAIN': {'contacts': {}}
        }
        try:
            self.app = Eve(settings=my_settings)
        except TypeError:
            self.fail("ALLOW_UNKNOWN and SOFT_DELETE enabled should not cause "
                      "a crash.")

    def test_default_import_name(self):
        self.assertEqual(self.app.import_name, eve.__package__)

    def test_custom_import_name(self):
        self.app = Eve('unittest', settings=self.settings_file)
        self.assertEqual(self.app.import_name, 'unittest')

    def test_custom_kwargs(self):
        self.app = Eve('unittest', static_folder='/',
                       settings=self.settings_file)
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
        self.assertEqual(self.app.config['ISSUES'], '_issues')

        self.assertEqual(self.app.config['OPLOG'], False)
        self.assertEqual(self.app.config['OPLOG_NAME'], 'oplog')
        self.assertEqual(self.app.config['OPLOG_ENDPOINT'], None)
        self.assertEqual(self.app.config['OPLOG_AUDIT'], True)
        self.assertEqual(self.app.config['OPLOG_METHODS'], ['DELETE',
                                                            'POST',
                                                            'PATCH',
                                                            'PUT'])
        self.assertEqual(self.app.config['OPLOG_CHANGE_METHODS'], ['DELETE',
                                                                   'PATCH',
                                                                   'PUT'])
        self.assertEqual(self.app.config['QUERY_WHERE'], 'where')
        self.assertEqual(self.app.config['QUERY_PROJECTION'], 'projection')
        self.assertEqual(self.app.config['QUERY_SORT'], 'sort')
        self.assertEqual(self.app.config['QUERY_PAGE'], 'page')
        self.assertEqual(self.app.config['QUERY_MAX_RESULTS'], 'max_results')
        self.assertEqual(self.app.config['QUERY_EMBEDDED'], 'embedded')
        self.assertEqual(self.app.config['QUERY_AGGREGATION'], 'aggregate')

        self.assertEqual(self.app.config['JSON_SORT_KEYS'], False)
        self.assertEqual(self.app.config['SOFT_DELETE'], False)
        self.assertEqual(self.app.config['DELETED'], '_deleted')
        self.assertEqual(self.app.config['SHOW_DELETED_PARAM'], 'show_deleted')
        self.assertEqual(self.app.config['STANDARD_ERRORS'],
                         [400, 401, 404, 405, 406, 409, 410, 412, 422, 428])
        self.assertEqual(self.app.config['UPSERT_ON_PUT'], True)
        self.assertEqual(self.app.config['JSON_REQUEST_CONTENT_TYPES'],
                         ['application/json'])

    def test_settings_as_dict(self):
        my_settings = {'API_VERSION': 'override!', 'DOMAIN': {'contacts': {}}}
        self.app = Eve(settings=my_settings)
        self.assertEqual(self.app.config['API_VERSION'], 'override!')
        # did not reset other defaults
        self.assertEqual(self.app.config['MONGO_WRITE_CONCERN'], {'w': 1})

    def test_existing_env_config(self):
        env = os.environ
        os.environ = {'EVE_SETTINGS': 'test_settings_env.py'}
        self.app = Eve()
        self.assertTrue('env_domain' in self.app.config['DOMAIN'])
        os.environ = env

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
        self.app = Eve(data=MyTestDataLayer, settings=self.settings_file)
        self.assertEqual(type(self.app.data), MyTestDataLayer)

    def test_validate_domain_struct(self):
        del self.app.config['DOMAIN']
        self.assertValidateConfigFailure('missing')

        self.app.config['DOMAIN'] = []
        self.assertValidateConfigFailure('must be a dict')

        self.app.config['DOMAIN'] = {}
        self.assertValidateConfigSuccess()

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

    def assertUnallowedField(self, field, field_type='datetime'):
        self.domain.clear()
        schema = {field: {'type': field_type}}
        self.domain['resource'] = {'schema': schema}
        self.app.set_defaults()
        self.assertValidateSchemaFailure('resource', schema, field)

    def test_validate_schema(self):
        # lack of 'collection' key for 'data_collection' rule
        schema = self.domain['invoices']['schema']
        del(schema['person']['data_relation']['resource'])
        self.assertValidateSchemaFailure('invoices', schema, 'resource')

    def test_validate_invalid_field_names(self):
        schema = self.domain['invoices']['schema']
        schema['te$t'] = {'type': 'string'}
        self.assertValidateSchemaFailure('invoices', schema, 'te$t')
        del(schema['te$t'])

        schema['te.t'] = {'type': 'string'}
        self.assertValidateSchemaFailure('invoices', schema, 'te.t')
        del(schema['te.t'])

        schema['test_a_dict_schema'] = {
            'type': 'dict',
            'schema': {'te$t': {'type': 'string'}}
        }
        self.assertValidateSchemaFailure('invoices', schema, 'te$t')

        schema['test_a_dict_schema']['schema'] = {'te.t': {'type': 'string'}}
        self.assertValidateSchemaFailure('invoices', schema, 'te.t')

    def test_set_schema_defaults(self):
        # default data_relation field value
        schema = self.domain['invoices']['schema']
        data_relation = schema['person']['data_relation']
        self.assertTrue('field' in data_relation)
        self.assertEqual(data_relation['field'],
                         self.domain['contacts']['id_field'])
        id_field = self.domain['invoices']['id_field']
        self.assertTrue(id_field in schema)
        self.assertEqual(schema[id_field], {'type': 'objectid'})

    def test_set_defaults(self):
        self.domain.clear()
        resource = 'plurals'
        self.domain[resource] = {}
        self.app.set_defaults()
        self._test_defaults_for_resource(resource)
        settings = self.domain[resource]
        self.assertEqual(len(settings['schema']), 1)

    def _test_defaults_for_resource(self, resource):
        settings = self.domain[resource]
        self.assertEqual(settings['url'], resource)
        self.assertEqual(settings['internal_resource'],
                         self.app.config['INTERNAL_RESOURCE'])
        self.assertEqual(settings['resource_methods'],
                         self.app.config['RESOURCE_METHODS'])
        self.assertEqual(settings['public_methods'],
                         self.app.config['PUBLIC_METHODS'])
        self.assertEqual(settings['allowed_roles'],
                         self.app.config['ALLOWED_ROLES'])
        self.assertEqual(settings['allowed_read_roles'],
                         self.app.config['ALLOWED_READ_ROLES'])
        self.assertEqual(settings['allowed_write_roles'],
                         self.app.config['ALLOWED_WRITE_ROLES'])
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
        self.assertEqual(settings['allowed_item_read_roles'],
                         self.app.config['ALLOWED_ITEM_READ_ROLES'])
        self.assertEqual(settings['allowed_item_write_roles'],
                         self.app.config['ALLOWED_ITEM_WRITE_ROLES'])
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
        self.assertEqual(settings['versioning'], self.app.config['VERSIONING'])
        self.assertEqual(settings['soft_delete'],
                         self.app.config['SOFT_DELETE'])
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
        self.assertEqual(settings['resource_title'], settings['url'])

        self.assertNotEqual(settings['schema'], None)
        self.assertEqual(type(settings['schema']), dict)
        self.assertEqual(settings['etag_ignore_fields'], None)

    def test_datasource(self):
        self._test_datasource_for_resource('invoices')

    def _test_datasource_for_resource(self, resource):
        datasource = self.domain[resource]['datasource']
        schema = self.domain[resource]['schema']
        compare = [key for key in datasource['projection'] if key in schema]
        compare.extend([self.domain[resource]['id_field'],
                        self.app.config['LAST_UPDATED'],
                        self.app.config['DATE_CREATED'],
                        self.app.config['ETAG']])

        self.assertEqual(datasource['projection'],
                         dict((field, 1) for (field) in compare))
        self.assertEqual(datasource['source'], resource)
        self.assertEqual(datasource['filter'], None)

        self.assertEqual(datasource['aggregation'], None)

    def test_validate_roles(self):
        for resource in self.domain:
            self.assertValidateRoles(resource, 'allowed_roles')
            self.assertValidateRoles(resource, 'allowed_read_roles')
            self.assertValidateRoles(resource, 'allowed_write_roles')
            self.assertValidateRoles(resource, 'allowed_item_roles')
            self.assertValidateRoles(resource, 'allowed_item_read_roles')
            self.assertValidateRoles(resource, 'allowed_item_write_roles')

    def assertValidateRoles(self, resource, directive):
        prev = self.domain[resource][directive]
        self.domain[resource][directive] = 'admin'
        self.assertValidateConfigFailure(directive)
        self.domain[resource][directive] = []
        self.assertValidateConfigSuccess()
        self.domain[resource][directive] = ['admin', 'dev']
        self.assertValidateConfigSuccess()
        self.domain[resource][directive] = None
        self.assertValidateConfigFailure(directive)
        self.domain[resource][directive] = prev

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

    def test_url_helpers(self):
        self.assertNotEqual(self.app.config.get('URLS'), None)
        self.assertEqual(type(self.app.config['URLS']), dict)

        self.assertNotEqual(self.app.config.get('SOURCES'), None)
        self.assertEqual(type(self.app.config['SOURCES']), dict)

        del(self.domain['internal_transactions'])
        for resource, settings in self.domain.items():
            self.assertEqual(settings['datasource'],
                             self.app.config['SOURCES'][resource])

    def test_pretty_resource_urls(self):
        """ test that regexes are stripped out of urls and #466 is fixed. """
        resource_url = self.app.config['URLS']['peopleinvoices']
        pretty_url = 'users/<person>/invoices'
        self.assertEqual(resource_url, pretty_url)
        resource_url = self.app.config['URLS']['peoplesearches']
        pretty_url = 'users/<person>/saved_searches'
        self.assertEqual(resource_url, pretty_url)

    def test_url_rules(self):
        map_adapter = self.app.url_map.bind('')

        del(self.domain['peopleinvoices'])
        del(self.domain['peoplerequiredinvoices'])
        del(self.domain['peoplesearches'])
        del(self.domain['internal_transactions'])
        del(self.domain['child_products'])
        for _, settings in self.domain.items():
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

    def test_auth_field_as_idfield(self):
        resource = 'resource'
        settings = {
            'auth_field': self.app.config['ID_FIELD'],
        }
        self.assertRaises(ConfigException, self.app.register_resource,
                          resource, settings)

    def test_auth_field_as_custom_idfield(self):
        resource = 'resource'
        settings = {
            'schema': {
                'id': {'type': 'string'}
            },
            'id_field': 'id',
            'auth_field': 'id'
        }
        self.assertRaises(ConfigException, self.app.register_resource,
                          resource, settings)

    def test_oplog_config(self):

        # if OPLOG_ENDPOINT is eanbled the endoint is included with the domain
        self.app.config['OPLOG_ENDPOINT'] = 'oplog'
        self.app._init_oplog()
        self.assertOplog('oplog', 'oplog')
        del(self.domain['oplog'])

        # OPLOG can be also with a custom name (which will be used
        # as the collection/table name on the db)
        oplog = 'custom'
        self.app.config['OPLOG_NAME'] = oplog
        self.app._init_oplog()
        self.assertOplog(oplog, 'oplog')
        del(self.domain[oplog])

        # oplog can be defined as a regular API endpoint, with a couple caveats
        self.domain['oplog'] = {
            'resource_methods': ['POST', 'DELETE'],     # not allowed
            'resource_items': ['PATCH', 'PUT'],         # not allowed
            'url': 'custom_url',
            'datasource': {'source': 'customsource'}
        }
        self.app.config['OPLOG_NAME'] = 'oplog'
        settings = self.domain['oplog']
        self.app._init_oplog()

        # endpoint is always read-only
        self.assertEqual(settings['resource_methods'], ['GET'])
        self.assertEqual(settings['item_methods'], ['GET'])
        # other settings are customizable
        self.assertEqual(settings['url'], 'custom_url')
        self.assertEqual(settings['datasource']['source'], 'customsource')

    def assertOplog(self, key, endpoint):
        self.assertTrue(key in self.domain)

        settings = self.domain[key]
        self.assertEqual(settings['resource_methods'], ['GET'])
        self.assertEqual(settings['item_methods'], ['GET'])
        self.assertEqual(settings['url'], endpoint)
        self.assertEqual(settings['datasource']['source'], key)

    def test_create_indexes(self):
        # prepare a specific schema with mongo indexes declared
        # along with the schema.
        settings = {
            'schema': {
                'name': {'type': 'string'},
                'other_field': {'type': 'string'},
                'lat_long': {'type': 'list'}
            },
            'versioning': True,
            'mongo_indexes': {
                'name': [('name', 1)],
                'composed': [('name', 1), ('other_field', 1)],
                'arguments': ([('lat_long', "2d")], {"sparse": True})
            }
        }
        self.app.register_resource('mongodb_features', settings)

        # check that the indexes are there as a part of the resource
        # settings
        self.assertEqual(
            self.app.config['DOMAIN']['mongodb_features']['mongo_indexes'],
            settings['mongo_indexes']
        )

        # check that the indexes were created
        from pymongo import MongoClient
        db_name = self.app.config['MONGO_DBNAME']

        db = MongoClient()[db_name]
        for coll in [db['mongodb_features'], db['mongodb_features_versions']]:
            indexes = coll.index_information()

            # at least there is an index for the _id field plus the indexes
            # created by the resource of this test
            self.assertTrue(len(indexes) > len(settings['mongo_indexes']))

            # check each one, fields involved and arguments given
            for key, value in settings['mongo_indexes'].items():
                if isinstance(value, tuple):
                    fields, args = value
                else:
                    fields = value
                    args = None

                self.assertTrue(key in indexes)
                self.assertEqual(indexes[key]['key'], fields)

                for arg in args or ():
                    self.assertTrue(arg in indexes[key])
                    self.assertEqual(args[arg], indexes[key][arg])

    def test_custom_error_handlers(self):
        """ Test that the standard, custom error handler is registered for
        supported error codes.
        """
        codes = self.app.config['STANDARD_ERRORS']

        # http://flask.pocoo.org/docs/0.10/api/#flask.Flask.error_handler_spec
        handlers = self.app.error_handler_spec[None]

        challenge = lambda code: self.assertTrue(code in handlers)  # noqa
        map(challenge, codes)

    def test_mongodb_settings(self):
        # Create custom app with mongodb settings.
        settings = {
            'DOMAIN': {'contacts': {}},
            'MONGO_OPTIONS': {
                'connect': False
            }
        }
        app = Eve(settings=settings)
        # Check if settings are set.
        self.assertEqual(
            app.config['MONGO_OPTIONS']['connect'],
            app.config['MONGO_CONNECT']
        )
        # Prepare a specific schema with mongo specific settings.
        settings = {
            'schema': {
                'name': {'type': 'string'},
            },
            'MONGO_OPTIONS': {
                'connect': False
            }
        }
        self.app.register_resource('mongodb_settings', settings)
        # check that settings are set.
        resource_settings = self.app.config['DOMAIN']['mongodb_settings']
        self.assertEqual(
            resource_settings['MONGO_OPTIONS'],
            settings['MONGO_OPTIONS']
        )
        # check that settings are set.
        self.assertEqual(
            resource_settings['MONGO_OPTIONS']['connect'],
            settings['MONGO_OPTIONS']['connect']
        )
