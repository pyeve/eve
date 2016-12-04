# -*- coding: utf-8 -*-

from ast import literal_eval
from eve.tests import TestBase
import simplejson as json
import eve
import os


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
        self.assertEqual(len(response), 3)

        resource = response.get('_items')
        self.assertTrue(isinstance(resource, list))
        links = response.get('_links')
        self.assertTrue(isinstance(links, dict))
        meta = response.get('_meta')
        self.assertTrue(isinstance(meta, dict))

    def test_response_pretty(self):
        # check if pretty printing was successful by checking the length of the
        # response since pretty printing the respone makes it longer and not
        # type dict anymore
        self.r = self.test_client.get('/%s/?pretty' % self.empty_resource)
        response = self.r.get_data().decode()
        self.assertEqual(len(response), 300)


class TestNoHateoas(TestBase):

    def setUp(self):
        super(TestNoHateoas, self).setUp()
        self.app.config['HATEOAS'] = False
        self.domain[self.known_resource]['hateoas'] = False

    def test_get_no_hateoas_resource(self):
        r = self.test_client.get(self.known_resource_url)
        response = json.loads(r.get_data().decode())
        self.assertTrue(isinstance(response, dict))
        self.assertEqual(len(response['_items']), 25)
        item = response['_items'][0]
        self.assertTrue(isinstance(item, dict))
        self.assertTrue('_links' not in response)

    def test_get_no_hateoas_item(self):
        r = self.test_client.get(self.item_id_url)
        response = json.loads(r.get_data().decode())
        self.assertTrue(isinstance(response, dict))
        self.assertTrue('_links' not in response)

    def test_get_no_hateoas_homepage(self):
        r = self.test_client.get('/')
        self.assert200(r.status_code)

    def test_get_no_hateoas_homepage_reply(self):
        r = self.test_client.get('/')
        resp = json.loads(r.get_data().decode())
        self.assertEqual(resp, {})

        self.app.config['INFO'] = '_info'

        r = self.test_client.get('/')
        resp = json.loads(r.get_data().decode())
        self.assertEqual(resp['_info']['server'], 'Eve')
        self.assertEqual(resp['_info']['version'], eve.__version__)

        settings_file = os.path.join(self.this_directory, 'test_version.py')
        self.app = eve.Eve(settings=settings_file)
        self.app.config['INFO'] = '_info'

        r = self.app.test_client().get('/v1')
        resp = json.loads(r.get_data().decode())
        self.assertEqual(resp['_info']['api_version'],
                         self.app.config['API_VERSION'])
        self.assertEqual(resp['_info']['server'], 'Eve')
        self.assertEqual(resp['_info']['version'], eve.__version__)

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
