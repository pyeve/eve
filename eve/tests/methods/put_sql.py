from datetime import datetime
import simplejson as json

from eve import STATUS_OK, LAST_UPDATED, ID_FIELD, ISSUES, STATUS, ETAG
from eve.tests import TestBaseSQL
from eve.tests.utils import DummyEvent


class TestPutSQL(TestBaseSQL):

    def test_put_to_resource_endpoint(self):
        _, status = self.put(self.known_resource_url, data={})
        self.assert405(status)

    def test_readonly_resource(self):
        _, status = self.put(self.readonly_id_url, data={})
        self.assert405(status)

    def test_unknown_id(self):
        _, status = self.put(self.unknown_item_id_url, data={'key1': 'value1'})
        self.assert404(status)

    def test_unknown_id_different_resource(self):
        # replacing a 'user' with a valid 'contact' id will 404
        _, status = self.put('%s/%s/' % (self.different_resource,
                                         self.unknown_item_id),
                             data={'firstname': 'doug'})
        self.assert404(status)

        # of course we can still put a 'user'
        _, status = self.put('%s/%s/' % (self.different_resource,
                                         self.user_id),
                             data={'firstname': 'doug'},
                             headers=[('If-Match', self.user_etag)])
        self.assert200(status)

    def test_by_name(self):
        _, status = self.put(self.user_firstname_url, data={'key1': 'value1'})
        self.assert405(status)

    def test_ifmatch_missing(self):
        _, status = self.put(self.item_id_url, data={'key1': 'value1'})
        self.assert403(status)

    def test_ifmatch_disabled(self):
        self.app.config['IF_MATCH'] = False
        r, status = self.put(self.item_id_url, data={'key1': 'value1'})
        self.assertEqual(status, 422)
        self.assertTrue(ETAG not in r)

    def test_ifmatch_bad_etag(self):
        _, status = self.put(self.item_id_url,
                             data={'key1': 'value1'},
                             headers=[('If-Match', 'not-quite-right')])
        self.assert412(status)

    def test_unique_value(self):
        r, status = self.put(self.item_id_url,
                             data={"firstname": "%s" % self.item_firstname},
                             headers=[('If-Match', self.item_etag)])
        self.assertEqual(status, 422)
        self.assertValidationError(r,
                                   {'firstname': "value '%s' is not unique" %
                                       self.item_firstname})

    def test_put_x_www_form_urlencoded(self):
        field = "firstname"
        test_value = "Douglas"
        changes = {field: test_value}
        headers = [('If-Match', self.item_etag)]
        r, status = self.parse_response(self.test_client.put(
            self.item_id_url, data=changes, headers=headers))
        self.assert200(status)
        self.assertTrue('OK' in r[STATUS])

    def test_put_referential_integrity(self):
        data = {"people_id": int(self.unknown_item_id)}
        headers = [('If-Match', self.invoice_etag)]
        r, status = self.put(self.invoice_id_url, data=data, headers=headers)
        self.assertEqual(status, 422)
        expected = ("value '%s' must exist in resource '%s', field '%s'" %
                    (self.unknown_item_id, 'people',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, {'people_id': expected})

        data = {"people_id": self.item_id}
        r, status = self.put(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        self.assertPutResponse(r, self.invoice_id)

    def test_put_string(self):
        field = "firstname"
        test_value = "Douglas"
        changes = {field: test_value}
        r = self.perform_put(changes)
        db_value = self.compare_put_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_put_with_post_override(self):
        # POST request with PUT override turns into a PUT
        field = "firstname"
        test_value = "Douglas"
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
        test_value = 'Mr.'
        data = {'firstname': 'Douglas'}
        r = self.perform_put(data)
        db_value = self.compare_put_with_get(test_field, r)
        self.assertEqual(test_value, db_value)

    def test_put_subresource(self):
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
        response, status = self.put('users/%s/invoices/%s' %
                                    (fake_person_id, fake_invoice_id),
                                    data=data, headers=headers)
        self.assert200(status)
        self.assertPutResponse(response, fake_invoice_id)

    def test_put_bandwidth_saver(self):
        changes = {'prog': 1234567890}

        # bandwidth_saver is on by default
        self.assertTrue(self.app.config['BANDWIDTH_SAVER'])
        r = self.perform_put(changes)
        self.assertFalse('prog' in r)
        db_value = self.compare_put_with_get(self.app.config['ETAG'], r)
        self.assertEqual(db_value, r[self.app.config['ETAG']])
        self.item_etag = r[self.app.config['ETAG']]

        # test return all fields (bandwidth_saver off)
        self.app.config['BANDWIDTH_SAVER'] = False
        r = self.perform_put(changes)
        self.assertTrue('prog' in r)
        db_value = self.compare_put_with_get(self.app.config['ETAG'], r)
        self.assertEqual(db_value, r[self.app.config['ETAG']])

    def test_put_dependency_fields_with_default(self):
        # test that default values are resolved before validation. See #353.
        del(self.domain['people']['schema']['prog']['required'])
        field = "firstname"
        test_value = "Mary"
        changes = {field: test_value}
        r = self.perform_put(changes)
        db_value = self.compare_put_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def perform_put(self, changes):
        r, status = self.put(self.item_id_url, data=changes,
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
        self.assertEqual(raw_r.headers.get('ETag'), put_response[ETAG])
        if isinstance(fields, str):
            return r[fields]
        else:
            return [r[field] for field in fields]


class TestEventsSQL(TestBaseSQL):
    new_person = {'firstname': 'Douglas', 'lastname': 'Adams', 'prog': 10}

    def test_on_pre_PUT(self):
        devent = DummyEvent(self.before_replace)
        self.app.on_pre_PUT += devent
        self.put()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(3, len(devent.called))

    def test_on_pre_PUT_people(self):
        devent = DummyEvent(self.before_replace)
        self.app.on_pre_PUT_people += devent
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

    def test_on_post_PUT_people(self):
        devent = DummyEvent(self.after_replace)
        self.app.on_post_PUT_people += devent
        self.put()
        self.assertEqual(200, devent.called[1].status_code)
        self.assertEqual(2, len(devent.called))

    def test_on_replace(self):
        devent = DummyEvent(self.before_replace)
        self.app.on_replace += devent
        self.put()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(self.new_person['firstname'],
                         devent.called[1]['firstname'])
        self.assertEqual(3, len(devent.called))

    def test_on_replace_people(self):
        devent = DummyEvent(self.before_replace)
        self.app.on_replace_people += devent
        self.put()
        self.assertEqual(self.new_person['firstname'],
                         devent.called[0]['firstname'])
        self.assertEqual(2, len(devent.called))

    def test_on_replaced(self):
        devent = DummyEvent(self.after_replace)
        self.app.on_replaced += devent
        self.put()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(self.new_person['firstname'],
                         devent.called[1]['firstname'])
        self.assertEqual(3, len(devent.called))

    def test_on_replaced_people(self):
        devent = DummyEvent(self.after_replace)
        self.app.on_replaced_people += devent
        self.put()
        self.assertEqual(self.new_person['firstname'],
                         devent.called[0]['firstname'])
        self.assertEqual(2, len(devent.called))

    def before_replace(self):
        _db = self.app.data.driver
        query = _db.session.query(self.test_sql_tables.People)
        person = query.get(self.item_id)
        return person.firstname == self.item_firstname

    def after_replace(self):
        return not self.before_replace()

    def put(self):
        headers = [('Content-Type', 'application/json'),
                   ('If-Match', self.item_etag)]
        data = json.dumps(self.new_person)
        return self.test_client.put(self.item_id_url, data=data,
                                    headers=headers)
