from datetime import datetime

import simplejson as json
from bson import ObjectId

from eve.methods.common import serialize
from eve.tests import TestBase
from eve.tests.test_settings import MONGO_DBNAME
from eve.utils import config


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
            }
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
                    }
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

    def oplog_get(self, url='/oplog'):
        r = self.test_client.get(url)
        return self.parse_response(r)

    def assertOpLogEntry(self, entry, op):
        self.assertTrue('r' in entry)
        self.assertTrue('i' in entry)
        self.assertTrue(config.LAST_UPDATED in entry)
        self.assertTrue(config.DATE_CREATED in entry)
        self.assertTrue('o' in entry)
        self.assertEqual(entry['o'], op)
        self.assertTrue('127.0.0.1' in entry['ip'])
        if op in ('PATCH', 'PUT', 'DELETE'):
            self.assertTrue('c' in entry)


class TestOpLogEndpointDisabled(TestOpLogBase):
    def setUp(self):
        super(TestOpLogEndpointDisabled, self).setUp()

        self.app.config['OPLOG'] = True
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

    def test_post_oplog(self):
        r = self.test_client.post(self.known_resource_url,
                                  data=json.dumps(self.data),
                                  headers=self.headers,
                                  environ_base={'REMOTE_ADDR': '127.0.0.1'})
        r, status = self.oplog_get()
        self.assert200(status)
        self.assertEqual(len(r['_items']), 1)
        oplog_entry = r['_items'][0]
        self.assertOpLogEntry(oplog_entry, 'POST')

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
        # See https://github.com/nicolaiarocci/eve/issues/681
        with self.app.test_request_context('not_an_existing_endpoint'):
            self.app.data.driver.db['again']
