import time
from datetime import datetime

import simplejson as json
from bson import ObjectId, decimal128
from bson.dbref import DBRef

from eve.methods.common import serialize, normalize_dotted_fields
from eve.tests import TestBase
from eve.tests.auth import ValidBasicAuth, ValidTokenAuth, ValidHMACAuth
from eve.tests.test_settings import MONGO_DBNAME
from eve.utils import config

from collections import OrderedDict  # noqa


class TestSerializer(TestBase):
    def test_serialize_subdocument(self):
        # tests fix for #244, serialization of sub-documents.
        schema = {'personal': {'type': 'dict',
                               'schema': {'best_friend': {'type': 'objectid'},
                                          'born': {'type': 'datetime'}}},
                  'without_type': {}}
        doc = {'personal': {'best_friend': '50656e4538345b39dd0414f0',
                            'born': 'Tue, 06 Nov 2012 10:33:31 GMT'},
               'without_type': 'foo'}
        with self.app.app_context():
            serialized = serialize(doc, schema=schema)
        self.assertTrue(
            isinstance(serialized['personal']['best_friend'], ObjectId))
        self.assertTrue(
            isinstance(serialized['personal']['born'], datetime))

    def test_mongo_serializes(self):
        schema = {
            'id': {'type': 'objectid'},
            'date': {'type': 'datetime'},
            'count': {'type': 'integer'},
            'average': {'type': 'float'},
            'dict_valueschema': {
                'valueschema': {'type': 'objectid'}
            },
            'refobj': {'type': 'dbref'},
            'decobjstring': {'type': 'decimal'},
            'decobjnumber': {'type': 'decimal'}
        }
        with self.app.app_context():
            # Success
            res = serialize(
                {
                    'id': '50656e4538345b39dd0414f0',
                    'date': 'Tue, 06 Nov 2012 10:33:31 GMT',
                    'count': 42,
                    'average': 42.42,
                    'dict_valueschema': {
                        'foo1': '50656e4538345b39dd0414f0',
                        'foo2': '50656e4538345b39dd0414f0',
                    },
                    'refobj': {
                        '$id': '50656e4538345b39dd0414f0',
                        '$col': 'SomeCollection'
                    },
                    'decobjstring': "200.0",
                    'decobjnumber': 200.0
                },
                schema=schema
            )
            self.assertTrue(isinstance(res['id'], ObjectId))
            self.assertTrue(isinstance(res['date'], datetime))
            self.assertTrue(isinstance(res['count'], int))
            self.assertTrue(isinstance(res['average'], float))

            ks = res['dict_valueschema']
            self.assertTrue(isinstance(ks['foo1'], ObjectId))
            self.assertTrue(isinstance(ks['foo2'], ObjectId))
            self.assertTrue(isinstance(res['refobj'], DBRef))
            self.assertTrue(isinstance(res['decobjstring'],
                                       decimal128.Decimal128))
            self.assertTrue(isinstance(res['decobjnumber'],
                                       decimal128.Decimal128))

    def test_non_blocking_on_simple_field_serialization_exception(self):
        schema = {
            'extract_time': {'type': 'datetime'},
            'date': {'type': 'datetime'},
            'total': {'type': 'integer'}
        }

        with self.app.app_context():
            # Success
            res = serialize(
                {
                    'extract_time': 'Tue, 06 Nov 2012 10:33:31 GMT',
                    'date': 'Tue, 06 Nov 2012 10:33:31 GMT',
                    'total': 'r123'
                },
                schema=schema
            )
            # this has been left untouched as it could not be serialized.
            self.assertEqual(res['total'], 'r123')
            # these have been both serialized.
            self.assertTrue(isinstance(res['extract_time'], datetime))
            self.assertTrue(isinstance(res['date'], datetime))

    def test_serialize_lists_of_lists(self):
        # serialize should handle list of lists of basic types
        schema = {
            'l_of_l': {
                'type': 'list',
                'schema': {
                    'type': 'list',
                    'schema': {
                        'type': 'objectid'
                    }
                }
            }
        }
        doc = {
            'l_of_l': [
                ['50656e4538345b39dd0414f0', '50656e4538345b39dd0414f0'],
                ['50656e4538345b39dd0414f0', '50656e4538345b39dd0414f0']
            ]
        }

        with self.app.app_context():
            serialized = serialize(doc, schema=schema)
        for sublist in serialized['l_of_l']:
            for item in sublist:
                self.assertTrue(isinstance(item, ObjectId))

        # serialize should handle list of lists of dicts
        schema = {
            'l_of_l': {
                'type': 'list',
                'schema': {
                    'type': 'list',
                    'schema': {
                        'type': 'dict',
                        'schema': {
                            '_id': {
                                'type': 'objectid'
                            }
                        }
                    }
                }
            }
        }
        doc = {
            'l_of_l': [
                [
                    {'_id': '50656e4538345b39dd0414f0'},
                    {'_id': '50656e4538345b39dd0414f0'}
                ],
                [
                    {'_id': '50656e4538345b39dd0414f0'},
                    {'_id': '50656e4538345b39dd0414f0'}
                ],
            ]
        }
        with self.app.app_context():
            serialized = serialize(doc, schema=schema)
        for sublist in serialized['l_of_l']:
            for item in sublist:
                self.assertTrue(isinstance(item['_id'], ObjectId))

    def test_dbref_serialize_lists_of_lists(self):
        # serialize should handle list of lists of basic types
        schema = {
            'l_of_l': {
                'type': 'list',
                'schema': {
                    'type': 'list',
                    'schema': {
                        'type': 'dbref'
                    }
                }
            }
        }
        doc = {
            'l_of_l': [
                [{'$col': 'SomeCollection', '$id': '50656e4538345b39dd0414f0'},
                 {'$col': 'SomeCollection', '$id': '50656e4538345b39dd0414f0'}
                 ],
                [{'$col': 'SomeCollection', '$id': '50656e4538345b39dd0414f0'},
                 {'$col': 'SomeCollection', '$id': '50656e4538345b39dd0414f0'}
                 ]
            ]
        }

        with self.app.app_context():
            serialized = serialize(doc, schema=schema)
        for sublist in serialized['l_of_l']:
            for item in sublist:
                self.assertTrue(isinstance(item, DBRef))

        # serialize should handle list of lists of dicts
        schema = {
            'l_of_l': {
                'type': 'list',
                'schema': {
                    'type': 'list',
                    'schema': {
                        'type': 'dict',
                        'schema': {
                            '_id': {
                                'type': 'dbref'
                            }
                        }
                    }
                }
            }
        }
        doc = {
            'l_of_l': [
                [
                    {'_id': {'$col': 'SomeCollection',
                             '$id': '50656e4538345b39dd0414f0'}
                     },
                    {'_id': {'$col': 'SomeCollection',
                             '$id': '50656e4538345b39dd0414f0'}
                     }
                ],
                [
                    {'_id': {'$col': 'SomeCollection',
                             '$id': '50656e4538345b39dd0414f0'}
                     },
                    {'_id': {'$col': 'SomeCollection',
                             '$id': '50656e4538345b39dd0414f0'}
                     }
                ],
            ]
        }
        with self.app.app_context():
            serialized = serialize(doc, schema=schema)
        for sublist in serialized['l_of_l']:
            for item in sublist:
                self.assertTrue(isinstance(item['_id'], DBRef))

    def test_serialize_null_dictionary(self):
        # Serialization should continue after encountering a null value dict
        # field. Field may be nullable, or error will be caught in validation.
        schema = {
            'nullable_dict': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'simple_field': {
                        'type': 'number'
                    }
                }
            }
        }
        doc = {
            'nullable_dict': None
        }
        with self.app.app_context():
            try:
                serialize(doc, schema=schema)
            except Exception:
                self.assertTrue(False, "Serializing null dictionaries should "
                                       "not raise an exception.")

    def test_serialize_null_list(self):
        schema = {
            'nullable_list': {
                'type': 'list',
                'nullable': True,
                'schema': {
                    'type': 'objectid'
                }
            }
        }
        doc = {
            'nullable_list': None
        }
        with self.app.app_context():
            try:
                serialize(doc, schema=schema)
            except Exception:
                self.fail('Serializing null lists'
                          ' should not raise an exception')

        schema = {
            'nullable_list': {
                'type': 'list',
                'nullable': True,
                'schema': {
                    'type': 'dbref'
                }
            }
        }
        doc = {
            'nullable_list': None
        }
        with self.app.app_context():
            try:
                serialize(doc, schema=schema)
            except Exception:
                self.fail('Serializing null lists'
                          ' should not raise an exception')

    def test_serialize_number(self):
        schema = {
            'anumber': {
                'type': 'number',
            }
        }
        for expected_type, value in [(int, '35'), (float, '3.5')]:
            doc = {
                'anumber': value
            }
            with self.app.app_context():
                serialized = serialize(doc, schema=schema)
                self.assertTrue(
                    isinstance(serialized['anumber'], expected_type)
                )

    def test_serialize_boolean(self):
        schema = {'bool': {'type': 'boolean'}}

        with self.app.app_context():
            for val in [1, '1', 0, '0', 'true', 'True', 'false', 'False']:
                doc = {'bool': val}
                serialized = serialize(doc, schema=schema)
                self.assertTrue(isinstance(serialized['bool'], bool))

    def test_serialize_inside_x_of_rules(self):
        for x_of in ['allof', 'anyof', 'oneof', 'noneof']:
            schema = {
                'x_of-field': {
                    x_of: [
                        {'type': 'objectid'},
                        {'required': True}
                    ]
                }
            }
            doc = {'x_of-field': '50656e4538345b39dd0414f0'}
            with self.app.app_context():
                serialized = serialize(doc, schema=schema)
                self.assertTrue(isinstance(serialized['x_of-field'], ObjectId))

    def test_serialize_alongside_x_of_rules(self):
        for x_of in ['allof', 'anyof', 'oneof', 'noneof']:
            schema = OrderedDict([
                ('x_of-field', {
                    x_of: [
                        {'type': 'objectid'},
                        {'required': True}
                    ]
                }),
                ('oid-field', {'type': 'objectid'})
            ])
            doc = OrderedDict([('x_of-field', '50656e4538345b39dd0414f0'),
                               ('oid-field', '50656e4538345b39dd0414f0')])
            with self.app.app_context():
                serialized = serialize(doc, schema=schema)
                self.assertTrue(isinstance(serialized['x_of-field'], ObjectId))
                self.assertTrue(isinstance(serialized['oid-field'], ObjectId))

    def test_serialize_list_alongside_x_of_rules(self):
        for x_of in ['allof', 'anyof', 'oneof', 'noneof']:
            schema = {
                'x_of-field': {
                    "type": "list",
                    x_of: [
                        {"schema": {'type': 'objectid'}},
                        {"schema": {'type': 'datetime'}}
                    ]
                }
            }
            doc = {'x_of-field': ['50656e4538345b39dd0414f0']}
            with self.app.app_context():
                serialized = serialize(doc, schema=schema)
                self.assertTrue(isinstance(serialized['x_of-field'][0],
                                           ObjectId))

    def test_serialize_inside_nested_x_of_rules(self):
        schema = {
            'nested-x_of-field': {
                'oneof': [
                    {
                        'anyof': [
                            {'type': 'objectid'},
                            {'type': 'datetime'}
                        ],
                        'required': True
                    },
                    {
                        'allof': [
                            {'type': 'boolean'},
                            {'required': True}
                        ]
                    }
                ]
            }
        }
        doc = {'nested-x_of-field': '50656e4538345b39dd0414f0'}
        with self.app.app_context():
            serialized = serialize(doc, schema=schema)
            self.assertTrue(
                isinstance(serialized['nested-x_of-field'], ObjectId))

    def test_serialize_inside_x_of_typesavers(self):
        for x_of in ['allof', 'anyof', 'oneof', 'noneof']:
            schema = {
                'x_of-field': {
                    '{0}_type'.format(x_of): ['objectid', 'float', 'boolean']
                }
            }
            doc = {'x_of-field': '50656e4538345b39dd0414f0'}
            with self.app.app_context():
                serialized = serialize(doc, schema=schema)
                self.assertTrue(isinstance(serialized['x_of-field'], ObjectId))

    def test_serialize_inside_list_of_x_of_rules(self):
        for x_of in ['allof', 'anyof', 'oneof', 'noneof']:
            schema = {
                'list-field': {
                    'type': 'list',
                    'schema': {
                        x_of: [
                            {
                                'type': 'objectid',
                                'required': True}
                        ]
                    }
                }
            }
            doc = {'list-field': ['50656e4538345b39dd0414f0']}
            with self.app.app_context():
                serialized = serialize(doc, schema=schema)
                serialized_oid = serialized['list-field'][0]
                self.assertTrue(isinstance(serialized_oid, ObjectId))

    def test_serialize_inside_list_of_schema_of_x_of_rules(self):
        for x_of in ['allof', 'anyof', 'oneof', 'noneof']:
            schema = {
                'list-field': {
                    'type': 'list',
                    'schema': {
                        x_of: [
                            {
                                'type': 'dict',
                                'schema': {
                                    'x_of-field': {
                                        'type': 'objectid',
                                        'required': True
                                    }
                                }
                            }
                        ]
                    }
                }
            }
            doc = {'list-field': [{'x_of-field': '50656e4538345b39dd0414f0'}]}
            with self.app.app_context():
                serialized = serialize(doc, schema=schema)
                serialized_oid = serialized['list-field'][0]['x_of-field']
                self.assertTrue(isinstance(serialized_oid, ObjectId))

    def test_serialize_inside_list_of_x_of_typesavers(self):
        for x_of in ['allof', 'anyof', 'oneof', 'noneof']:
            schema = {
                'list-field': {
                    'type': 'list',
                    'schema': {
                        '{0}_type'.format(x_of): [
                            'objectid', 'float', 'boolean'
                        ]
                    }
                }
            }
            doc = {'list-field': ['50656e4538345b39dd0414f0']}
            with self.app.app_context():
                serialized = serialize(doc, schema=schema)
                serialized_oid = serialized['list-field'][0]
                self.assertTrue(isinstance(serialized_oid, ObjectId))


