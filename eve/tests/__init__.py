# -*- coding: utf-8 -*-

import unittest
import eve
import string
import random
import os
import simplejson as json
from datetime import datetime, timedelta
from flask_pymongo import MongoClient
from bson import ObjectId
from eve.tests.test_settings import MONGO_PASSWORD, MONGO_USERNAME, \
    MONGO_DBNAME, DOMAIN, MONGO_HOST, MONGO_PORT
from eve import ISSUES, ETAG
from eve.utils import date_to_str
try:
    from urlparse import parse_qs, urlparse
except ImportError:
    from urllib.parse import parse_qs, urlparse


class ValueStack(object):
    """
    Descriptor to store multiple assignments in an attribute.

    Due to the multiple self.app = assignments in tests, it is difficult to
    keep track by hand of the applications created in order to close their
    database connections. This descriptor helps with it.
    """
    def __init__(self, on_delete):
        """
        :param on_delete: Action to execute when the attribute is deleted
        """
        self.elements = []
        self.on_delete = on_delete

    def __set__(self, obj, val):
        self.elements.append(val)

    def __get__(self, obj, objtype):
        return self.elements[-1] if self.elements else None

    def __delete__(self, obj):
        for item in self.elements:
            self.on_delete(item)
        self.elements = []


def close_pymongo_connection(app):
    """
    Close the pymongo connection in an eve/flask app
    """
    if 'pymongo' not in app.extensions:
        return
    del app.extensions['pymongo']
    del app.media


