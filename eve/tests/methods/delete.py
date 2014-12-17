from eve.tests import TestBase
from eve.tests.utils import DummyEvent
from eve.tests.test_settings import MONGO_DBNAME
from eve import ETAG
from bson import ObjectId

from eve.methods.delete import deleteitem_internal


class TestDelete(TestBase):
    def setUp(self):
        super(TestDelete, self).setUp()
        # Etag used to delete an item (a contact)
        self.etag_headers = [('If-Match', self.item_etag)]

    def test_unknown_resource(self):
        url = '%s%s/' % (self.unknown_resource_url, self.item_id)
        _, status = self.delete(url)
        self.assert404(status)

    def test_delete_from_resource_endpoint(self):
        r, status = self.delete(self.known_resource_url)
        self.assert204(status)
        r, status = self.parse_response(self.test_client.get(
            self.known_resource_url))
        self.assert200(status)
        self.assertEqual(len(r['_items']), 0)

    def test_delete_from_resource_endpoint_write_concern(self):
        # should get a 500 since there's no replicaset on the mongod instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 2}
        _, status = self.delete(self.known_resource_url)
        self.assert500(status)

    def test_delete_from_resource_endpoint_different_resource(self):
        r, status = self.delete(self.different_resource_url)
        self.assert204(status)
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

    def test_delete_ifmatch_missing(self):
        _, status = self.delete(self.item_id_url)
        self.assert403(status)

    def test_delete_ifmatch_disabled(self):
        self.app.config['IF_MATCH'] = False
        _, status = self.delete(self.item_id_url)
        self.assert204(status)

    def test_delete_ifmatch_bad_etag(self):
        _, status = self.delete(self.item_id_url,
                                headers=[('If-Match', 'not-quite-right')])
        self.assert412(status)

    def test_delete(self):
        r, status = self.delete(self.item_id_url, headers=self.etag_headers)
        self.assert204(status)

        r = self.test_client.get(self.item_id_url)
        self.assert404(r.status_code)

    def test_delete_non_existant(self):
        url = self.item_id_url[:-5] + "00000"
        r, status = self.delete(url, headers=self.etag_headers)
        self.assert404(status)

    def test_delete_write_concern(self):
        # should get a 500 since there's no replicaset on the mongod instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 2}
        _, status = self.delete(self.item_id_url,
                                headers=[('If-Match', self.item_etag)])
        self.assert500(status)

    def test_delete_different_resource(self):
        r, status = self.delete(self.user_id_url,
                                headers=[('If-Match', self.user_etag)])
        self.assert204(status)

        r = self.test_client.get(self.user_id_url)
        self.assert404(r.status_code)

    def test_delete_with_post_override(self):
        # POST request with DELETE override turns into a DELETE
        headers = [('X-HTTP-Method-Override', 'DELETE'),
                   ('If-Match', self.item_etag)]
        r = self.test_client.post(self.item_id_url, data={}, headers=headers)
        self.assert204(r.status_code)

    def test_delete_subresource(self):
        _db = self.connection[MONGO_DBNAME]

        # create random contact
        fake_contact = self.random_contacts(1)
        fake_contact_id = _db.contacts.insert(fake_contact)[0]

        # grab parent collection count; we will use this later to make sure we
        # didn't delete all the users in the datanase. We add one extra invoice
        # to make sure that the actual count will never be 1 (which would
        # invalidate the test)
        _db.invoices.insert({'inv_number': 1})
        response, status = self.get('invoices')
        invoices = len(response[self.app.config['ITEMS']])

        # update first invoice to reference the new contact
        _db.invoices.update({'_id': ObjectId(self.invoice_id)},
                            {'$set': {'person': fake_contact_id}})

        # verify that the only document retrieved is referencing the correct
        # parent document
        response, status = self.get('users/%s/invoices' % fake_contact_id)
        person_id = ObjectId(response[self.app.config['ITEMS']][0]['person'])
        self.assertEqual(person_id, fake_contact_id)

        # delete all documents at the sub-resource endpoint
        response, status = self.delete('users/%s/invoices' % fake_contact_id)
        self.assert204(status)

        # verify that the no documents are left at the sub-resource endpoint
        response, status = self.get('users/%s/invoices' % fake_contact_id)
        self.assertEqual(len(response['_items']), 0)

        # verify that other documents in the invoices collection have not neen
        # deleted
        response, status = self.get('invoices')
        self.assertEqual(len(response['_items']), invoices - 1)

    def test_delete_subresource_item(self):
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

        headers = [('If-Match', etag)]
        response, status = self.delete('users/%s/invoices/%s' %
                                       (fake_contact_id, self.invoice_id),
                                       headers=headers)
        self.assert204(status)

    def test_deleteitem_internal(self):
        # test that deleteitem_internal is available and working properly.
        with self.app.test_request_context(self.item_id_url):
            r, _, _, status = deleteitem_internal(
                self.known_resource, concurrency_check=False,
                **{'_id': self.item_id})
        self.assert204(status)

        r = self.test_client.get(self.item_id_url)
        self.assert404(r.status_code)

    def delete(self, url, headers=None):
        r = self.test_client.delete(url, headers=headers)
        return self.parse_response(r)


