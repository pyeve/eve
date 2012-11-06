# TODO test unallowed methods (PUT, but also PATCH for collections and so on)
from eve.tests import TestMethodsBase
import eve
from eve import STATUS_OK, LAST_UPDATED, ID_FIELD
from datetime import datetime, timedelta
from testsettings import MONGO_PASSWORD, MONGO_USERNAME, MONGO_DBNAME, DOMAIN
from flask.ext.pymongo import Connection
import string
import random


class TestGet(TestMethodsBase):

    def test_get_empty_resource(self):
        response, status = self.get(self.empty_resource)
        self.assert200(status)

        resource = response[self.empty_resource]
        self.assertEqual(len(resource), 0)

        links = response['links']
        self.assertEqual(len(links), 2)
        self.assertResourceLink(links, self.empty_resource)
        self.assertHomeLink(links)

    def test_get_max_results(self):
        maxr = 10
        response, status = self.get(self.known_resource,
                                    '?max_results=%d' % maxr)
        self.assert200(status)

        resource = response[self.known_resource]
        self.assertEqual(len(resource), maxr)

        maxr = self.app.config['PAGING_LIMIT'] + 1
        response, status = self.get(self.known_resource,
                                    '?max_results=%d' % maxr)
        self.assert200(status)
        resource = response[self.known_resource]
        self.assertEqual(len(resource), self.app.config['PAGING_LIMIT'])

    def test_get_page(self):
        response, status = self.get(self.known_resource)
        self.assert200(status)

        links = response['links']
        self.assertNextLink(links, 2)

        page = 1
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['links']
        self.assertNextLink(links, 2)

        page = 2
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['links']
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)

        page = 3
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['links']
        self.assertNextLink(links, 4)
        self.assertPrevLink(links, 2)

    def test_get_where_mongo_syntax(self):
        where = '{"ref": "%s"}' % self.item_name
        response, status = self.get(self.known_resource,
                                    '?where=%s' % where)
        self.assert200(status)

        resource = response[self.known_resource]
        self.assertEqual(len(resource), 1)

    def test_get_sort_mongo_syntax(self):
        sort = '[("prog",1)]'
        response, status = self.get(self.known_resource,
                                    '?sort=%s' % sort)
        self.assert200(status)

        resource = response[self.known_resource]
        self.assertEqual(len(resource), self.app.config['PAGING_DEFAULT'])
        # TODO testing all the resultset seems a excessive?
        for i in range(len(resource)):
            self.assertEqual(resource[i]['prog'], i)

    def test_get_if_modified_since(self):
        self.assertIfModifiedSince(self.known_resource_url)

    def test_cache_control(self):
        self.assertCacheControl(self.known_resource_url)

    def test_expires(self):
        self.assertExpires(self.known_resource_url)

    def test_get(self):
        response, status = self.get(self.known_resource)
        self.assert200(status)

        links = response['links']
        self.assertEqual(len(links), 3)
        self.assertHomeLink(links)
        self.assertResourceLink(links, self.known_resource)
        self.assertNextLink(links, 2)

        resource = response[self.known_resource]
        self.assertEqual(len(resource), self.app.config['PAGING_DEFAULT'])

        # TODO maybe limit the test to just the first item in the resultset?
        for item in resource:
            self.assertItem(item)

        etag = item.get('etag')
        self.assertTrue(etag is not None)
        # TODO figure a way to test etag match. Even removing the etag field
        # itself won't help since the 'item' dict is unordered (and therefore
        # doesn't match the original representation)
        #del(item['etag'])
        #self.assertEqual(hashlib.sha1(str(item)).hexdigest(), etag)


class TestGetItem(TestMethodsBase):

    def assertItemResponse(self, response, status):
        self.assert200(status)
        self.assertEqual(len(response), 2)

        links = response['links']
        self.assertEqual(len(links), 2)
        self.assertHomeLink(links)
        self.assertResourceLink(links, self.known_resource)

        item = response.get(self.known_resource)
        self.assertItem(item)

    def test_getitem_by_id(self):
        response, status = self.get(self.known_resource,
                                    item=self.item_id)
        self.assertItemResponse(response, status)

        response, status = self.get(self.known_resource,
                                    item=self.unknown_item_id)
        self.assert404(status)

    def test_getitem_by_name(self):
        response, status = self.get(self.known_resource,
                                    item=self.item_name)
        self.assertItemResponse(response, status)
        response, status = self.get(self.known_resource,
                                    item=self.unknown_item_name)
        self.assert404(status)

    def test_getitem_if_modified_since(self):
        self.assertIfModifiedSince(self.item_id_url)

    def test_getitem_if_none_match(self):
        r = self.test_client.get(self.item_id_url)

        etag = r.headers.get('ETag')
        self.assertTrue(etag is not None)
        r = self.test_client.get(self.item_id_url,
                                 headers=[('If-None-Match', etag)])
        self.assert304(r.status_code)
        self.assertEqual(r.data, '')

    def test_cache_control(self):
        self.assertCacheControl(self.item_id_url)

    def test_expires(self):
        self.assertExpires(self.item_id_url)


