import simplejson as json
from eve.tests import TestBase
from eve import STATUS_OK, LAST_UPDATED, ID_FIELD


class TestPut(TestBase):
    # TODO consider making a base codebase out of 'patch' and 'put' tests
    def test_put_to_resource_endpoint(self):
        r, status = self.put(self.known_resource_url, data={})
        self.assert405(status)

    def test_readonly_resource(self):
        r, status = self.put(self.readonly_id_url, data={})
        self.assert405(status)

    def test_bad_form_length(self):
        r, status = self.put(self.item_id_url, data={})
        self.assert400(status)

        r, status = self.put(self.item_id_url,
                             data={'key1': 'value1', 'key2': 'value2'})
        self.assert400(status)

    def test_unknown_id(self):
        r, status = self.put(self.unknown_item_id_url,
                             data={'key1': 'value1'})
        self.assert404(status)

    def test_unknown_id_different_resource(self):
        # replacing a 'user' with a valid 'contact' id will 404
        r, status = self.put('%s/%s/' % (self.different_resource,
                                         self.item_id),
                             data={'key1': 'value1'})
        self.assert404(status)

        # of course we can still put a 'user'
        r, status = self.put('%s/%s/' % (self.different_resource,
                                         self.user_id),
                             data={'key1': '{"username": "username1"}'},
                             headers=[('If-Match', self.user_etag)])
        self.assert200(status)

    def test_by_name(self):
        r, status = self.put(self.item_name_url, data={'key1': 'value1'})
        self.assert405(status)

    def test_ifmatch_missing(self):
        r, status = self.put(self.item_id_url, data={'key1': 'value1'})
        self.assert403(status)

    def test_ifmatch_bad_etag(self):
        r, status = self.put(self.item_id_url,
                             data={'key1': 'value1'},
                             headers=[('If-Match', 'not-quite-right')])
        self.assert412(status)

    def test_bad_request(self):
        r, status = self.put(self.item_id_url,
                             data={'key1': '{"ref"="hey, gonna bomb"}'},
                             headers=[('If-Match', self.item_etag)])
        self.assert400(status)

    def test_unique_value(self):
        r, status = self.put(self.item_id_url,
                             data={'key1': '{"ref": "%s"}' % self.alt_ref},
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertValidationError(r, 'key1', ("field 'ref'", self.alt_ref,
                                               'not unique'))

    def test_allow_unknown(self):
        changes = {'key1': json.dumps({"unknown": "unknown"})}
        r, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertValidationError(r, 'key1', 'unknown field')
        self.app.config['DOMAIN'][self.known_resource]['allow_unknown'] = True
        changes = {'key1': json.dumps({"unknown": "unknown",
                                       "ref": "1234567890123456789012345"})}
        r, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertPutResponse(r, 'key1', self.item_id)

    def test_put_json(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = json.dumps({'key1': {field: test_value}})
        headers = [('If-Match', self.item_etag),
                   ('Content-Type', 'application/json')]
        r, status = self.parse_response(self.test_client.put(
            self.item_id_url, data=changes, headers=headers))
        self.assert200(status)
        self.assertTrue('OK' in r['key1']['status'])

    def test_put_referential_integrity(self):
        data = {'item1': json.dumps({"person": self.unknown_item_id})}
        headers = [('If-Match', self.invoice_etag)]
        r, status = self.put(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        expected = ("value '%s' for field '%s' must exist in collection "
                    "collection '%s', field '%s'" %
                    (self.unknown_item_id, 'person', 'contacts',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, 'item1', expected)

        data = {'item1': json.dumps({"person": self.item_id})}
        r, status = self.put(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        self.assertPutResponse(r, 'item1', self.invoice_id)

    def test_put_write_concern_success(self):
        # 0 and 1 are the only valid values for 'w' on our mongod instance (1
        # is the default)
        self.domain['contacts']['mongo_write_concern'] = {'w': 0}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {'key1': json.dumps({field: test_value})}
        r, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)

    def test_put_write_concern_fail(self):
        # should get a 500 since there's no replicaset on the mongod instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 2}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {'key1': json.dumps({field: test_value})}
        r, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert500(status)

    def test_put_string(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {'key1': json.dumps({field: test_value})}
        r = self.perform_put(changes)
        db_value = self.compare_put_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_put_with_post_override(self):
        # POST request with PUT override turns into a PUT
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {'key1': json.dumps({field: test_value})}
        headers = [('X-HTTP-Method-Override', 'PUT'),
                   ('If-Match', self.item_etag),
                   ('Content-Type', 'application/x-www-form-urlencoded')]
        r = self.test_client.post(self.item_id_url, data=changes,
                                  headers=headers)
        self.assert200(r.status_code)
        self.assertPutResponse(json.loads(r.get_data()), 'key1', self.item_id)

    def perform_put(self, changes):
        r, status = self.put(self.item_id_url,
                             data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertPutResponse(r, 'key1', self.item_id)
        return r

    def assertPutResponse(self, response, key, item_id):
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

    def put(self, url, data, headers=[]):
        headers.append(('Content-Type', 'application/x-www-form-urlencoded'))
        r = self.test_client.put(url, data=data, headers=headers)
        return self.parse_response(r)

    def compare_put_with_get(self, fields, put_response):
        raw_r = self.test_client.get(self.item_id_url)
        r, status = self.parse_response(raw_r)
        self.assert200(status)
        self.assertEqual(raw_r.headers.get('ETag'),
                         put_response['key1']['etag'])
        if isinstance(fields, str):
            return r[fields]
        else:
            return [r[field] for field in fields]
