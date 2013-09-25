# -*- coding: utf-8 -*-

from eve.tests import TestBase
import simplejson as json
from eve.utils import api_prefix


class TestRenders(TestBase):

    def test_default_render(self):
        r = self.test_client.get('/')
        self.assertEqual(r.content_type, 'application/json')

    def test_json_render(self):
        r = self.test_client.get('/', headers=[('Accept', 'application/json')])
        self.assertEqual(r.content_type, 'application/json')

    def test_xml_render(self):
        r = self.test_client.get('/', headers=[('Accept', 'application/xml')])
        self.assertTrue('application/xml' in r.content_type)

    def test_xml_url_escaping(self):
        r = self.test_client.get('%s?max_results=1' % self.known_resource_url,
                                 headers=[('Accept', 'application/xml')])
        self.assertTrue(b'&amp;' in r.get_data())

    def test_unknown_render(self):
        r = self.test_client.get('/', headers=[('Accept', 'application/html')])
        self.assertEqual(r.content_type, 'application/json')

    def test_CORS(self):
        r = self.test_client.get('/')
        self.assertFalse('Access-Control-Allow-Origin' in r.headers)
        self.assertFalse('Access-Control-Allow-Methods' in r.headers)
        self.assertFalse('Access-Control-Allow-Max-Age' in r.headers)

        self.app.config['X_DOMAINS'] = '*'
        r = self.test_client.get('/', headers=[('Origin',
                                                'http://example.com')])
        self.assertEqual(r.headers['Access-Control-Allow-Origin'], '*')

        self.app.config['X_DOMAINS'] = ['http://example.com',
                                        'http://1on1.com']
        r = self.test_client.get('/', headers=[('Origin',
                                                'http://example.com')])
        self.assertEqual(r.headers['Access-Control-Allow-Origin'],
                         'http://example.com, http://1on1.com')

        self.assertTrue('Access-Control-Allow-Origin' in r.headers)
        self.assertTrue('Access-Control-Allow-Max-Age' in r.headers)

        r = self.test_client.get('/', headers=[('Origin',
                                                'http://not_an_example.com')])
        self.assertEqual(r.headers['Access-Control-Allow-Origin'],
                         'http://example.com, http://1on1.com')

    def test_CORS_OPTIONS(self, url='/', methods=[]):
        r = self.test_client.open(url, method='OPTIONS')
        self.assertFalse('Access-Control-Allow-Origin' in r.headers)
        self.assertFalse('Access-Control-Allow-Methods' in r.headers)
        self.assertFalse('Access-Control-Allow-Max-Age' in r.headers)
        self.assert200(r.status_code)

        self.app.config['X_DOMAINS'] = '*'
        r = self.test_client.open(url, method='OPTIONS',
                                  headers=[('Origin', 'http://example.com')])
        self.assert200(r.status_code)
        self.assertEqual(r.headers['Access-Control-Allow-Origin'], '*')
        for m in methods:
            self.assertTrue(m in r.headers['Access-Control-Allow-Methods'])

        self.app.config['X_DOMAINS'] = ['http://example.com',
                                        'http://1on1.com']
        r = self.test_client.open(url, method='OPTIONS',
                                  headers=[('Origin', 'http://example.com')])
        self.assert200(r.status_code)
        self.assertEqual(r.headers['Access-Control-Allow-Origin'],
                         'http://example.com, http://1on1.com')

        for m in methods:
            self.assertTrue(m in r.headers['Access-Control-Allow-Methods'])

        self.assertTrue('Access-Control-Allow-Origin' in r.headers)
        self.assertTrue('Access-Control-Allow-Max-Age' in r.headers)

        r = self.test_client.get(url, headers=[('Origin',
                                                'http://not_an_example.com')])
        self.assert200(r.status_code)
        self.assertEqual(r.headers['Access-Control-Allow-Origin'],
                         'http://example.com, http://1on1.com')
        for m in methods:
            self.assertTrue(m in r.headers['Access-Control-Allow-Methods'])

    def test_CORS_OPTIONS_resources(self):
        prefix = api_prefix(self.app.config['URL_PREFIX'],
                            self.app.config['API_VERSION'])

        for resource, settings in self.app.config['DOMAIN'].items():

            # resource endpoint
            url = '%s/%s/' % (prefix, settings['url'])
            methods = settings['resource_methods'] + ['OPTIONS']
            self.test_CORS_OPTIONS(url, methods)