class TestMinimal(unittest.TestCase):
    """ Start the building of the tests for an application
    based on Eve by subclassing this class and provide proper settings
    using :func:`setUp()`
    """
    app = ValueStack(close_pymongo_connection)

    def setUp(self, settings_file=None, url_converters=None):
        """ Prepare the test fixture

        :param settings_file: the name of the settings file.  Defaults
                              to `eve/tests/test_settings.py`.
        """
        self.this_directory = os.path.dirname(os.path.realpath(__file__))
        if settings_file is None:
            # Load the settings file, using a robust path
            settings_file = os.path.join(self.this_directory,
                                         'test_settings.py')

        self.connection = None
        self.known_resource_count = 101
        self.setupDB()

        self.settings_file = settings_file
        self.app = eve.Eve(settings=self.settings_file,
                           url_converters=url_converters)

        self.test_client = self.app.test_client()

        self.domain = self.app.config['DOMAIN']

    def tearDown(self):
        del self.app
        self.dropDB()

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert201(self, status):
        self.assertEqual(status, 201)

    def assert204(self, status):
        self.assertEqual(status, 204)

    def assert301(self, status):
        self.assertEqual(status, 301)

    def assert304(self, status):
        self.assertEqual(status, 304)

    def assert404(self, status):
        self.assertEqual(status, 404)

    def assert422(self, status):
        self.assertEqual(status, 422)

    def get(self, resource, query='', item=None):
        if resource in self.domain:
            resource = self.domain[resource]['url']
        if item:
            request = '/%s/%s%s' % (resource, item, query)
        else:
            request = '/%s%s' % (resource, query)

        r = self.test_client.get(request)
        return self.parse_response(r)

    def post(self, url, data, headers=None, content_type='application/json'):
        if headers is None:
            headers = []
        headers.append(('Content-Type', content_type))
        r = self.test_client.post(url, data=json.dumps(data), headers=headers)
        return self.parse_response(r)

    def put(self, url, data, headers=None):
        if headers is None:
            headers = []
        headers.append(('Content-Type', 'application/json'))
        r = self.test_client.put(url, data=json.dumps(data), headers=headers)
        return self.parse_response(r)

    def patch(self, url, data, headers=None):
        if headers is None:
            headers = []
        headers.append(('Content-Type', 'application/json'))
        r = self.test_client.patch(url, data=json.dumps(data), headers=headers)
        return self.parse_response(r)

    def delete(self, url, headers=None):
        r = self.test_client.delete(url, headers=headers)
        return self.parse_response(r)

    def parse_response(self, r):
        try:
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def assertValidationErrorStatus(self, status):
        self.assertEqual(status,
                         self.app.config.get('VALIDATION_ERROR_STATUS'))

    def assertValidationError(self, response, matches):
        self.assertTrue(eve.STATUS in response)
        self.assertTrue(eve.STATUS_ERR in response[eve.STATUS])
        self.assertTrue(ISSUES in response)
        issues = response[ISSUES]
        self.assertTrue(len(issues))

        for k, v in matches.items():
            self.assertTrue(k in issues)
            self.assertTrue(v in issues[k])

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
        self.assertTrue(not r.get_data())

    def assertItem(self, item, resource):
        self.assertEqual(type(item), dict)

        updated_on = item.get(self.app.config['LAST_UPDATED'])
        self.assertTrue(updated_on is not None)
        try:
            datetime.strptime(updated_on, self.app.config['DATE_FORMAT'])
        except Exception as e:
            self.fail('Cannot convert field "%s" to datetime: %s' %
                      (self.app.config['LAST_UPDATED'], e))

        created_on = item.get(self.app.config['DATE_CREATED'])
        self.assertTrue(updated_on is not None)
        try:
            datetime.strptime(created_on, self.app.config['DATE_FORMAT'])
        except Exception as e:
            self.fail('Cannot convert field "%s" to datetime: %s' %
                      (self.app.config['DATE_CREATED'], e))

        link = item.get('_links')
        _id = item.get(self.domain[resource]['id_field'])
        self.assertItemLink(link, _id)

    def assertPagination(self, response, page, total, max_results):
        p_key, mr_key = self.app.config['QUERY_PAGE'], \
            self.app.config['QUERY_MAX_RESULTS']
        self.assertTrue(self.app.config['META'] in response)
        meta = response.get(self.app.config['META'])
        self.assertTrue(p_key in meta)
        self.assertTrue(mr_key in meta)
        self.assertTrue('total' in meta)
        self.assertEqual(meta[p_key], page)
        self.assertEqual(meta[mr_key], max_results)
        self.assertEqual(meta['total'], total)

    def assertHomeLink(self, links):
        self.assertTrue('parent' in links)
        link = links['parent']
        self.assertTrue('title' in link)
        self.assertTrue('href' in link)
        self.assertEqual('home', link['title'])
        self.assertEqual("/", link['href'])

    def assertResourceLink(self, links, resource):
        self.assertTrue('self' in links)
        link = links['self']
        self.assertTrue('title' in link)
        self.assertTrue('href' in link)
        url = self.domain[resource]['url']
        self.assertEqual(url, link['title'])
        self.assertEqual("%s" % url, link['href'])

    def assertCollectionLink(self, links, resource):
        self.assertTrue('collection' in links)
        link = links['collection']
        self.assertTrue('title' in link)
        self.assertTrue('href' in link)
        url = self.domain[resource]['url']
        self.assertEqual(url, link['title'])
        self.assertEqual("%s" % url, link['href'])

    def assertNextLink(self, links, page):
        self.assertTrue('next' in links)
        link = links['next']
        self.assertTrue('title' in link)
        self.assertTrue('href' in link)
        self.assertEqual('next page', link['title'])
        self.assertTrue("%s=%d" % (self.app.config['QUERY_PAGE'], page)
                        in link['href'])

    def assertPrevLink(self, links, page):
        self.assertTrue('prev' in links)
        link = links['prev']
        self.assertTrue('title' in link)
        self.assertTrue('href' in link)
        self.assertEqual('previous page', link['title'])
        if page > 1:
            self.assertTrue("%s=%d" % (self.app.config['QUERY_PAGE'], page)
                            in link['href'])

    def assertItemLink(self, links, item_id):
        self.assertTrue('self' in links)
        link = links['self']
        # TODO we are too deep here to get a hold of the due title. Should fix.
        self.assertTrue('title' in link)
        self.assertTrue('href' in link)
        self.assertTrue('/%s' % item_id in link['href'])

    def assertLastLink(self, links, page):
        if page:
            self.assertTrue('last' in links)
            link = links['last']
            self.assertTrue('title' in link)
            self.assertTrue('href' in link)
            self.assertEqual('last page', link['title'])
            self.assertTrue("%s=%d" % (self.app.config['QUERY_PAGE'], page)
                            in link['href'])
        else:
            self.assertTrue('last' not in links)

    def assertCustomParams(self, link, params):
        self.assertTrue('href' in link)
        url_params = parse_qs(urlparse(link['href']).query)
        for param, values in params.lists():
            self.assertTrue(param in url_params)
            for value in values:
                self.assertTrue(value in url_params[param])

    def assert400(self, status):
        self.assertEqual(status, 400)

    def assert401(self, status):
        self.assertEqual(status, 401)

    def assert401or405(self, status):
        self.assertTrue(status == 401 or 405)

    def assert403(self, status):
        self.assertEqual(status, 403)

    def assert405(self, status):
        self.assertEqual(status, 405)

    def assert412(self, status):
        self.assertEqual(status, 412)

    def assert428(self, status):
        self.assertEqual(status, 428)

    def assert500(self, status):
        self.assertEqual(status, 500)

    def setupDB(self):
        self.connection = MongoClient(MONGO_HOST, MONGO_PORT)
        self.connection.drop_database(MONGO_DBNAME)
        if MONGO_USERNAME:
            self.connection[MONGO_DBNAME].add_user(MONGO_USERNAME,
                                                   MONGO_PASSWORD)
        self.bulk_insert()

    def bulk_insert(self):
        pass

    def dropDB(self):
        self.connection = MongoClient(MONGO_HOST, MONGO_PORT)
        self.connection.drop_database(MONGO_DBNAME)
        self.connection.close()


