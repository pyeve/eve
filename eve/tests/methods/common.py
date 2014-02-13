from eve.tests import TestBase
from eve.methods.common import serialize
import simplejson as json
from datetime import datetime
from bson import ObjectId


class TestPreEventHooks(TestBase):
    def setUp(self):
        super(TestPreEventHooks, self).setUp()
        self.passed = False

    def test_on_GET(self):
        def pre_hook(resource, request):
            self.passed = True
        self.app.on_pre_GET += pre_hook
        # resource endpoint
        self.test_client.get(self.known_resource_url)
        self.assertTrue(self.passed)
        # document endpoint
        self.passed = False
        self.test_client.get(self.item_id_url)
        self.assertTrue(self.passed)

    def test_on_GET_resource(self):
        def pre_hook(request):
            self.passed = True
        self.app.on_pre_GET_contacts += pre_hook
        # resource endpoint
        self.test_client.get(self.known_resource_url)
        self.assertTrue(self.passed)
        # document endpoint
        self.passed = False
        self.test_client.get(self.item_id_url)
        self.assertTrue(self.passed)

    def test_on_POST(self):
        def pre_hook(resource, request):
            self.passed = True
        self.app.on_pre_POST += pre_hook
        self.post()
        self.assertTrue(self.passed)

    def test_on_POST_resource(self):
        def pre_hook(request):
            self.passed = True
        self.app.on_pre_POST_contacts += pre_hook
        self.post()
        self.assertTrue(self.passed)

    def test_on_PATCH(self):
        def pre_hook(resource, request):
            self.passed = True
        self.app.on_pre_PATCH += pre_hook
        self.patch()
        self.assertTrue(self.passed)

    def test_on_PATCH_resource(self):
        def pre_hook(request):
            self.passed = True
        self.app.on_pre_PATCH_contacts += pre_hook
        self.patch()
        self.assertTrue(self.passed)

    def test_on_PUT(self):
        def pre_hook(resource, request):
            self.passed = True
        self.app.on_pre_PUT += pre_hook
        self.put()
        self.assertTrue(self.passed)

    def test_on_PUT_resource(self):
        def pre_hook(request):
            self.passed = True
        self.app.on_pre_PUT_contacts += pre_hook
        self.put()
        self.assertTrue(self.passed)

    def test_on_DELETE(self):
        def pre_hook(resource, request):
            self.passed = True
        self.app.on_pre_DELETE += pre_hook
        self.delete()
        self.assertTrue(self.passed)

    def test_on_DELETE_resource(self):
        def pre_hook(request):
            self.passed = True
        self.app.on_pre_DELETE_contacts += pre_hook
        self.delete()
        self.assertTrue(self.passed)

    def post(self, extra=None):
        headers = [('Content-Type', 'application/json')]
        data = json.dumps({"ref": "0123456789012345678901234"})
        if extra:
            headers.extend(extra)
        self.test_client.post(self.known_resource_url, data=data,
                              headers=headers)

    def patch(self):
        headers = [('Content-Type', 'application/json'),
                   ('If-Match', self.item_etag)]
        data = json.dumps({"ref": "i'm unique"})
        self.test_client.patch(self.item_id_url, data=data, headers=headers)

    def delete(self):
        self.test_client.delete(self.item_id_url, headers=[('If-Match',
                                                            self.item_etag)])

    def put(self):
        headers = [('Content-Type', 'application/json'),
                   ('If-Match', self.item_etag)]
        data = json.dumps({"ref": "0123456789012345678901234"})
        self.test_client.put(self.item_id_url, data=data, headers=headers)


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
