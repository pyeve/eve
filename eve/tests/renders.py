# -*- coding: utf-8 -*-

from eve.tests import TestBase
import simplejson as json


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
        self.assertTrue('&amp;' in r.data)

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

    def test_CORS_OPTIONS(self):
        r = self.test_client.open('/', method='OPTIONS')
        self.assertFalse('Access-Control-Allow-Origin' in r.headers)
        self.assertFalse('Access-Control-Allow-Methods' in r.headers)
        self.assertFalse('Access-Control-Allow-Max-Age' in r.headers)

        self.app.config['X_DOMAINS'] = '*'
        r = self.test_client.open('/', method='OPTIONS',
                                  headers=[('Origin', 'http://example.com')])
        self.assertEqual(r.headers['Access-Control-Allow-Origin'], '*')

        self.app.config['X_DOMAINS'] = ['http://example.com',
                                        'http://1on1.com']
        r = self.test_client.open('/', method='OPTIONS',
                                  headers=[('Origin', 'http://example.com')])
        self.assertEqual(r.headers['Access-Control-Allow-Origin'],
                         'http://example.com, http://1on1.com')

        self.assertTrue('Access-Control-Allow-Origin' in r.headers)
        self.assertTrue('Access-Control-Allow-Max-Age' in r.headers)

        r = self.test_client.get('/', headers=[('Origin',
                                                'http://not_an_example.com')])
        self.assertEqual(r.headers['Access-Control-Allow-Origin'],
                         'http://example.com, http://1on1.com')

        r = self.test_client.open('/', method='OPTIONS',
                                  headers=[('Origin',
                                            'http://not_an_example.com')])
        self.assertEqual(r.headers['Access-Control-Allow-Origin'],
                         'http://example.com, http://1on1.com')


class TestEventHooks(TestBase):

    def setUp(self):
        super(TestEventHooks, self).setUp()
        self.passed = False
        self.callback_value = None
        self.documents = None

    def test_on_get(self):
        def general_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_get += general_hook
        # homepage
        self.test_client.get('/')
        self.assertEqual(self.callback_value, None)
        # resource endpoint
        self.test_client.get(self.known_resource_url)
        self.assertEqual(self.callback_value, self.known_resource)
        # document endpoint
        self.test_client.get(self.item_id_url)
        self.assertEqual(self.callback_value, self.known_resource)

    def test_get_resource(self):
        def resource_hook(request, payload):
            self.passed = True
        self.app.on_get_contacts += resource_hook
        # resource endpoint
        self.test_client.get(self.known_resource_url)
        self.assertTrue(self.passed)
        # document endpoint
        self.passed = False
        self.test_client.get(self.item_id_url)
        self.assertTrue(self.passed)

    def test_on_post(self):
        def general_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_post += general_hook
        self.post()
        self.assertEqual(self.callback_value, self.known_resource)

    def test_on_post_resource(self):
        def resource_hook(request, payload):
            self.passed = True
        self.app.on_post_contacts += resource_hook
        self.post()
        self.assertTrue(self.passed)

    def test_on_patch(self):
        def general_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_patch += general_hook
        self.patch()
        self.assertEqual(self.callback_value, self.known_resource)

    def test_on_patch_resource(self):
        def resource_hook(resource, request, payload):
            self.passed = True
        self.app.on_patch += resource_hook
        self.patch()
        self.assertTrue(self.passed)

    def test_on_patch_with_post_override(self):
        def global_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_patch += global_hook
        self.patch()
        self.post(extra=[('X-HTTP-Method-Override', True)])
        self.assertEqual(self.callback_value, self.known_resource)

    def test_on_patch_with_post_override_resource(self):
        def resource_hook(request, payload):
            self.passed = True
        self.app.on_patch_contacts += resource_hook
        self.patch()
        self.post(extra=[('X-HTTP-Method-Override', True)])
        self.assertTrue(self.passed)

    def test_on_delete(self):
        def general_hook(resource, request, payload):
            self.callback_value = resource
        self.app.on_delete += general_hook
        self.delete()
        self.assertEqual(self.callback_value, self.known_resource)

    def test_on_delete_resource(self):
        def resource_hook(resource, request, payload):
            self.passed = True
        self.app.on_delete += resource_hook
        self.delete()
        self.assertTrue(self.passed)

    def test_on_posting(self):
        def general_hook(resource, documents):
            self.assertEqual(resource, self.known_resource)
            self.assertEqual(len(documents), 1)
            self.passed = True
        self.app.on_posting += general_hook
        self.post()
        self.assertTrue(self.passed)

    def test_on_posting_resource(self):
        def resource_hook(documents):
            self.assertEqual(len(documents), 1)
            self.passed = True
        self.app.on_posting_contacts += resource_hook
        self.post()
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
