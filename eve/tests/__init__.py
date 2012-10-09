import re
import eva
import unittest
import simplejson as json
from datetime import datetime


class TestBase(unittest.TestCase):

    def setUp(self):
        reload(eva)
        self.app = eva.app
        self.test_client = self.app.test_client()

        #TODO provide a test DOMAIN so we don't rely on default_settings.py's
        self.domain = self.app.config['DOMAIN']
        self.known_resource = 'contacts'
        self.known_item_by_id = '4f46445fc88e201858000000'
        self.known_item_by_name = 'anna'
        self.empty_resource = 'invoices'
        self.unknown_resource = 'unknown'
        self.unknown_item_by_id = '4f46445fc88e201858000000'
        self.unknown_item_by_name = 'unknown'

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert301(self, status):
        self.assertEqual(status, 301)

    def assert404(self, status):
        self.assertEqual(status, 404)

    def assert304(self, status):
        self.assertEqual(status, 304)


class TestMethodsBase(TestBase):

    def response(self, resource, query='', item=None):
        if resource in self.domain:
            resource = self.domain[resource]['url']
        if item:
            request = '/%s/%s/' % (resource, item)
        else:
            request = '/%s/%s' % (resource, query)

        r = self.test_client.get(request)
        value = None
        if r.status_code != 404:
            value = json.loads(r.data)['response']
        return value, r.status_code

    def assertExpires(self, resource):
        # TODO if we ever get access to response.date (it is None), compare
        # it with Expires
        r = self.test_client.get(resource)

        expires = r.headers.get('Expires')
        self.assertTrue(expires is not None)

    def assertCacheControl(self, resource):
        r = self.test_client.get(resource)

        cache_control = r.headers.get('Cache-Control')
        self.assertTrue(cache_control is not None)
        self.assertEqual(cache_control,
                         self.domain[self.known_resource]['cache_control'])

    def assertIfModifiedSince(self, resource):
        r = self.test_client.get(resource)

        last_modified = r.headers.get('Last-Modified')
        self.assertTrue(last_modified is not None)
        r = self.test_client.get(resource, headers=[('If-Modified-Since',
                                                    last_modified)])
        self.assert304(r.status_code)
        self.assertEqual(r.data, '')

    def assertItem(self, item):
        self.assertIs(type(item), dict)

        _id = item.get(self.app.config['ID_FIELD'])
        self.assertTrue(_id is not None)
        match = re.compile(self.app.config['ITEM_URL']).match(_id)
        self.assertTrue(match is not None)
        self.assertEqual(match.group(), _id)

        updated_on = item.get(self.app.config['LAST_UPDATED'])
        self.assertTrue(updated_on is not None)
        try:
            datetime.strptime(updated_on, self.app.config['DATE_FORMAT'])
        except Exception, e:
            self.fail('Cannot convert field "%s" to datetime: %s' %
                      (self.app.config['LAST_UPDATED'], e))

        link = item.get('link')
        self.assertTrue(link is not None)
        self.assertItemLink(link, _id)

    def assertHomeLink(self, links):
        found = False
        for link in links:
            if "title='home'" in link and \
               "href='%s'" % self.app.config['BASE_URI'] in link:
                found = True
                break
        self.assertTrue(found)

    def assertResourceLink(self, links, resource):
        url = self.domain[resource]['url']
        found = False
        for link in links:
            if "title='%s'" % url in link and \
               "href='%s/%s/" % (self.app.config['BASE_URI'], url) in link:
                found = True
                break
        self.assertTrue(found)

    def assertNextLink(self, links, page):
        found = False
        for link in links:
            if "title='next page'" in link and "rel='next'" in link and \
               'page=%d' % page in link:
                found = True
        self.assertTrue(found)

    def assertPrevLink(self, links, page):
        found = False
        for link in links:
            if "title='previous page'" in link and "rel='prev'" in link:
                if page > 1:
                    found = 'page=%d' % page in link
                else:
                    found = True
        self.assertTrue(found)

    def assertItemLink(self, link, item_id):
        self.assertTrue("rel='self'" in link and '/%s/' % item_id in link)