class TestNormalizeDottedFields(TestBase):
    def test_normalize_dotted_fields(self):
        def compare_recursive(a, b):
            for key, value in a.items():
                if key not in b:
                    return False
                if isinstance(value, dict):
                    compare_recursive(value, b[key])
            return True

        document = {
            'a.b': 1,
            'c.d': {
                'e.f': {
                    'g': 1,
                    'h': 2,
                },
                'e.f.i': {'j.k': 3,
                          },
            },
            'l': [
                {
                    'm.n': 4,
                },
            ],
        }
        expected_result = {
            'a': {
                'b': 1,
            },
            'c': {
                'd': {
                    'e': {
                        'f': {
                            'g': 1,
                            'h': 2,
                            'i': {
                                'j': {
                                    'k': 3,
                                },
                            },
                        },
                    },
                },
            },
            'l': [
                {
                    'm': {
                        'n': 4,
                    },
                },
            ],
        }
        normalize_dotted_fields(document)
        self.assertTrue(compare_recursive(document, expected_result))


class TestOpLogBase(TestBase):
    def setUp(self):
        super(TestOpLogBase, self).setUp()
        self.test_field, self.test_value = 'ref', "1234567890123456789054321"
        self.data = {self.test_field: self.test_value}
        self.test_client = self.app.test_client()
        self.headers = [(('Content-Type', 'application/json'))]

    def oplog_reset(self):
        self.app._init_oplog()
        self.app.register_resource('oplog', self.domain['oplog'])

        settings = self.app.config['DOMAIN']['oplog']
        datasource = settings['datasource']
        schema = settings['schema']
        datasource['projection'] = {}
        self.app._set_resource_projection(datasource, schema, settings)

    def oplog_get(self, url='/oplog'):
        r = self.test_client.get(url)
        return self.parse_response(r)

    def assertOpLogEntry(self, entry, op, user=None):
        self.assertTrue('r' in entry)
        self.assertTrue('i' in entry)
        self.assertTrue(config.LAST_UPDATED in entry)
        self.assertTrue(config.DATE_CREATED in entry)
        self.assertTrue('o' in entry)
        self.assertEqual(entry['o'], op)
        self.assertTrue('127.0.0.1' in entry['ip'])
        if op in self.app.config['OPLOG_CHANGE_METHODS']:
            self.assertTrue('c' in entry)
        self.assertTrue('u' in entry)
        if user:
            self.assertTrue(user in entry['u'])
        else:
            self.assertTrue('n/a' in entry['u'])


