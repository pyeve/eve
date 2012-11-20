# -*- coding: utf-8 -*-

from ast import literal_eval
from eve.tests import TestBase


class TestResponse(TestBase):

    def setUp(self):
        super(TestResponse, self).setUp()
        self.r = self.test_client.get('/%s/' % self.empty_resource)

    def test_response_data(self):
        response = None
        try:
            response = literal_eval(self.r.data)
        except:
            self.fail('standard response cannot be converted to a dict')
        self.assertIs(type(response), dict)

    def test_response_object(self):
        response = literal_eval(self.r.data).get('response')
        self.assertEqual(type(response), dict)
        self.assertEqual(len(response), 2)

        resource = response.get(self.empty_resource)
        self.assertEqual(type(resource), list)
        links = response.get('links')
        self.assertEqual(type(links), list)
