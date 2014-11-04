import simplejson as json
from datetime import datetime

from eve import STATUS_OK, LAST_UPDATED, ID_FIELD, ISSUES, STATUS, ETAG
from eve.tests import TestBaseSQL
from eve.tests.utils import DummyEvent


class TestPatch(TestBaseSQL):

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
        # replacing a 'user' with a valid 'contact' id will 404
        _, status = self.patch('%s/%s/' % (self.different_resource,
                                           self.unknown_item_id),
                               data={'firstname': 'doug'})
        self.assert404(status)

        # of course we can still put a 'user'
        _, status = self.patch('%s/%s/' % (self.different_resource,
                                           self.user_id),
                               data={'firstname': 'doug'},
                               headers=[('If-Match', self.user_etag)])
        self.assert200(status)

    def test_by_name(self):
        _, status = self.patch(self.user_firstname_url,
                               data={'key1': 'value1'})
        self.assert405(status)

    def test_ifmatch_missing(self):
        _, status = self.patch(self.item_id_url, data={'key1': 'value1'})
        self.assert403(status)

    def test_ifmatch_disabled(self):
        self.app.config['IF_MATCH'] = False
        r, status = self.patch(self.item_id_url, data={'key1': 'value1'})
        self.assertEqual(status, 422)
        self.assertTrue(ETAG not in r)

    def test_ifmatch_bad_etag(self):
        _, status = self.patch(self.item_id_url,
                               data={'key1': 'value1'},
                               headers=[('If-Match', 'not-quite-right')])
        self.assert412(status)

    def test_unique_value(self):
        r, status = self.patch(self.item_id_url,
                               data={"firstname": "%s" % self.item_firstname},
                               headers=[('If-Match', self.item_etag)])
        self.assertEqual(status, 422)
        self.assertValidationError(r,
                                   {'firstname': "value '%s' is not unique" %
                                       self.item_firstname})

    def test_patch_string(self):
        field = 'firstname'
        test_value = 'Douglas'
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

    def test_patch_datetime(self):
        field = "born"
        test_value = "Tue, 06 Nov 2012 10:33:31 GMT"
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_defaults(self):
        field = 'firstname'
        test_value = 'Douglas'
        changes = {field: test_value}
        r = self.perform_patch(changes)
        self.assertRaises(KeyError, self.compare_patch_with_get, 'title', r)

    def test_patch_defaults_with_post_override(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        r = self.perform_patch_with_post_override(field, test_value)
        self.assertRaises(KeyError, self.compare_patch_with_get, 'title',
                          json.loads(r.get_data()))

    def test_patch_multiple_fields(self):
        fields = ['firstname', 'prog']
        test_values = ['Douglas', 123]
        changes = {fields[0]: test_values[0], fields[1]: test_values[1]}
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
        self.assertEqual(raw_r.headers.get('ETag'), patch_response[ETAG])
        if isinstance(fields, str):
            result = r[fields]
            if not result:
                raise KeyError
            else:
                return result
        else:
            return [r[field] for field in fields]

    def test_patch_allow_unknown(self):
        changes = {"unknown": "unknown"}
        r, status = self.patch(self.item_id_url,
                               data=changes,
                               headers=[('If-Match', self.item_etag)])
        self.assertEqual(status, 422)
        self.assertValidationError(r, {'unknown': 'unknown field'})

    def test_patch_x_www_form_urlencoded(self):
        field = 'firstname'
        test_value = 'Douglas'
        changes = {field: test_value}
        headers = [('If-Match', self.item_etag)]
        r, status = self.parse_response(self.test_client.
                                        patch(self.item_id_url, data=changes,
                                              headers=headers))
        self.assert200(status)
        self.assertTrue('OK' in r[STATUS])

    def test_patch_referential_integrity(self):
        data = {'people_id': int(self.unknown_item_id)}
        headers = [('If-Match', self.invoice_etag)]
        r, status = self.patch(self.invoice_id_url, data=data, headers=headers)
        self.assertEqual(status, 422)
        expected = ("value '%s' must exist in resource '%s', field '%s'" %
                    (self.unknown_item_id, 'people',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, {'people_id': expected})

        data = {'people_id': self.item_id}
        r, status = self.patch(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        self.assertPatchResponse(r, self.invoice_id)

    def test_patch_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        # directly insert a document, without DATE_CREATED e LAST_UPDATED
        # values.
        _db = self.app.data.driver
        firstname = 'Douglas'
        person = self.test_sql_tables.People(firstname=firstname,
                                             lastname='Adams',
                                             prog=1)
        _db.session.add(person)
        _db.session.commit()

        # now retrieve same document via API and get its etag, which is
        # supposed to be computed on default DATE_CREATED and LAST_UPDATAED
        # values.
        response, status = self.get(self.known_resource, item=person._id)
        etag = response[ETAG]
        _id = response['_id']

        # attempt a PATCH with the new etag.
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {field: test_value}
        _, status = self.patch('%s/%s' % (self.known_resource_url, _id),
                               data=changes, headers=[('If-Match', etag)])
        self.assertEqual(status, 422)

    def test_patch_subresource(self):
        _db = self.app.data.driver

        # create random person
        fake_person = self.test_sql_tables.People.\
            from_tuple(self.random_people(1)[0])
        fake_person._created = datetime.now()
        fake_person._updated = datetime.now()
        _db.session.add(fake_person)
        _db.session.commit()
        fake_person_id = fake_person._id
        fake_invoice = self.test_sql_tables.Invoices(number=4)
        fake_invoice.people_id = fake_person_id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.commit()
        fake_invoice_id = fake_invoice._id

        # GET all invoices by new contact
        response, status = self.get('users/%s/invoices/%s' %
                                    (fake_person_id, fake_invoice_id))
        etag = response[ETAG]

        data = {"number": 5}
        headers = [('If-Match', etag)]
        response, status = self.patch('users/%s/invoices/%s' %
                                      (fake_person_id, fake_invoice_id),
                                      data=data, headers=headers)
        self.assert200(status)
        self.assertPatchResponse(response, fake_invoice_id)

    def test_patch_bandwidth_saver(self):
        changes = {'prog': 1234567890}

        # bandwidth_saver is on by default
        self.assertTrue(self.app.config['BANDWIDTH_SAVER'])
        r = self.perform_patch(changes)
        self.assertFalse('prog' in r)
        db_value = self.compare_patch_with_get(self.app.config['ETAG'], r)
        self.assertEqual(db_value, r[self.app.config['ETAG']])
        self.item_etag = r[self.app.config['ETAG']]

        # test return all fields (bandwidth_saver off)
        self.app.config['BANDWIDTH_SAVER'] = False
        r = self.perform_patch(changes)
        self.assertTrue('prog' in r)
        db_value = self.compare_patch_with_get(self.app.config['ETAG'], r)
        self.assertEqual(db_value, r[self.app.config['ETAG']])

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


class TestEvents(TestBaseSQL):
    new_person = {'firstname': 'Douglas', 'lastname': 'Adams', 'prog': 10}

    def test_on_pre_PATCH(self):
        devent = DummyEvent(self.before_update)
        self.app.on_pre_PATCH += devent
        self.patch()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(3, len(devent.called))

    def test_on_pre_PATCH_people(self):
        devent = DummyEvent(self.before_update)
        self.app.on_pre_PATCH_people += devent
        self.patch()
        self.assertEqual(2, len(devent.called))

    def test_on_PATCH_dynamic_filter(self):
        def filter_this(resource, request, lookup):
            lookup["_id"] = self.unknown_item_id
        self.app.on_pre_PATCH += filter_this
        # Would normally patch the known document; will return 404 instead.
        r, s = self.parse_response(self.patch())
        self.assert404(s)

    def test_on_post_PATCH(self):
        devent = DummyEvent(self.after_update)
        self.app.on_post_PATCH += devent
        self.patch()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(200, devent.called[2].status_code)
        self.assertEqual(3, len(devent.called))

    def test_on_post_PATCH_people(self):
        devent = DummyEvent(self.after_update)
        self.app.on_post_PATCH_people += devent
        self.patch()
        self.assertEqual(200, devent.called[1].status_code)
        self.assertEqual(2, len(devent.called))

    def test_on_update(self):
        devent = DummyEvent(self.before_update)
        self.app.on_update += devent
        self.patch()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(3, len(devent.called))

    def test_on_update_people(self):
        devent = DummyEvent(self.before_update)
        self.app.on_update_people += devent
        self.patch()
        self.assertEqual(2, len(devent.called))

    def test_on_updated(self):
        devent = DummyEvent(self.after_update)
        self.app.on_updated += devent
        self.patch()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(3, len(devent.called))

    def test_on_updated_people(self):
        devent = DummyEvent(self.after_update)
        self.app.on_updated_people += devent
        self.patch()
        self.assertEqual(2, len(devent.called))

    def before_update(self):
        _db = self.app.data.driver
        query = _db.session.query(self.test_sql_tables.People)
        person = query.get(self.item_id)
        return person.firstname == self.item_firstname

    def after_update(self):
        return not self.before_update()

    def patch(self):
        headers = [('Content-Type', 'application/json'),
                   ('If-Match', self.item_etag)]
        data = json.dumps(self.new_person)
        return self.test_client.patch(self.item_id_url, data=data,
                                      headers=headers)
