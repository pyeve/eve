# -*- coding: utf-8 -*-

from eve.tests import TestBase
from eve import Eve

# TODO find a reliable way to test item endpoints
# which are based on regex, maybe reverse them?
# http://stackoverflow.com/questions/492716/reversing-a-regular-expression-in-python
#
# but there must be an easier way out :)


class TestEndPoints(TestBase):

    def test_homepage(self):
        r = self.test_client.get('/')
        self.assertEqual(r.status_code, 200)

    def test_resource_endpoint(self):
        for settings in self.domain.values():
            r = self.test_client.get('/%s/' % settings['url'])
            self.assert200(r.status_code)

            r = self.test_client.get('/%s' % settings['url'])
            self.assert301(r.status_code)

    def test_item_endpoint(self):
        pass

    def test_unknown_endpoints(self):
        r = self.test_client.get('/%s/' % self.unknown_resource)
        self.assert404(r.status_code)

        r = self.test_client.get(self.unknown_item_id_url)
        self.assert404(r.status_code)

        r = self.test_client.get(self.unknown_item_name_url)
        self.assert404(r.status_code)

    def test_api_version(self):
        settings_file = 'eve/tests/test_version.py'
        self.prefixapp = Eve(settings=settings_file)
        self.test_prefix = self.prefixapp.test_client()
        r = self.test_prefix.get('/')
        self.assert404(r.status_code)
        r = self.test_prefix.get('/v1/')
        self.assert200(r.status_code)

        r = self.test_prefix.get('/contacts/')
        self.assert404(r.status_code)
        r = self.test_prefix.get('/v1/contacts')
        self.assert301(r.status_code)
        r = self.test_prefix.get('/v1/contacts/')
        self.assert200(r.status_code)

    def test_api_prefix(self):
        settings_file = 'eve/tests/test_prefix.py'
        self.prefixapp = Eve(settings=settings_file)
        self.test_prefix = self.prefixapp.test_client()
        r = self.test_prefix.get('/')
        self.assert404(r.status_code)
        r = self.test_prefix.get('/prefix/')
        self.assert200(r.status_code)

        r = self.test_prefix.get('/prefix/contacts')
        self.assert301(r.status_code)
        r = self.test_prefix.get('/prefix/contacts/')
        self.assert200(r.status_code)

    def test_api_prefix_version(self):
        settings_file = 'eve/tests/test_prefix_version.py'
        self.prefixapp = Eve(settings=settings_file)
        self.test_prefix = self.prefixapp.test_client()
        r = self.test_prefix.get('/')
        self.assert404(r.status_code)
        r = self.test_prefix.get('/prefix/v1/')
        self.assert200(r.status_code)
        r = self.test_prefix.get('/prefix/v1/contacts')
        self.assert301(r.status_code)
        r = self.test_prefix.get('/prefix/v1/contacts/')
        self.assert200(r.status_code)
