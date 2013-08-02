#import unittest
from eve.tests import TestBase
from eve import STATUS_OK, LAST_UPDATED, ID_FIELD
import simplejson as json


#@unittest.skip("don't need no freakin' tests!")
class TestPatch(TestBase):

    def test_patch_to_resource_endpoint(self):
        r, status = self.patch(self.known_resource_url, data={})
        self.assert405(status)

    def test_readonly_resource(self):
        r, status = self.patch(self.readonly_id_url, data={})
        self.assert405(status)

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

    def test_unknown_id_different_resource(self):
        # patching a 'user' with a valid 'contact' id will 404
        r, status = self.patch('%s/%s/' % (self.different_resource,
                                           self.item_id),
                               data={'key1': 'value1'})
        self.assert404(status)

        # of course we can still patch a 'user'
        r, status = self.patch('%s/%s/' % (self.different_resource,
                                           self.user_id),
                               data={'key1': '{"username": "username1"}'},
                               headers=[('If-Match', self.user_etag)])
        self.assert200(status)

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
        changes = {'key1': json.dumps({field: test_value})}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_integer(self):
        field = "prog"
        test_value = 9999
        changes = {'key1': json.dumps({field: test_value})}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_list_as_array(self):
        field = "role"
        test_value = ["vendor", "client"]
        changes = {'key1': json.dumps({field: test_value})}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertTrue(set(test_value).issubset(db_value))

    def test_patch_rows(self):
        field = "rows"
        test_value = [
            {'sku': 'AT1234', 'price': 99},
            {'sku': 'XF9876', 'price': 9999}
        ]
        changes = {'key1': json.dumps({field: test_value})}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)

        for test_item in test_value:
            self.assertTrue(test_item in db_value)

    def test_patch_list(self):
        field = "alist"
        test_value = ["a_string", 99]
        changes = {'key1': json.dumps({field: test_value})}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_dict(self):
        field = "location"
        test_value = {'address': 'an address', 'city': 'a city'}
        changes = {'key1': json.dumps({field: test_value})}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_datetime(self):
        field = "born"
        test_value = "Tue, 06 Nov 2012 10:33:31 UTC"
        changes = {'key1': json.dumps({field: test_value})}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_objectid(self):
        field = "tid"
        test_value = "4f71c129c88e2018d4000000"
        changes = {'key1': json.dumps({field: test_value})}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_defaults(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {'key1': json.dumps({field: test_value})}
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
        changes = {'key1': json.dumps({"ref": test_values[0],
                                       "prog": test_values[1],
                                       "role": test_values[2]})}
        r = self.perform_patch(changes)
        db_values = self.compare_patch_with_get(fields, r)
        for i in range(len(db_values)):
            self.assertEqual(db_values[i], test_values[i])

    def test_patch_with_post_override(self):
        r = self.perform_patch_with_post_override('prog', 1)
        self.assert200(r.status_code)

    def perform_patch(self, changes):
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertPatchResponse(r, 'key1', self.item_id)
        return r

    def perform_patch_with_post_override(self, field, value):
        headers = [('X-HTTP-Method-Override', 'True'),
                   ('If-Match', self.item_etag),
                   ('Content-Type', 'application/x-www-form-urlencoded')]
        return self.test_client.post(self.item_id_url,
                                     data={'key1': json.dumps({field: value})},
                                     headers=headers)

    def compare_patch_with_get(self, fields, patch_response):
        raw_r = self.test_client.get(self.item_id_url)
        r, status = self.parse_response(raw_r)
        self.assert200(status)
        self.assertEqual(raw_r.headers.get('ETag'),
                         patch_response['key1']['etag'])
        if isinstance(fields, str):
            return r[fields]
        else:
            return [r[field] for field in fields]

    def test_patch_allow_unknown(self):
        changes = {'key1': json.dumps({"unknown": "unknown"})}
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertValidationError(r, 'key1', 'unknown field')
        self.app.config['DOMAIN'][self.known_resource]['allow_unknown'] = True
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertPatchResponse(r, 'key1', self.item_id)

    def test_patch_json(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = json.dumps({'key1': {field: test_value}})
        headers = [('If-Match', self.item_etag),
                   ('Content-Type', 'application/json')]
        r, status = self.parse_response(self.test_client.patch(
            self.item_id_url, data=changes, headers=headers))
        self.assert200(status)
        self.assertTrue('OK' in r['key1']['status'])

    def test_patch_referential_integrity(self):
        data = {'item1': json.dumps({"person": self.unknown_item_id})}
        headers = [('If-Match', self.invoice_etag)]
        r, status = self.patch(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        expected = ("value '%s' for field '%s' must exist in collection "
                    "collection '%s', field '%s'" %
                    (self.unknown_item_id, 'person', 'contacts',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, 'item1', expected)

        data = {'item1': json.dumps({"person": self.item_id})}
        r, status = self.patch(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        self.assertPatchResponse(r, 'item1', self.invoice_id)

    def test_patch_list_referential_integrity(self):
        # Patch the tags list with two tags
        test_values = [self.tag_id1, self.tag_id1]
        data = {'key1': json.dumps({"tags": test_values})}
        headers = [('If-Match', self.user_etag)]
        r, status = self.patch(self.user_id_url, data=data, headers=headers)
        self.assert200(status)
        self.assertTrue('OK' in r['key1']['status'],
                        msg="key1: %s" % r['key1'])
        r1, status1 = self.get(self.different_resource, item=self.user_id)
        self.assertEqual(test_values, r1['tags'])

    def test_patch_write_concern_success(self):
        # 0 and 1 are the only valid values for 'w' on our mongod instance (1
        # is the default)
        self.domain['contacts']['mongo_write_concern'] = {'w': 0}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {'key1': json.dumps({field: test_value})}
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert200(status)

    def test_patch_write_concern_fail(self):
        # should get a 500 since there's no replicaset on the mongod instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 2}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {'key1': json.dumps({field: test_value})}
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assert500(status)

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
        self.assertTrue('_links') in k
        self.assertItemLink(k['_links'], item_id)

    def patch(self, url, data, headers=[]):
        headers.append(('Content-Type', 'application/x-www-form-urlencoded'))
        r = self.test_client.patch(url,
                                   data=data,
                                   headers=headers)
        return self.parse_response(r)
