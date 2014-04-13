# -*- coding: utf-8 -*-

from eve.tests import TestBase
from eve.utils import api_prefix
from eve.tests.test_settings import MONGO_DBNAME


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

    def test_xml_leaf_escaping(self):
        # test that even xml leaves content is being properly escaped

        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]
        fake_contact = self.random_contacts(1)
        fake_contact[0]['ref'] = "12345 & 67890"
        fake_contact_id = _db.contacts.insert(fake_contact)[0]

        r = self.test_client.get('%s/%s' %
                                 (self.known_resource_url, fake_contact_id),
                                 headers=[('Accept', 'application/xml')])
        self.assertTrue(b'12345 &amp; 6789' in r.get_data())

    def test_unknown_render(self):
        r = self.test_client.get('/', headers=[('Accept', 'application/html')])
        self.assertEqual(r.content_type, 'application/json')

    def test_json_xml_disabled(self):
        self.app.config['JSON'] = False
        self.app.config['XML'] = False
        r = self.test_client.get(self.known_resource_url,
                                 headers=[('Accept', 'application/json')])
        self.assert500(r.status_code)
        r = self.test_client.get(self.known_resource_url,
                                 headers=[('Accept', 'application/xml')])
        self.assert500(r.status_code)
        r = self.test_client.get(self.known_resource_url)
        self.assert500(r.status_code)

    def test_json_disabled(self):
        self.app.config['JSON'] = False
        r = self.test_client.get(self.known_resource_url,
                                 headers=[('Accept', 'application/json')])
        self.assertTrue('application/xml' in r.content_type)
        r = self.test_client.get(self.known_resource_url,
                                 headers=[('Accept', 'application/xml')])
        self.assertTrue('application/xml' in r.content_type)
        r = self.test_client.get(self.known_resource_url)
        self.assertTrue('application/xml' in r.content_type)

    def test_xml_disabled(self):
        self.app.config['XML'] = False
        r = self.test_client.get(self.known_resource_url,
                                 headers=[('Accept', 'application/xml')])
        self.assertEqual(r.content_type, 'application/json')
        r = self.test_client.get(self.known_resource_url,
                                 headers=[('Accept', 'application/json')])
        self.assertEqual(r.content_type, 'application/json')
        r = self.test_client.get(self.known_resource_url)
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

    def test_CORS_MAX_AGE(self):
        self.app.config['X_DOMAINS'] = '*'
        r = self.test_client.get('/', headers=[('Origin',
                                                'http://example.com')])
        self.assertEqual(r.headers['Access-Control-Allow-Max-Age'],
                         '21600')

        self.app.config['X_MAX_AGE'] = 2000
        r = self.test_client.get('/', headers=[('Origin',
                                                'http://example.com')])
        self.assertEqual(r.headers['Access-Control-Allow-Max-Age'],
                         '2000')

    def test_CORS_OPTIONS(self, url='/', methods=None):
        if methods is None:
            methods = []

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

        del(self.domain['peopleinvoices'])
        for _, settings in self.app.config['DOMAIN'].items():

            # resource endpoint
            url = '%s/%s/' % (prefix, settings['url'])
            methods = settings['resource_methods'] + ['OPTIONS']
            self.test_CORS_OPTIONS(url, methods)

    def test_CORS_OPTIONS_item(self):
        prefix = api_prefix(self.app.config['URL_PREFIX'],
                            self.app.config['API_VERSION'])

        url = '%s%s' % (prefix, self.item_id_url)
        methods = (self.domain[self.known_resource]['resource_methods'] +
                   ['OPTIONS'])
        self.test_CORS_OPTIONS(url, methods)
        url = '%s%s/%s' % (prefix, self.known_resource_url, self.item_ref)
        methods = ['GET', 'OPTIONS']
        self.test_CORS_OPTIONS(url, methods)
