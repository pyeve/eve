from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId

from eve.tests import TestBase
from eve.methods.common import serialize


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
        }
        with self.app.app_context():
            # Success
            res = serialize(
                {
                    'id': '50656e4538345b39dd0414f0',
                    'date': 'Tue, 06 Nov 2012 10:33:31 GMT',
                    'count': '42',
                    'average': '42.42',
                },
                schema=schema
            )
            self.assertTrue(isinstance(res['id'], ObjectId))
            self.assertTrue(isinstance(res['date'], datetime))
            self.assertTrue(isinstance(res['count'], int))
            self.assertTrue(isinstance(res['average'], float))

            # Fail
            with self.assertRaises(InvalidId):
                serialize({'id': 'test'}, schema=schema)

            with self.assertRaises(ValueError):
                serialize({'date': 'test'}, schema=schema)

            with self.assertRaises(ValueError):
                serialize({'count': '10.0'}, schema=schema)

            with self.assertRaises(ValueError):
                serialize({'average': 'test'}, schema=schema)
