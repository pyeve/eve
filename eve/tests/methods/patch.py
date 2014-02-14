#import unittest
from eve.tests import TestBase
from eve.tests.test_settings import MONGO_DBNAME
from eve import STATUS_OK, LAST_UPDATED, ID_FIELD, ISSUES, STATUS, ETAG
from bson import ObjectId
import simplejson as json


#@unittest.skip("don't need no freakin' tests!")
class TestPatch(TestBase):

    def test_patch_to_resource_endpoint(self):
        _, status = self.patch(self.known_resource_url, data={})
        self.assert405(status)

    def test_readonly_resource(self):
        _, status = self.patch(self.readonly_id_url, data={})
        self.assert405(status)

    def test_unknown_id(self):
        _, status = self.patch(self.unknown_item_id_url,
                               data={"key1": 'value1'})
        self.assert404(status)

    def test_unknown_id_different_resource(self):
        # patching a 'user' with a valid 'contact' id will 404
        _, status = self.patch('%s/%s/' % (self.different_resource,
                                           self.item_id),
                               data={"key1": "value1"})
        self.assert404(status)

        # of course we can still patch a 'user'
        _, status = self.patch('%s/%s/' % (self.different_resource,
                                           self.user_id),
                               data={'key1': '{"username": "username1"}'},
                               headers=[('If-Match', self.user_etag)])
        self.assert200(status)

    def test_by_name(self):
        _, status = self.patch(self.item_name_url, data={'key1': 'value1'})
        self.assert405(status)

    def test_ifmatch_missing(self):
        _, status = self.patch(self.item_id_url, data={'key1': 'value1'})
        self.assert403(status)

    def test_ifmatch_disabled(self):
        self.app.config['IF_MATCH'] = False
        r, status = self.patch(self.item_id_url, data={'key1': 'value1'})
        self.assert200(status)
        self.assertTrue(ETAG not in r)

    def test_ifmatch_bad_etag(self):
        _, status = self.patch(self.item_id_url,
                               data={'key1': 'value1'},
                               headers=[('If-Match', 'not-quite-right')])
        self.assert412(status)

    def test_unique_value(self):
        # TODO
        # for the time being we are happy with testing only Eve's custom
        # validation. We rely on Cerberus' own test suite for other validation
        # unit tests. This test also makes sure that response status is
        # syntatically correcy in case of validation issues.
        # We should probably test every single case as well (seems overkill).
        r, status = self.patch(self.item_id_url,
                               data={"ref": "%s" % self.alt_ref},
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertValidationError(r, {'ref': "value '%s' is not unique" %
                                       self.alt_ref})

    def test_patch_string(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_integer(self):
        field = "prog"
        test_value = 9999
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_list_as_array(self):
        field = "role"
        test_value = ["vendor", "client"]
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertTrue(set(test_value).issubset(db_value))

    def test_patch_rows(self):
        field = "rows"
        test_value = [
            {'sku': 'AT1234', 'price': 99},
            {'sku': 'XF9876', 'price': 9999}
        ]
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)

        for test_item in test_value:
            self.assertTrue(test_item in db_value)

    def test_patch_list(self):
        field = "alist"
        test_value = ["a_string", 99]
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_dict(self):
        field = "location"
        test_value = {'address': 'an address', 'city': 'a city'}
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_datetime(self):
        field = "born"
        test_value = "Tue, 06 Nov 2012 10:33:31 GMT"
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_objectid(self):
        field = "tid"
        test_value = "4f71c129c88e2018d4000000"
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_defaults(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {field: test_value}
        r = self.perform_patch(changes)
        self.assertRaises(KeyError, self.compare_patch_with_get, 'title', r)

    def test_patch_defaults_with_post_override(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        r = self.perform_patch_with_post_override(field, test_value)
        self.assert200(r.status_code)
        self.assertRaises(KeyError, self.compare_patch_with_get, 'title',
                          json.loads(r.get_data()))

    def test_patch_multiple_fields(self):
        fields = ['ref', 'prog', 'role']
        test_values = ["9876543210987654321054321", 123, ["agent"]]
        changes = {"ref": test_values[0], "prog": test_values[1],
                   "role": test_values[2]}
        r = self.perform_patch(changes)
        db_values = self.compare_patch_with_get(fields, r)
        for i in range(len(db_values)):
            self.assertEqual(db_values[i], test_values[i])

    def test_patch_with_post_override(self):
        # a POST request with PATCH override turns into a PATCH request
        r = self.perform_patch_with_post_override('prog', 1)
        self.assert200(r.status_code)

    def perform_patch(self, changes):
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertPatchResponse(r, self.item_id)
        return r

    def perform_patch_with_post_override(self, field, value):
        headers = [('X-HTTP-Method-Override', 'PATCH'),
                   ('If-Match', self.item_etag),
                   ('Content-Type', 'application/json')]
        return self.test_client.post(self.item_id_url,
                                     data=json.dumps({field: value}),
                                     headers=headers)

    def compare_patch_with_get(self, fields, patch_response):
        raw_r = self.test_client.get(self.item_id_url)
        r, status = self.parse_response(raw_r)
        self.assert200(status)
        self.assertEqual(raw_r.headers.get('ETag'),
                         patch_response[ETAG])
        if isinstance(fields, str):
            return r[fields]
        else:
            return [r[field] for field in fields]

    def test_patch_allow_unknown(self):
        changes = {"unknown": "unknown"}
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertValidationError(r, {'unknown': 'unknown field'})
        self.app.config['DOMAIN'][self.known_resource]['allow_unknown'] = True
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertPatchResponse(r, self.item_id)

    def test_patch_x_www_form_urlencoded(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {field: test_value}
        headers = [('If-Match', self.item_etag)]
        r, status = self.parse_response(self.test_client.patch(
            self.item_id_url, data=changes, headers=headers))
        self.assert200(status)
        self.assertTrue('OK' in r[STATUS])

    def test_patch_referential_integrity(self):
        data = {"person": self.unknown_item_id}
        headers = [('If-Match', self.invoice_etag)]
        r, status = self.patch(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        expected = ("value '%s' must exist in resource '%s', field '%s'" %
                    (self.unknown_item_id, 'contacts',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, {'person': expected})

        data = {"person": self.item_id}
        r, status = self.patch(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        self.assertPatchResponse(r, self.invoice_id)

    def test_patch_write_concern_success(self):
        # 0 and 1 are the only valid values for 'w' on our mongod instance (1
        # is the default)
        self.domain['contacts']['mongo_write_concern'] = {'w': 0}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {field: test_value}
        _, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)

    def test_patch_write_concern_fail(self):
        # should get a 500 since there's no replicaset on the mongod instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 2}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {field: test_value}
        _, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert500(status)

    def test_patch_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        # directly insert a document, without DATE_CREATED e LAST_UPDATED
        # values.
        contacts = self.random_contacts(1, False)
        ref = 'test_update_field'
        contacts[0]['ref'] = ref
        _db = self.connection[MONGO_DBNAME]
        _db.contacts.insert(contacts)

        # now retrieve same document via API and get its etag, which is
        # supposed to be computed on default DATE_CREATED and LAST_UPDATAED
        # values.
        response, status = self.get(self.known_resource, item=ref)
        etag = response[ETAG]
        _id = response['_id']

        # attempt a PATCH with the new etag.
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {field: test_value}
        _, status = self.patch('%s/%s' % (self.known_resource_url, _id),
                               data=changes, headers=[('If-Match', etag)])
        self.assert200(status)

    def test_patch_subresource(self):
        _db = self.connection[MONGO_DBNAME]

        # create random contact
        fake_contact = self.random_contacts(1)
        fake_contact_id = _db.contacts.insert(fake_contact)[0]

        # update first invoice to reference the new contact
        _db.invoices.update({'_id': ObjectId(self.invoice_id)},
                            {'$set': {'person': fake_contact_id}})

        # GET all invoices by new contact
        response, status = self.get('users/%s/invoices/%s' %
                                    (fake_contact_id, self.invoice_id))
        etag = response[ETAG]

        data = {"inv_number": "new_number"}
        headers = [('If-Match', etag)]
        response, status = self.patch('users/%s/invoices/%s' %
                                      (fake_contact_id, self.invoice_id),
                                      data=data, headers=headers)
        self.assert200(status)
        self.assertPatchResponse(response, self.invoice_id)

    def assertPatchResponse(self, response, item_id):
        self.assertTrue(STATUS in response)
        self.assertTrue(STATUS_OK in response[STATUS])
        self.assertFalse(ISSUES in response)
        self.assertTrue(ID_FIELD in response)
        self.assertEqual(response[ID_FIELD], item_id)
        self.assertTrue(LAST_UPDATED in response)
        self.assertTrue(ETAG in response)
        self.assertTrue('_links' in response)
        self.assertItemLink(response['_links'], item_id)

    def patch(self, url, data, headers=[]):
        headers.append(('Content-Type', 'application/json'))
        r = self.test_client.patch(url,
                                   data=json.dumps(data),
                                   headers=headers)
        return self.parse_response(r)
