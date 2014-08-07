from datetime import datetime

from bson import ObjectId

from eve.tests import TestBase
from eve.methods.common import serialize, resource_link


class TestSerializer(TestBase):
    def test_serialize_subdocument(self):
        # tests fix for #244, serialization of sub-documents.
        schema = {'personal': {'type': 'dict',
                               'schema': {'best_friend': {'type': 'objectid'},
                                          'born': {'type': 'datetime'}}}}
        doc = {'personal': {'best_friend': '50656e4538345b39dd0414f0',
                            'born': 'Tue, 06 Nov 2012 10:33:31 GMT'}}
        with self.app.app_context():
            serialized = serialize(doc, schema=schema)
        self.assertTrue(
            isinstance(serialized['personal']['best_friend'], ObjectId))
        self.assertTrue(
            isinstance(serialized['personal']['born'], datetime))


class TestLinks(TestBase):
    def test_resource_link(self):
        with self.app.test_request_context():
            self.app.config['URL_PROTOCOL'] = 'http'
            self.app.config['SERVER_NAME'] = '0.0.0.0:5000'
            self.assertEqual(resource_link(), 'http://0.0.0.0:5000')
