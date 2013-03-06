# -*- coding: utf-8 -*-

from eve.tests import TestBase


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
