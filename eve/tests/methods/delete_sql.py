from datetime import datetime
from eve.tests import TestBaseSQL
from eve.tests.utils import DummyEvent
from eve import ETAG


class TestDeleteSQL(TestBaseSQL):

    def setUp(self, settings_file=None, url_converters=None):
        super(TestDeleteSQL, self).setUp(settings_file, url_converters)
        # Etag used to delete an item (a contact)
        self.etag_headers = [('If-Match', self.item_etag)]

    def test_unknown_resource(self):
        url = '%s%s/' % (self.unknown_resource_url, self.item_id)
        _, status = self.delete(url)
        self.assert404(status)

    def test_delete_from_resource_endpoint(self):
        r, status = self.delete(self.known_resource_url)
        self.assert200(status)
        r, status = self.parse_response(self.test_client.get(
            self.known_resource_url))
        self.assert200(status)
        self.assertEqual(len(r['_items']), 0)

    def test_delete_from_resource_endpoint_different_resource(self):
        r, status = self.delete(self.different_resource_url)
        self.assert200(status)
        r, status = self.parse_response(self.test_client.get(
            self.different_resource_url))
        self.assert200(status)
        self.assertEqual(len(r['_items']), 0)

        # deletion of 'users' will still lave 'contacts' untouched (same db
        # collection)
        r, status = self.parse_response(self.test_client.get(
            self.known_resource_url))
        self.assert200(status)
        self.assertEqual(len(r['_items']), 25)

    def test_delete_empty_resource(self):
        url = '%s%s/' % (self.empty_resource_url, self.item_id)
        _, status = self.delete(url)
        self.assert404(status)

    def test_delete_readonly_resource(self):
        _, status = self.delete(self.readonly_id_url)
        self.assert405(status)

    def test_delete_unknown_item(self):
        url = '%s%s/' % (self.known_resource_url, self.unknown_item_id)
        _, status = self.delete(url)
        self.assert404(status)

    def test_delete_if_match_missing(self):
        _, status = self.delete(self.item_id_url)
        self.assert403(status)

    def test_delete_if_match_disabled(self):
        self.app.config['IF_MATCH'] = False
        _, status = self.delete(self.item_id_url)
        self.assert200(status)

    def test_delete_ifmatch_bad_etag(self):
        _, status = self.delete(self.item_id_url,
                                headers=[('If-Match', 'not-quite-right')])
        self.assert412(status)

    def test_delete(self):
        r, status = self.delete(self.item_id_url, headers=self.etag_headers)
        self.assert200(status)

        r = self.test_client.get(self.item_id_url)
        self.assert404(r.status_code)

    def test_delete_non_existant(self):
        url = self.item_id_url[:-5] + "00000"
        r, status = self.delete(url, headers=self.etag_headers)
        self.assert404(status)

    def test_delete_different_resource(self):
        r, status = self.delete(self.user_id_url,
                                headers=[('If-Match', self.user_etag)])
        self.assert200(status)

        r = self.test_client.get(self.user_id_url)
        self.assert404(r.status_code)

    def test_delete_with_post_override(self):
        # POST request with DELETE override turns into a DELETE
        headers = [('X-HTTP-Method-Override', 'DELETE'),
                   ('If-Match', self.item_etag)]
        r = self.test_client.post(self.item_id_url, data={}, headers=headers)
        self.assert200(r.status_code)

    def test_delete_subresource(self):
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
        fake_invoice.people_id = fake_person._id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.commit()

        # grab parent collection count; we will use this later to make sure we
        # didn't delete all the users in the database. We add one extra invoice
        # to make sure that the actual count will never be 1 (which would
        # invalidate the test)
        response, status = self.get('invoices')
        invoices = len(response[self.app.config['ITEMS']])

        # verify that the only document retrieved is referencing the correct
        # parent document
        response, status = self.get('users/%s/invoices' % fake_person_id)
        person_id = response[self.app.config['ITEMS']][1]['people']['_id']
        self.assertEqual(person_id, fake_person_id)

        # delete all documents at the sub-resource endpoint
        response, status = self.delete('users/%s/invoices' % fake_person_id)
        self.assert200(status)

        # verify that the no documents are left at the sub-resource endpoint
        response, status = self.get('users/%s/invoices' % fake_person_id)
        self.assertEqual(len(response['_items']), 0)

        # verify that other documents in the invoices collection have not been
        # deleted
        response, status = self.get('invoices')
        self.assertEqual(len(response['_items']), invoices - 2)

    def test_delete_subresource_item(self):
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
        fake_invoice.people_id = fake_person._id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.commit()
        fake_invoice_id = fake_invoice._id

        # GET all invoices by new contact
        response, status = self.get('users/%s/invoices/%s' %
                                    (fake_person_id, fake_invoice_id))
        etag = response[ETAG]

        headers = [('If-Match', etag)]
        response, status = self.delete('users/%s/invoices/%s' %
                                       (fake_person_id, fake_invoice_id),
                                       headers=headers)
        self.assert200(status)

    def delete(self, url, headers=None):
        r = self.test_client.delete(url, headers=headers)
        return self.parse_response(r)


