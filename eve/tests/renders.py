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
