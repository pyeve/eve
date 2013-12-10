import simplejson as json
from eve.tests import TestBase
from eve import STATUS_OK, LAST_UPDATED, ID_FIELD, ISSUES, STATUS, ETAG
from eve.tests.test_settings import MONGO_DBNAME
from bson import ObjectId


class TestPut(TestBase):
    # TODO consider making a base codebase out of 'patch' and 'put' tests
    def test_put_to_resource_endpoint(self):
        _, status = self.put(self.known_resource_url, data={})
        self.assert405(status)

    def test_readonly_resource(self):
        _, status = self.put(self.readonly_id_url, data={})
        self.assert405(status)

    def test_unknown_id(self):
        _, status = self.put(self.unknown_item_id_url,
                             data={'key1': 'value1'})
        self.assert404(status)

    def test_unknown_id_different_resource(self):
        # replacing a 'user' with a valid 'contact' id will 404
        _, status = self.put('%s/%s/' % (self.different_resource,
                                         self.item_id),
                             data={'key1': 'value1'})
        self.assert404(status)

        # of course we can still put a 'user'
        _, status = self.put('%s/%s/' % (self.different_resource,
                                         self.user_id),
                             data={'key1': '{"username": "username1"}'},
                             headers=[('If-Match', self.user_etag)])
        self.assert200(status)

    def test_by_name(self):
        _, status = self.put(self.item_name_url, data={'key1': 'value1'})
        self.assert405(status)

    def test_ifmatch_missing(self):
        _, status = self.put(self.item_id_url, data={'key1': 'value1'})
        self.assert403(status)

    def test_ifmatch_disabled(self):
        self.app.config['IF_MATCH'] = False
        r, status = self.put(self.item_id_url, data={'key1': 'value1'})
        self.assert200(status)
        self.assertTrue(ETAG not in r)

    def test_ifmatch_bad_etag(self):
        _, status = self.put(self.item_id_url,
                             data={'key1': 'value1'},
                             headers=[('If-Match', 'not-quite-right')])
        self.assert412(status)

    def test_unique_value(self):
        r, status = self.put(self.item_id_url,
                             data={"ref": "%s" % self.alt_ref},
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertValidationError(r, {'ref': "value '%s' is not unique" %
                                       self.alt_ref})

    def test_allow_unknown(self):
        changes = {"unknown": "unknown"}
        r, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertValidationError(r, {'unknown': 'unknown field'})
        self.app.config['DOMAIN'][self.known_resource]['allow_unknown'] = True
        changes = {"unknown": "unknown", "ref": "1234567890123456789012345"}
        r, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertPutResponse(r, self.item_id)

    def test_put_x_www_form_urlencoded(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {field: test_value}
        headers = [('If-Match', self.item_etag)]
        r, status = self.parse_response(self.test_client.put(
            self.item_id_url, data=changes, headers=headers))
        self.assert200(status)
        self.assertTrue('OK' in r[STATUS])

    def test_put_referential_integrity(self):
        data = {"person": self.unknown_item_id}
        headers = [('If-Match', self.invoice_etag)]
        r, status = self.put(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        expected = ("value '%s' must exist in resource '%s', field '%s'" %
                    (self.unknown_item_id, 'contacts',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, {'person': expected})

        data = {"person": self.item_id}
        r, status = self.put(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        self.assertPutResponse(r, self.invoice_id)

    def test_put_write_concern_success(self):
        # 0 and 1 are the only valid values for 'w' on our mongod instance (1
        # is the default)
        self.domain['contacts']['mongo_write_concern'] = {'w': 0}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {field: test_value}
        _, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)

    def test_put_write_concern_fail(self):
        # should get a 500 since there's no replicaset on the mongod instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 2}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {field: test_value}
        _, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert500(status)

    def test_put_string(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {field: test_value}
        r = self.perform_put(changes)
        db_value = self.compare_put_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_put_with_post_override(self):
        # POST request with PUT override turns into a PUT
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {field: test_value}
        headers = [('X-HTTP-Method-Override', 'PUT'),
                   ('If-Match', self.item_etag),
                   ('Content-Type', 'application/x-www-form-urlencoded')]
        r = self.test_client.post(self.item_id_url, data=changes,
                                  headers=headers)
        self.assert200(r.status_code)
        self.assertPutResponse(json.loads(r.get_data()), self.item_id)

    def test_put_default_value(self):
        test_field = 'title'
        test_value = "Mr."
        data = {'ref': '9234567890123456789054321'}
        r = self.perform_put(data)
        db_value = self.compare_put_with_get(test_field, r)
        self.assertEqual(test_value, db_value)

    def test_put_subresource(self):
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
        response, status = self.put('users/%s/invoices/%s' %
                                    (fake_contact_id, self.invoice_id),
                                    data=data, headers=headers)
        self.assert200(status)
        self.assertPutResponse(response, self.invoice_id)

    def perform_put(self, changes):
        r, status = self.put(self.item_id_url,
                             data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assert200(status)
        self.assertPutResponse(r, self.item_id)
        return r

    def assertPutResponse(self, response, item_id):
        self.assertTrue(STATUS in response)
        self.assertTrue(STATUS_OK in response[STATUS])
        self.assertFalse(ISSUES in response)
        self.assertTrue(ID_FIELD in response)
        self.assertEqual(response[ID_FIELD], item_id)
        self.assertTrue(LAST_UPDATED in response)
        self.assertTrue(ETAG in response)
        self.assertTrue('_links' in response)
        self.assertItemLink(response['_links'], item_id)

    def put(self, url, data, headers=[]):
        headers.append(('Content-Type', 'application/json'))
        r = self.test_client.put(url, data=json.dumps(data), headers=headers)
        return self.parse_response(r)

    def compare_put_with_get(self, fields, put_response):
        raw_r = self.test_client.get(self.item_id_url)
        r, status = self.parse_response(raw_r)
        self.assert200(status)
        self.assertEqual(raw_r.headers.get('ETag'),
                         put_response[ETAG])
        if isinstance(fields, str):
            return r[fields]
        else:
            return [r[field] for field in fields]