class TestBase(TestMinimal):

    def setUp(self, url_converters=None):
        super(TestBase, self).setUp(url_converters=url_converters)

        self.disabled_bulk = 'disabled_bulk'
        self.disabled_bulk_url = ('/%s' %
                                  self.domain[self.disabled_bulk]['url'])

        self.known_resource = 'contacts'
        self.known_resource_url = ('/%s' %
                                   self.domain[self.known_resource]['url'])
        self.empty_resource = 'empty'
        self.empty_resource_url = '/%s' % self.empty_resource

        self.unknown_resource = 'unknown'
        self.unknown_resource_url = '/%s' % self.unknown_resource
        self.unknown_item_id = '4f46445fc88e201858000000'
        self.unknown_item_name = 'unknown'

        self.unknown_item_id_url = ('/%s/%s' %
                                    (self.domain[self.known_resource]['url'],
                                     self.unknown_item_id))
        self.unknown_item_name_url = ('/%s/%s' %
                                      (self.domain[self.known_resource]['url'],
                                       self.unknown_item_name))

        self.readonly_resource = 'payments'
        self.readonly_resource_url = (
            '/%s' % self.domain[self.readonly_resource]['url'])

        self.different_resource = 'users'
        self.different_resource_url = ('/%s' %
                                       self.domain[
                                           self.different_resource]['url'])

        response, _ = self.get('contacts', '?max_results=2')
        contact = self.response_item(response)
        self.item = contact
        self.item_id = contact[self.domain['contacts']['id_field']]
        self.item_name = contact['ref']
        self.item_tid = contact['tid']
        self.item_etag = contact[ETAG]
        self.item_ref = contact['ref']
        self.item_id_url = ('/%s/%s' %
                            (self.domain[self.known_resource]['url'],
                             self.item_id))
        self.item_name_url = ('/%s/%s' %
                              (self.domain[self.known_resource]['url'],
                               self.item_name))
        self.alt_ref = self.response_item(response, 1)['ref']

        response, _ = self.get('payments', '?max_results=1')
        self.readonly_id = self.response_item(response)['_id']
        self.readonly_id_url = ('%s/%s' % (self.readonly_resource_url,
                                           self.readonly_id))

        response, _ = self.get('users')
        user = self.response_item(response)
        self.user_id = user[self.domain['users']['id_field']]
        self.user_username = user['username']
        self.user_name = user['ref']
        self.user_etag = user[ETAG]
        self.user_id_url = ('/%s/%s' %
                            (self.domain[self.different_resource]['url'],
                             self.user_id))
        self.user_username_url = (
            '/%s/%s' % (self.domain[self.different_resource]['url'],
                        self.user_username)
        )

        response, _ = self.get('invoices')
        invoice = self.response_item(response)
        self.invoice_id = invoice[self.domain['invoices']['id_field']]
        self.invoice_etag = invoice[ETAG]
        self.invoice_id_url = ('/%s/%s' %
                               (self.domain['invoices']['url'],
                                self.invoice_id))

        self.epoch = date_to_str(datetime(1970, 1, 1))

    def response_item(self, response, i=0):
        if self.app.config['HATEOAS']:
            return response['_items'][i]
        else:
            return response[i]

    def random_contacts(self, num, standard_date_fields=True):
        schema = DOMAIN['contacts']['schema']
        contacts = []
        for i in range(num):
            dt = datetime.utcnow().replace(microsecond=0)
            contact = {
                'ref': self.random_string(schema['ref']['maxlength']),
                'prog': i,
                'role': random.choice(schema['role']['allowed']),
                'rows': self.random_rows(random.randint(0, 5)),
                'alist': self.random_list(random.randint(0, 5)),
                'location': {
                    'address': 'address ' + self.random_string(5),
                    'city': 'city ' + self.random_string(3),
                },
                'born': datetime.today() + timedelta(
                    days=random.randint(-10, 10)),

                'tid': ObjectId(),
                'read_only_field': schema['read_only_field']['default']
            }
            if standard_date_fields:
                contact[eve.LAST_UPDATED] = dt
                contact[eve.DATE_CREATED] = dt

            contacts.append(contact)
        return contacts

    def random_users(self, num):
        users = self.random_contacts(num)
        for user in users:
            user['username'] = self.random_string(10)
        return users

    def random_payments(self, num):
        payments = []
        for i in range(num):
            dt = datetime.utcnow().replace(microsecond=0)
            payment = {
                'a_string': self.random_string(10),
                'a_number': i,
                eve.LAST_UPDATED: dt,
                eve.DATE_CREATED: dt,
            }
            payments.append(payment)
        return payments

    def random_invoices(self, num):
        invoices = []
        for _ in range(num):
            dt = datetime.utcnow().replace(microsecond=0)
            invoice = {
                'inv_number': self.random_string(10),
                eve.LAST_UPDATED: dt,
                eve.DATE_CREATED: dt,
            }
            invoices.append(invoice)
        return invoices

    def random_products(self, num):
        schema = DOMAIN['products']['schema']
        products = []
        for _ in range(num):
            products.append(
                {
                    'sku': self.random_string(schema['sku']['maxlength']),
                    'title': ("Hypercube " + self.random_string(2) +
                              str(random.randint(100, 1000)))
                }
            )
        return products

    def random_string(self, num):
        return (''.join(random.choice(string.ascii_uppercase)
                        for x in range(num)))

    def random_list(self, num):
        alist = []
        for i in range(num):
            alist.append(['string' + str(i), random.randint(1000, 9999)])
        return alist

    def random_rows(self, num):
        schema = DOMAIN['contacts']['schema']['rows']['schema']['schema']
        rows = []
        for _ in range(num):
            rows.append(
                {
                    'sku': self.random_string(schema['sku']['maxlength']),
                    'price': random.randint(100, 1000),
                }
            )
        return rows

    def random_internal_transactions(self, num):
        transactions = []
        for i in range(num):
            dt = datetime.utcnow().replace(microsecond=0)
            transaction = {
                'internal_string': self.random_string(10),
                'internal_number': i,
                eve.LAST_UPDATED: dt,
                eve.DATE_CREATED: dt,
            }
            transactions.append(transaction)
        return transactions

    def bulk_insert(self):
        _db = self.connection[MONGO_DBNAME]
        _db.contacts.insert(self.random_contacts(self.known_resource_count))
        _db.contacts.insert(self.random_users(2))
        _db.payments.insert(self.random_payments(10))
        _db.invoices.insert(self.random_invoices(1))
        _db.internal_transactions.insert(self.random_internal_transactions(4))
        _db.products.insert(self.random_products(2))
        self.connection.close()
