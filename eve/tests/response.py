# -*- coding: utf-8 -*-

from ast import literal_eval
from eve.tests import TestBase
import simplejson as json


class TestResponse(TestBase):

    def setUp(self):
        super(TestResponse, self).setUp()
        self.r = self.test_client.get('/%s/' % self.empty_resource)

    def test_response_data(self):
        response = None
        try:
            response = literal_eval(self.r.get_data().decode())
        except:
            self.fail('standard response cannot be converted to a dict')
        self.assertTrue(isinstance(response, dict))

    def test_response_object(self):
        response = literal_eval(self.r.get_data().decode())
        self.assertTrue(isinstance(response, dict))
        self.assertEqual(len(response), 2)

        resource = response.get('_items')
        self.assertTrue(isinstance(resource, list))
        links = response.get('_links')
        self.assertTrue(isinstance(links, dict))


class TestNoHateoas(TestBase):

    def setUp(self):
        super(TestNoHateoas, self).setUp()
        self.app.config['HATEOAS'] = False
        self.domain[self.known_resource]['hateoas'] = False

    def test_get_no_hateoas_resource(self):
        r = self.test_client.get(self.known_resource_url)
        response = json.loads(r.get_data().decode())
        self.assertTrue(isinstance(response, list))
        self.assertEqual(len(response), 25)
        item = response[0]
        self.assertTrue(isinstance(item, dict))
        self.assertTrue('_links' not in item)

    def test_get_no_hateoas_item(self):
        r = self.test_client.get(self.item_id_url)
        response = json.loads(r.get_data().decode())
        self.assertTrue(isinstance(response, dict))
        self.assertTrue('_links' not in response)

    def test_get_no_hateoas_homepage(self):
        r = self.test_client.get('/')
        self.assert404(r.status_code)

    def test_post_no_hateoas(self):
        data = {'item1': json.dumps({"ref": "1234567890123456789054321"})}
        headers = [('Content-Type', 'application/x-www-form-urlencoded')]
        r = self.test_client.post(self.known_resource_url, data=data,
                                  headers=headers)
        response = json.loads(r.get_data().decode())
        self.assertTrue('_links' not in response)

    def test_patch_no_hateoas(self):
        data = {'item1': json.dumps({"ref": "0000000000000000000000000"})}
        headers = [('Content-Type', 'application/x-www-form-urlencoded'),
                   ('If-Match', self.item_etag)]
        r = self.test_client.patch(self.item_id_url, data=data,
                                   headers=headers)
        response = json.loads(r.get_data().decode())
        self.assertTrue('_links' not in response)