class TestOpLogEndpointDisabled(TestOpLogBase):
    def setUp(self):
        super(TestOpLogEndpointDisabled, self).setUp()

        self.app.config['OPLOG'] = True
        from eve.default_settings import OPLOG_CHANGE_METHODS
        self.app.config['OPLOG_CHANGE_METHODS'] = OPLOG_CHANGE_METHODS
        self.oplog_reset()

    def test_post_oplog(self):
        r = self.test_client.post(self.known_resource_url,
                                  data=json.dumps(self.data),
                                  headers=self.headers,
                                  environ_base={'REMOTE_ADDR': '127.0.0.1'})

        # oplog endpoint is not available.
        r, status = self.oplog_get()
        self.assert404(status)

        # however the oplog collection has been updated.
        db = self.connection[MONGO_DBNAME]
        cursor = db.oplog.find()
        self.assertEqual(cursor.count(), 1)
        self.assertOpLogEntry(cursor[0], 'POST')


class TestOpLogEndpointEnabled(TestOpLogBase):
    def setUp(self):
        super(TestOpLogEndpointEnabled, self).setUp()

        self.app.config['OPLOG'] = True
        self.app.config['OPLOG_ENDPOINT'] = 'oplog'
        self.oplog_reset()

    def test_oplog_hook(self):
        def oplog_callback(resource, entries):
            for entry in entries:
                entry['extra'] = {'customfield': 'customvalue'}

        self.app.on_oplog_push += oplog_callback

        r = self.test_client.post(self.known_resource_url,
                                  data=json.dumps(self.data),
                                  headers=self.headers,
                                  environ_base={'REMOTE_ADDR': '127.0.0.1'})

        # oplog enpoint does not expose the 'extra' field
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'POST')
        self.assertTrue('extra' not in oplog_entry)

        # however the oplog collection has the field.
        db = self.connection[MONGO_DBNAME]
        cursor = db.oplog.find()
        self.assertEqual(cursor.count(), 1)
        oplog_entry = cursor[0]
        self.assertTrue('extra' in oplog_entry)
        self.assertTrue('customvalue' in oplog_entry['extra']['customfield'])

        # enable 'extra' field for the endpoint
        self.app.config['OPLOG_RETURN_EXTRA_FIELD'] = True
        self.oplog_reset()

        # now the oplog endpoint includes the 'extra' field
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'POST')
        self.assertTrue('extra' in oplog_entry)
        self.assertTrue('customvalue' in oplog_entry['extra']['customfield'])

    def test_post_oplog(self):
        r = self.test_client.post(
            self.different_resource_url,
            data=json.dumps({'username': 'test', 'ref':
                             '1234567890123456789012345'}),
            headers=self.headers, environ_base={'REMOTE_ADDR': '127.0.0.1'})

        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'POST')
        self.assertTrue('extra' not in oplog_entry)

    def test_patch_oplog(self):
        self.headers.append(('If-Match', self.item_etag))
        r = self.test_client.patch(self.item_id_url,
                                   data=json.dumps(self.data),
                                   headers=self.headers,
                                   environ_base={'REMOTE_ADDR': '127.0.0.1'})
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'PATCH')

    def test_put_oplog(self):
        self.headers.append(('If-Match', self.item_etag))
        r = self.test_client.put(self.item_id_url,
                                 data=json.dumps(self.data),
                                 headers=self.headers,
                                 environ_base={'REMOTE_ADDR': '127.0.0.1'})
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'PUT')

    def test_put_oplog_does_not_alter_document(self):
        """ Make sure we don't alter document ETag when performing an
        oplog_push. See #590. """
        self.headers.append(('If-Match', self.item_etag))
        r = self.test_client.put(self.item_id_url,
                                 data=json.dumps(self.data),
                                 headers=self.headers,
                                 environ_base={'REMOTE_ADDR': '127.0.0.1'})

        etag1 = json.loads(r.get_data())['_etag']
        etag2 = json.loads(
            self.test_client.get(self.item_id_url).get_data())['_etag']
        self.assertEqual(etag1, etag2)

    def test_delete_oplog(self):
        self.headers.append(('If-Match', self.item_etag))
        r = self.test_client.delete(self.item_id_url,
                                    headers=self.headers,
                                    environ_base={'REMOTE_ADDR': '127.0.0.1'})
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'DELETE')

    def test_soft_delete_oplog(self):
        r, s = self.parse_response(self.test_client.get(self.item_id_url))
        doc_date = r[config.LAST_UPDATED]
        time.sleep(1)

        self.domain[self.known_resource]['soft_delete'] = True

        self.headers.append(('If-Match', self.item_etag))
        r = self.test_client.delete(self.item_id_url,
                                    headers=self.headers,
                                    environ_base={'REMOTE_ADDR': '127.0.0.1'})
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'DELETE')
        self.assertTrue(doc_date != oplog_entry[config.LAST_UPDATED])

    def test_post_oplog_with_basic_auth(self):
        self.domain['contacts']['authentication'] = ValidBasicAuth
        self.headers.append(('Authorization', 'Basic YWRtaW46c2VjcmV0'))
        r = self.test_client.post(self.known_resource_url,
                                  data=json.dumps(self.data),
                                  headers=self.headers,
                                  environ_base={'REMOTE_ADDR': '127.0.0.1'})
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'POST', 'admin')

    def test_post_oplog_with_token_auth(self):
        self.domain['contacts']['authentication'] = ValidTokenAuth
        self.headers.append(('Authorization', 'Basic dGVzdF90b2tlbjo='))
        r = self.test_client.post(self.known_resource_url,
                                  data=json.dumps(self.data),
                                  headers=self.headers,
                                  environ_base={'REMOTE_ADDR': '127.0.0.1'})
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'POST', 'test_token')

    def test_post_oplog_with_hmac_auth(self):
        self.domain['contacts']['authentication'] = ValidHMACAuth
        self.headers.append(('Authorization', 'admin:secret'))
        r = self.test_client.post(self.known_resource_url,
                                  data=json.dumps(self.data),
                                  headers=self.headers,
                                  environ_base={'REMOTE_ADDR': '127.0.0.1'})
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'POST', 'admin')

    def patch(self, url, data, headers=[], content_type='application/json'):
        headers.append(('Content-Type', content_type))
        headers.append(('If-Match', self.item_etag))
        r = self.test_client.patch(url, data=json.dumps(data), headers=headers)
        return self.parse_response(r)

    def put(self, url, data, headers=[], content_type='application/json'):
        headers.append(('Content-Type', content_type))
        headers.append(('If-Match', self.item_etag))
        r = self.test_client.put(url, data=json.dumps(data), headers=headers)
        return self.parse_response(r)


class TestTickets(TestBase):
    def test_ticket_681(self):
        # See https://github.com/pyeve/eve/issues/681
        with self.app.test_request_context('not_an_existing_endpoint'):
            self.app.data.driver.db['again']