class TestEventHooks(TestBase):
    #TODO not sure this is the right place for this class really.

    def setUp(self):
        super(TestEventHooks, self).setUp()
        self.passed = False
        self.callback_value = None
        self.documents = None

    def test_on_GET(self):
        def general_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_GET += general_hook
        # homepage
        self.test_client.get('/')
        self.assertEqual(self.callback_value, None)
        # resource endpoint
        self.test_client.get(self.known_resource_url)
        self.assertEqual(self.callback_value, self.known_resource)
        # document endpoint
        self.test_client.get(self.item_id_url)
        self.assertEqual(self.callback_value, self.known_resource)

    def test_GET_resource(self):
        def resource_hook(request, payload):
            self.passed = True
        self.app.on_GET_contacts += resource_hook
        # resource endpoint
        self.test_client.get(self.known_resource_url)
        self.assertTrue(self.passed)
        # document endpoint
        self.passed = False
        self.test_client.get(self.item_id_url)
        self.assertTrue(self.passed)

    def test_on_POST(self):
        def general_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_POST += general_hook
        self.post()
        self.assertEqual(self.callback_value, self.known_resource)

    def test_on_POST_resource(self):
        def resource_hook(request, payload):
            self.passed = True
        self.app.on_POST_contacts += resource_hook
        self.post()
        self.assertTrue(self.passed)

    def test_on_PATCH(self):
        def general_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_PATCH += general_hook
        self.patch()
        self.assertEqual(self.callback_value, self.known_resource)

    def test_on_PATCH_resource(self):
        def resource_hook(request, payload):
            self.passed = True
        self.app.on_PATCH_contacts += resource_hook
        self.patch()
        self.assertTrue(self.passed)

    def test_on_PUT(self):
        def general_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_PUT += general_hook
        self.put()
        self.assertEqual(self.callback_value, self.known_resource)

    def test_on_PUT_resource(self):
        def resource_hook(request, payload):
            self.passed = True
        self.app.on_PUT_contacts += resource_hook
        self.put()
        self.assertTrue(self.passed)

    def test_on_DELETE(self):
        def general_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_DELETE += general_hook
        self.delete()
        self.assertEqual(self.callback_value, self.known_resource)

    def test_on_DELETE_resource(self):
        def resource_hook(request, payload):
            self.passed = True
        self.app.on_DELETE_contacts += resource_hook
        self.delete()
        self.assertTrue(self.passed)

    def test_on_insert_POST(self):
        def general_hook(resource, documents):
            self.assertEqual(resource, self.known_resource)
            self.assertEqual(len(documents), 1)
            self.passed = True
        self.app.on_insert += general_hook
        self.post()
        self.assertTrue(self.passed)

    def test_on_insert_PUT(self):
        def general_hook(resource, documents):
            self.assertEqual(resource, self.known_resource)
            self.assertEqual(len(documents), 1)
            self.passed = True
        self.app.on_insert += general_hook
        self.put()
        self.assertTrue(self.passed)

    def test_on_insert_resource_POST(self):
        def resource_hook(documents):
            self.assertEqual(len(documents), 1)
            self.passed = True
        self.app.on_insert_contacts += resource_hook
        self.post()
        self.assertTrue(self.passed)

    def test_on_insert_resource_PUT(self):
        def resource_hook(documents):
            self.assertEqual(len(documents), 1)
            self.passed = True
        self.app.on_insert_contacts += resource_hook
        self.put()
        self.assertTrue(self.passed)

    def test_on_fetch(self):
        def general_hook(resource, documents):
            self.assertEqual(resource, self.known_resource)
            self.assertEqual(len(documents), 25)
            self.passed = True
        self.app.on_fetch_resource += general_hook
        self.test_client.get(self.known_resource_url)
        self.assertTrue(self.passed)

    def test_on_fetch_resource(self):
        def resource_hook(documents):
            self.assertEqual(len(documents), 25)
            self.passed = True
        self.app.on_fetch_resource_contacts += resource_hook
        self.test_client.get(self.known_resource_url)
        self.assertTrue(self.passed)

    def test_on_fetch_item(self):
        def item_hook(resource, _id, document):
            self.assertEqual(str(_id), self.item_id)
            self.passed = True
        self.app.on_fetch_item += item_hook
        self.test_client.get(self.item_id_url)
        self.assertTrue(self.passed)

    def post(self, extra=None):
        headers = [('Content-Type', 'application/x-www-form-urlencoded')]
        data = {'item1': json.dumps({"ref": "0123456789012345678901234"})}
        if extra:
            headers.extend(extra)
        self.test_client.post(self.known_resource_url, data=data,
                              headers=headers)

    def patch(self):
        headers = [('Content-Type', 'application/x-www-form-urlencoded'),
                   ('If-Match', self.item_etag)]
        data = {'item1': json.dumps({"ref": "i'm unique"})}
        self.test_client.patch(self.item_id_url, data=data, headers=headers)

    def delete(self):
        self.test_client.delete(self.item_id_url, headers=[('If-Match',
                                                            self.item_etag)])

    def put(self):
        headers = [('Content-Type', 'application/x-www-form-urlencoded'),
                   ('If-Match', self.item_etag)]
        data = {'item1': json.dumps({"ref": "0123456789012345678901234"})}
        self.test_client.put(self.item_id_url, data=data, headers=headers)
