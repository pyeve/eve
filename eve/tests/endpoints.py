# -*- coding: utf-8 -*-

from eve.tests import TestBase

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
