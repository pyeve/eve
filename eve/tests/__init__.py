# -*- coding: utf-8 -*-

import re
import unittest
import eve
import string
import random
import simplejson as json
from datetime import datetime, timedelta
from flask.ext.pymongo import Connection
from bson import ObjectId
from eve import Eve, STATUS_ERR
from test_settings import MONGO_PASSWORD, MONGO_USERNAME, MONGO_DBNAME, DOMAIN


class TestBase(unittest.TestCase):

    def setUp(self):
        #reload(eve)
        self.settings_file = 'eve/tests/test_settings.py'
        self.app = Eve(settings=self.settings_file)
        self.test_client = self.app.test_client()

        self.domain = self.app.config['DOMAIN']

        self.known_resource = 'contacts'
        self.known_resource_url = ('/%s/' %
                                   self.domain[self.known_resource]['url'])
        self.empty_resource = 'invoices'
        self.empty_resource_url = '/%s/' % self.empty_resource

        self.unknown_resource = 'unknown'
        self.unknown_resource_url = '/%s/' % self.unknown_resource
        self.unknown_item_id = '4f46445fc88e201858000000'
        self.unknown_item_name = 'unknown'

        self.unknown_item_id_url = ('/%s/%s/' %
                                    (self.domain[self.known_resource]['url'],
                                     self.unknown_item_id))
        self.unknown_item_name_url = ('/%s/%s/' %
                                      (self.domain[self.known_resource]['url'],
                                      self.unknown_item_name))

        self.readonly_resource = 'payments'
        self.readonly_resource_url = (
            '/%s/' % self.domain[self.readonly_resource]['url'])

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert301(self, status):
        self.assertEqual(status, 301)

    def assert404(self, status):
        self.assertEqual(status, 404)

    def assert304(self, status):
        self.assertEqual(status, 304)


class TestMethodsBase(TestBase):

    def setUp(self):
        super(TestMethodsBase, self).setUp()
        response, status = self.get('contacts', '?max_results=2')
        contact = response['contacts'][0]
        self.item_id = contact[self.app.config['ID_FIELD']]
        self.item_name = contact['ref']
        self.item_tid = contact['tid']
        self.item_etag = contact['etag']
        self.item_id_url = ('/%s/%s/' %
                            (self.domain[self.known_resource]['url'],
                             self.item_id))
        self.item_name_url = ('/%s/%s/' %
                              (self.domain[self.known_resource]['url'],
                               self.item_name))
        self.alt_ref = response['contacts'][1]['ref']

        response, status = self.get('payments', '?max_results=1')
        self.readonly_id = response['payments'][0]['_id']
        self.readonly_id_url = ('%s%s/' % (self.readonly_resource_url,
                                           self.readonly_id))

    def get(self, resource, query='', item=None):
        if resource in self.domain:
            resource = self.domain[resource]['url']
        if item:
            request = '/%s/%s/' % (resource, item)
        else:
            request = '/%s/%s' % (resource, query)

        r = self.test_client.get(request)
        return self.parse_response(r)

    def parse_response(self, r):
        v = json.loads(r.data)['response'] if r.status_code == 200 else None
        return v, r.status_code

    def assertValidationError(self, response, key, matches):
        self.assertTrue(key in response)
        k = response[key]
        self.assertTrue('status' in k)
        self.assertTrue(STATUS_ERR in k['status'])
        self.assertTrue('issues' in k)
        issues = k['issues']
        self.assertTrue(len(issues))

        for match in matches:
            self.assertTrue(match in issues[0])

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
               "href='%s'" % self.app.config['SERVER_NAME'] in link:
                found = True
                break
        self.assertTrue(found)

    def assertResourceLink(self, links, resource):
        url = self.domain[resource]['url']
        found = False
        for link in links:
            if "title='%s'" % url in link and \
               "href='%s/%s/" % (self.app.config['SERVER_NAME'], url) in link:
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

    def assert400(self, status):
        self.assertEqual(status, 400)

    def assert403(self, status):
        self.assertEqual(status, 403)

    def assert405(self, status):
        self.assertEqual(status, 405)

    def assert412(self, status):
        self.assertEqual(status, 412)

    @classmethod
    def setUpClass(cls):
        cls._c = Connection()
        cls._c.drop_database(MONGO_DBNAME)
        cls._c[MONGO_DBNAME].add_user(MONGO_USERNAME, MONGO_PASSWORD)
        cls.bulk_insert()
        cls._c.close()

    @classmethod
    def tearDownModule(cls):
        c = Connection()
        c.drop_database(MONGO_DBNAME)
        c.close()

    @classmethod
    def bulk_insert(cls):
        cls._db = cls._c[MONGO_DBNAME]
        cls._db.contacts.insert(cls.random_contacts(100))
        cls._db.payments.insert(cls.random_payments(10))

    @classmethod
    def random_contacts(cls, num):
        schema = DOMAIN['contacts']['schema']
        contacts = []
        for i in range(num):
            dt = datetime.now()
            contact = {
                'ref':  cls.random_string(schema['ref']['maxlength']),
                'prog': i,
                'role': random.choice(schema['role']['allowed']),
                'rows': cls.random_rows(random.randint(0, 5)),
                'alist': cls.random_list(random.randint(0, 5)),
                'location': {
                    'address': 'address ' + cls.random_string(5),
                    'city': 'city ' + cls.random_string(3),
                },
                'born': datetime.today() + timedelta(
                    days=random.randint(-10, 10)),

                'tid': ObjectId(),
                eve.LAST_UPDATED: dt,
                eve.DATE_CREATED: dt,

            }
            contacts.append(contact)
        return contacts

    @classmethod
    def random_payments(cls, num):
        payments = []
        for i in range(num):
            dt = datetime.now()
            payment = {
                'a_string':  cls.random_string(10),
                'a_number': i,
                eve.LAST_UPDATED: dt,
                eve.DATE_CREATED: dt,
            }
            payments.append(payment)
        return payments

    @classmethod
    def random_string(cls, num):
        return (''.join(random.choice(string.ascii_uppercase)
                        for x in range(num)))

    @classmethod
    def random_list(cls, num):
        alist = []
        for i in range(num):
            alist.append(['string' + str(i), random.randint(1000, 9999)])
        return alist

    @classmethod
    def random_rows(cls, num):
        schema = DOMAIN['contacts']['schema']['rows']['items']
        rows = []
        for i in range(num):
            rows.append(
                {
                    'sku': cls.random_string(schema['sku']['maxlength']),
                    'price': random.randint(100, 1000),
                }
            )
        return rows
        return rows
