from bson import ObjectId
import simplejson as json

from eve.tests import TestBase
from eve.tests.test_settings import MONGO_DBNAME
from eve.tests.utils import DummyEvent

from eve import STATUS_OK, LAST_UPDATED, ID_FIELD, ISSUES, STATUS, ETAG
from eve.methods.put import put_internal


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
                             data={'ref': '1234567890123456789012345',
                                   'username': 'username1'})
        self.assert404(status)

        # of course we can still put a 'user'
        _, status = self.put('%s/%s/' % (self.different_resource,
                                         self.user_id),
                             data={'ref': '1234567890123456789012345',
                                   'username': 'username1'},
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
        r, status = self.put(self.item_id_url,
                             data={'ref': '1234567890123456789012345'})
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
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {'ref': "value '%s' is not unique" %
                                       self.alt_ref})

    def test_allow_unknown(self):
        changes = {"unknown": "unknown"}
        r, status = self.put(self.item_id_url, data=changes,
                             headers=[('If-Match', self.item_etag)])
        self.assertValidationErrorStatus(status)
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
        self.assertValidationErrorStatus(status)
        expected = ("value '%s' must exist in resource '%s', field '%s'" %
                    (self.unknown_item_id, 'contacts',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, {'person': expected})

        data = {"person": self.item_id}
        r, status = self.put(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        self.assertPutResponse(r, self.invoice_id)

    def test_put_referential_integrity_list(self):
        data = {"invoicing_contacts": [self.item_id, self.unknown_item_id]}
        headers = [('If-Match', self.invoice_etag)]
        r, status = self.put(self.invoice_id_url, data=data, headers=headers)
        self.assertValidationErrorStatus(status)
        expected = ("value '%s' must exist in resource '%s', field '%s'" %
                    (self.unknown_item_id, 'contacts',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, {'invoicing_contacts': expected})

        data = {"invoicing_contacts": [self.item_id, self.item_id]}
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

    def test_put_bandwidth_saver(self):
        changes = {'ref': '1234567890123456789012345'}

        # bandwidth_saver is on by default
        self.assertTrue(self.app.config['BANDWIDTH_SAVER'])
        r = self.perform_put(changes)
        self.assertFalse('ref' in r)
        db_value = self.compare_put_with_get(self.app.config['ETAG'], r)
        self.assertEqual(db_value, r[self.app.config['ETAG']])
        self.item_etag = r[self.app.config['ETAG']]

        # test return all fields (bandwidth_saver off)
        self.app.config['BANDWIDTH_SAVER'] = False
        r = self.perform_put(changes)
        self.assertTrue('ref' in r)
        db_value = self.compare_put_with_get(self.app.config['ETAG'], r)
        self.assertEqual(db_value, r[self.app.config['ETAG']])

    def test_put_dependency_fields_with_default(self):
        # Test that if a dependency is missing but has a default value then the
        # field is still accepted. See #353.
        del(self.domain['contacts']['schema']['ref']['required'])
        field = "dependency_field2"
        test_value = "a value"
        changes = {field: test_value}
        r = self.perform_put(changes)
        db_value = self.compare_put_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_put_internal(self):
        # test that put_internal is available and working properly.
        test_field = 'ref'
        test_value = "9876543210987654321098765"
        data = {test_field: test_value}
        with self.app.test_request_context(self.item_id_url):
            r, _, _, status = put_internal(
                self.known_resource, data, concurrency_check=False,
                **{'_id': self.item_id})
        db_value = self.compare_put_with_get(test_field, r)
        self.assertEqual(db_value, test_value)
        self.assert200(status)

    def test_put_etag_header(self):
        # test that Etag is always includer with response header. See #562.
        changes = {"ref": "1234567890123456789012345"}
        headers = [('Content-Type', 'application/json'),
                   ('If-Match', self.item_etag)]
        r = self.test_client.put(self.item_id_url,
                                 data=json.dumps(changes),
                                 headers=headers)
        self.assertTrue('Etag' in r.headers)

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


class TestEvents(TestBase):
    new_ref = "0123456789012345678901234"

    def test_on_pre_PUT(self):
        devent = DummyEvent(self.before_replace)
        self.app.on_pre_PUT += devent
        self.put()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(3, len(devent.called))

    def test_on_pre_PUT_contacts(self):
        devent = DummyEvent(self.before_replace)
        self.app.on_pre_PUT_contacts += devent
        self.put()
        self.assertEqual(2, len(devent.called))

    def test_on_pre_PUT_dynamic_filter(self):
        def filter_this(resource, request, lookup):
            lookup["_id"] = self.unknown_item_id
        self.app.on_pre_PUT += filter_this
        # Would normally delete the known document; will return 404 instead.
        r, s = self.parse_response(self.put())
        self.assert404(s)

    def test_on_post_PUT(self):
        devent = DummyEvent(self.after_replace)
        self.app.on_post_PUT += devent
        self.put()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(200, devent.called[2].status_code)
        self.assertEqual(3, len(devent.called))

    def test_on_post_PUT_contacts(self):
        devent = DummyEvent(self.after_replace)
        self.app.on_post_PUT_contacts += devent
        self.put()
        self.assertEqual(200, devent.called[1].status_code)
        self.assertEqual(2, len(devent.called))

    def test_on_replace(self):
        devent = DummyEvent(self.before_replace)
        self.app.on_replace += devent
        self.put()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(self.new_ref, devent.called[1]['ref'])
        self.assertEqual(3, len(devent.called))

    def test_on_replace_contacts(self):
        devent = DummyEvent(self.before_replace)
        self.app.on_replace_contacts += devent
        self.put()
        self.assertEqual(self.new_ref, devent.called[0]['ref'])
        self.assertEqual(2, len(devent.called))

    def test_on_replaced(self):
        devent = DummyEvent(self.after_replace)
        self.app.on_replaced += devent
        self.put()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(self.new_ref, devent.called[1]['ref'])
        self.assertEqual(3, len(devent.called))

    def test_on_replaced_contacts(self):
        devent = DummyEvent(self.after_replace)
        self.app.on_replaced_contacts += devent
        self.put()
        self.assertEqual(self.new_ref, devent.called[0]['ref'])
        self.assertEqual(2, len(devent.called))

    def before_replace(self):
        db = self.connection[MONGO_DBNAME]
        contact = db.contacts.find_one(ObjectId(self.item_id))
        return contact['ref'] == self.item_name

    def after_replace(self):
        return not self.before_replace()

    def put(self):
        headers = [('Content-Type', 'application/json'),
                   ('If-Match', self.item_etag)]
        data = json.dumps({"ref": self.new_ref})
        return self.test_client.put(self.item_id_url, data=data,
                                    headers=headers)