class TestDeleteEvents(TestBase):
    def test_on_pre_DELETE_for_item(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_pre_DELETE += devent
        self.delete_item()
        self.assertEqual('contacts', devent.called[0])
        self.assertFalse(devent.called[1] is None)

    def test_on_pre_DELETE_resource_for_item(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_pre_DELETE_contacts += devent
        self.delete_item()
        self.assertFalse(devent.called is None)

    def test_on_pre_DELETE_for_resource(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_pre_DELETE += devent
        self.delete_resource()
        self.assertFalse(devent.called is None)

    def test_on_pre_DELETE_resource_for_resource(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_pre_DELETE_contacts += devent
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
        self.app.on_post_DELETE_contacts += devent
        self.delete_item()
        self.assertFalse(devent.called is None)

    def test_on_post_DELETE_for_resource(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_post_DELETE += devent
        self.delete_resource()
        self.assertFalse(devent.called is None)

    def test_on_post_DELETE_resource_for_resource(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_post_DELETE_contacts += devent
        self.delete_resource()
        self.assertFalse(devent.called is None)

    def test_on_delete_resource(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_delete_resource += devent
        self.delete_resource()
        self.assertEqual(('contacts',), devent.called)

    def test_on_delete_resource_contacts(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_delete_resource_contacts += devent
        self.delete_resource()
        self.assertEqual(tuple(), devent.called)

    def test_on_deleted_resource(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_deleted_resource += devent
        self.delete_resource()
        self.assertEqual(('contacts',), devent.called)

    def test_on_deleted_resource_contacts(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_deleted_resource_contacts += devent
        self.delete_resource()
        self.assertEqual(tuple(), devent.called)

    def test_on_delete_item(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_delete_item += devent
        self.delete_item()
        self.assertEqual('contacts', devent.called[0])
        self.assertEqual(
            self.item_id, str(devent.called[1][self.app.config['ID_FIELD']]))

    def test_on_delete_item_contacts(self):
        devent = DummyEvent(self.before_delete)
        self.app.on_delete_item_contacts += devent
        self.delete_item()
        self.assertEqual(
            self.item_id, str(devent.called[0][self.app.config['ID_FIELD']]))

    def test_on_deleted_item(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_deleted_item += devent
        self.delete_item()
        self.assertEqual('contacts', devent.called[0])
        self.assertEqual(
            self.item_id, str(devent.called[1][self.app.config['ID_FIELD']]))

    def test_on_deleted_item_contacts(self):
        devent = DummyEvent(self.after_delete)
        self.app.on_deleted_item_contacts += devent
        self.delete_item()
        self.assertEqual(
            self.item_id, str(devent.called[0][self.app.config['ID_FIELD']]))

    def delete_resource(self):
        self.test_client.delete(self.known_resource_url)

    def delete_item(self):
        return self.test_client.delete(
            self.item_id_url, headers=[('If-Match', self.item_etag)])

    def before_delete(self):
        db = self.connection[MONGO_DBNAME]
        return db.contacts.find_one(ObjectId(self.item_id)) is not None

    def after_delete(self):
        return not self.before_delete()