class TestPatch(TestMethodsBase):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.content_type = 'application/x-www-form-urlencoded'

    def test_bad_form_length(self):
        r, status = self.patch(self.item_id_url, data={})
        self.assert400(status)

        r, status = self.patch(self.item_id_url,
                               data={'key1': 'value1', 'key2': 'value2'})
        self.assert400(status)

    def test_unknown_id(self):
        r, status = self.patch(self.unknown_item_id_url,
                               data={'key1': 'value1'})
        self.assert404(status)

    def test_by_name(self):
        r, status = self.patch(self.item_name_url, data={'key1': 'value1'})
        self.assert405(status)

    def test_ifmatch_missing(self):
        r, status = self.patch(self.item_id_url, data={'key1': 'value1'})
        self.assert403(status)

    def test_ifmatch_bad_etag(self):
        r, status = self.patch(self.item_id_url,
                               data={'key1': 'value1'},
                               headers=[('If-Match', 'not-quite-right')])
        self.assert412(status)

    def test_bad_request(self):
        r, status = self.patch(self.item_id_url,
                               data={'key1': '{"ref"="hey, gonna bomb"}'},
                               headers=[('If-Match', self.item_etag)])
        self.assert400(status)

    def test_unique_value(self):
        # TODO
        # for the time being we are happy with testing only Eve's custom
        # validation. We rely on Cerberus' own test suite for other validation
        # unit tests. This test also makes sure that response status is
        # syntatically correcy in case of validation issues.
        # We should probably test every single case as well (seems overkill).
        r, status = self.patch(self.item_id_url,
                               data={'key1': '{"ref": "%s"}' % self.alt_ref},
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertValidationError(r, 'key1', ("field 'ref'", self.alt_ref,
                                               'not unique'))

    def test_patch_string(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {'key1': '{"%s": "%s"}' % (field, test_value)}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_integer(self):
        field = "prog"
        test_value = 9999
        changes = {'key1': '{"%s": %s}' % (field, test_value)}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_list_as_array(self):
        field = "role"
        test_value = ["vendor", "client"]
        changes = {'key1': '{"%s": %s}' % (field, test_value)}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertTrue(set(test_value).issubset(db_value))

    def test_patch_rows(self):
        field = "rows"
        test_value = [
            {'sku': 'AT1234', 'price': 99},
            {'sku': 'XF9876', 'price': 9999}
        ]
        changes = {'key1': '{"%s": %s}' % (field, test_value)}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)

        for test_item in test_value:
            self.assertTrue(test_item in db_value)

    def test_patch_list(self):
        field = "alist"
        test_value = ["a_string", 99]
        changes = {'key1': '{"%s": %s}' % (field, test_value)}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_dict(self):
        field = "location"
        test_value = {'address': 'an address', 'city': 'a city'}
        changes = {'key1': '{"%s": %s}' % (field, test_value)}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_datetime(self):
        field = "born"
        test_value = "Tue, 06 Nov 2012 10:33:31 UTC"
        changes = {'key1': '{"%s": "%s"}' % (field, test_value)}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def perform_patch(self, changes):
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertPatchResponse(r, 'key1', self.item_id)
        return r

    def compare_patch_with_get(self, field, patch_response):
        raw_r = self.test_client.get(self.item_id_url)
        r, status = self.parse_response(raw_r)
        self.assert200(status)
        self.assertEqual(raw_r.headers.get('ETag'),
                         patch_response['key1']['etag'])
        return r[self.known_resource][field]

    def assertPatchResponse(self, response, key, item_id):
        self.assertTrue(key in response)
        k = response[key]
        self.assertTrue('status' in k)
        self.assertTrue(STATUS_OK in k['status'])
        self.assertFalse('issues' in k)
        self.assertTrue(ID_FIELD in k)
        self.assertEqual(k[ID_FIELD], item_id)
        self.assertTrue(LAST_UPDATED in k)
        self.assertTrue('etag' in k)
        self.assertTrue('link') in k
        self.assertItemLink(k['link'], item_id)


def setUpModule():
    c = Connection()
    c.drop_database(MONGO_DBNAME)
    c[MONGO_DBNAME].add_user(MONGO_USERNAME, MONGO_PASSWORD)
    bulk_insert(c)
    c.close()


def tearDownModule():
    c = Connection()
    c.drop_database(MONGO_DBNAME)
    c.close()


def bulk_insert(c):
    db = c[MONGO_DBNAME]
    collection = db.contacts
    collection.insert(random_contacts(100))


def random_contacts(num):
    schema = DOMAIN['contacts']['schema']
    contacts = []
    for i in range(num):
        dt = datetime.now()
        contact = {
            'ref':  random_string(schema['ref']['maxlength']),
            'prog': i,
            'role': random.choice(schema['role']['allowed']),
            'rows': random_rows(random.randint(0, 5)),
            'alist': random_list(random.randint(0, 5)),
            'location': {
                'address': 'address ' + random_string(5),
                'city': 'city ' + random_string(3),
            },
            'born': datetime.today() + timedelta(
                days=random.randint(-10, 10)),

            eve.LAST_UPDATED: dt,
            eve.DATE_CREATED: dt,

        }
        contacts.append(contact)
    return contacts


def random_string(num):
    return (''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(num)))


def random_list(num):
    alist = []
    for i in range(num):
        alist.append(['string' + str(i), random.randint(1000, 9999)])
    return alist


def random_rows(num):
    schema = DOMAIN['contacts']['schema']['rows']['items']
    rows = []
    for i in range(num):
        rows.append(
            {
                'sku': random_string(schema['sku']['maxlength']),
                'price': random.randint(100, 1000),
            }
        )
    return rows