class TestDeleteEvents(TestBaseSQL):

    def test_on_pre_DELETE_for_item(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_pre_DELETE += devent
        self.delete_item()
        self.assertEqual('people', devent.called[0])
        self.assertFalse(devent.called[1] is None)

    def test_on_pre_DELETE_resource_for_item(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_pre_DELETE_people += devent
        self.delete_item()
        self.assertFalse(devent.called is None)

    def test_on_pre_DELETE_for_resource(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_pre_DELETE += devent
        self.delete_resource()
        self.assertFalse(devent.called is None)

    def test_on_pre_DELETE_resource_for_resource(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_pre_DELETE_people += devent
        self.delete_resource()
        self.assertFalse(devent.called is None)

    def test_on_pre_DELETE_dynamic_filter(self):
        def filter_this(resource, request, lookup):
            lookup["_id"] = self.unknown_item_id
        self.app.on_pre_DELETE += filter_this
        # Would normally delete the known document; will return 404 instead.
        r, s = self.parse_response(self.delete_item())
        self.assert404(s)

    def test_on_post_DELETE_for_item(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_post_DELETE += devent
        self.delete_item()
        self.assertFalse(devent.called is None)

    def test_on_post_DELETE_resource_for_item(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_post_DELETE_people += devent
        self.delete_item()
        self.assertFalse(devent.called is None)

    def test_on_post_DELETE_for_resource(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_post_DELETE += devent
        self.delete_resource()
        self.assertFalse(devent.called is None)

    def test_on_post_DELETE_resource_for_resource(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_post_DELETE_people += devent
        self.delete_resource()
        self.assertFalse(devent.called is None)

    def test_on_delete_resource(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_delete_resource += devent
        self.delete_resource()
        self.assertEqual(('people',), devent.called)

    def test_on_delete_resource_people(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_delete_resource_people += devent
        self.delete_resource()
        self.assertEqual(tuple(), devent.called)

    def test_on_deleted_resource(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_deleted_resource += devent
        self.delete_resource()
        self.assertEqual(('people',), devent.called)

    def test_on_deleted_resource_people(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_deleted_resource_people += devent
        self.delete_resource()
        self.assertEqual(tuple(), devent.called)

    def test_on_delete_item(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_delete_item += devent
        self.delete_item()
        self.assertEqual('people', devent.called[0])
        self.assertEqual(
            self.item_id, devent.called[1][self.app.config['ID_FIELD']])

    def test_on_delete_item_people(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_delete_item_people += devent
        self.delete_item()
        self.assertEqual(
            self.item_id, devent.called[0][self.app.config['ID_FIELD']])

    def test_on_deleted_item(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_deleted_item += devent
        self.delete_item()
        self.assertEqual('people', devent.called[0])
        self.assertEqual(
            self.item_id, devent.called[1][self.app.config['ID_FIELD']])

    def test_on_deleted_item_people(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_deleted_item_people += devent
        self.delete_item()
        self.assertEqual(
            self.item_id, devent.called[0][self.app.config['ID_FIELD']])

    def delete_resource(self):
        self.test_client.delete(self.known_resource_url)

    def delete_item(self):
        return self.test_client.delete(
            self.item_id_url, headers=[('If-Match', self.item_etag)])

    def before_delete(self):
        db = self.connection.session
        return db.query(self.test_sql_tables.People).\
            get(self.item_id) is not None

    def after_delete(self):
        return not self.before_delete()
