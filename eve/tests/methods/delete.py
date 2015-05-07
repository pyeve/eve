from eve.tests import TestBase
from eve.tests.utils import DummyEvent
from eve.tests.test_settings import MONGO_DBNAME
from eve import ETAG
from bson import ObjectId
from eve.utils import ParsedRequest
import copy

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


class TestSoftDelete(TestDelete):
    def setUp(self):
        super(TestSoftDelete, self).setUp()

        # Enable soft delete
        self.app.config['SOFT_DELETE'] = True
        domain = copy.copy(self.domain)
        for resource, settings in domain.items():
            # rebuild resource settings for soft delete
            self.app.register_resource(resource, settings)

        # alias for the configured DELETED field name
        self.DELETED = self.app.config['DELETED']

    # TestDelete overrides

    def test_delete(self):
        """Soft delete should mark an item as deleted and cause subsequent
        requests to return 410 Gone responses. 410s sent in response to GET
        requests should include the document in their body with the _deleted
        flag set to True.
        """
        r, status = self.delete(self.item_id_url, headers=self.etag_headers)
        self.assert204(status)

        r = self.test_client.get(self.item_id_url)
        data, status = self.parse_response(r)
        self.assert410(status)

        self.assertEqual(data.get(self.DELETED), True)
        self.assertNotEqual(data.get('_etag'), self.item_etag)

    def test_deleteitem_internal(self):
        """Deleteitem internal should honor soft delete settings.
        """
        # test that deleteitem_internal is available and working properly.
        with self.app.test_request_context(self.item_id_url):
            r, _, _, status = deleteitem_internal(
                self.known_resource, concurrency_check=False,
                **{'_id': self.item_id})
        self.assert204(status)

        r = self.test_client.get(self.item_id_url)
        data, status = self.parse_response(r)
        self.assert410(status)
        self.assertEqual(data.get(self.DELETED), True)

    def test_delete_different_resource(self):
        r, status = self.delete(self.user_id_url,
                                headers=[('If-Match', self.user_etag)])
        self.assert204(status)

        r = self.test_client.get(self.user_id_url)
        data, status = self.parse_response(r)
        self.assert410(status)
        self.assertEqual(data.get(self.DELETED), True)

    def test_delete_from_resource_endpoint(self):
        """Soft deleting an entire resource should mark each individual item
        as deleted, queries to that resource should return no items, and GETs
        on any individual items should return 410 responses.
        """
        # TestDelete deletes resource at known_resource_url, and confirms
        # subsequent queries to the resource return zero items
        super(TestSoftDelete, self).test_delete_from_resource_endpoint()

        r = self.test_client.get(self.item_id_url)
        data, status = self.parse_response(r)
        self.assert410(status)
        self.assertEqual(data.get(self.DELETED), True)

    # TetsSoftDelete specific tests

    def test_operations_after_softdelete(self):
        """After an item has been soft deleted, PUTs, PATCHes, and DELETEs should
        return a 410 Gone response.
        """
        r, status = self.delete(self.item_id_url, headers=self.etag_headers)
        self.assert204(status)

        # PUT should return 410 Gone
        r = self.test_client.put(self.item_id_url,
                                 data={'ref': '1234567890123456789012345'},
                                 headers=self.etag_headers)
        self.assert410(r.status_code)

        # PATCH should return 410 Gone
        r = self.test_client.patch(self.item_id_url,
                                   data={'ref': '1234567890123456789012345'},
                                   headers=self.etag_headers)
        self.assert410(r.status_code)

        # Second soft DELETE should return 410 Gone
        r, status = self.delete(self.item_id_url, headers=self.etag_headers)
        self.assert410(status)

    def test_softdelete_deleted_field(self):
        """The configured 'deleted' field should be added to all documents to indicate
        whether that document has been soft deleted or not.
        """
        r = self.test_client.get(self.item_id_url)
        data, status = self.parse_response(r)
        self.assert200(status)
        self.assertEqual(data.get(self.DELETED), False)

    def test_softdelete_show_deleted(self):
        """GETs on resource endpoints should include soft deleted items when
        the 'show_deleted' param is included in the query
        """
        r, status = self.delete(self.item_id_url, headers=self.etag_headers)
        self.assert204(status)

        data, status = self.get(self.known_resource)
        after_softdelete_count = data[self.app.config['META']]['total']
        self.assertEqual(after_softdelete_count, self.known_resource_count - 1)

        data, status = self.get(self.known_resource, query="?show_deleted")
        show_deleted_count = data[self.app.config['META']]['total']
        self.assertEqual(show_deleted_count, self.known_resource_count)

        # Test show_deleted with additional queries
        role_query = '?where={"role": "' + self.item['role'] + '"}'
        data, status = self.get(self.known_resource, query=role_query)
        role_count = data[self.app.config['META']]['total']

        data, status = self.get(
            self.known_resource, query=role_query + "&show_deleted")
        show_deleted_role_count = data[self.app.config['META']]['total']
        self.assertEqual(show_deleted_role_count, role_count + 1)

    def test_softdeleted_embedded_doc(self):
        """Soft deleted documents embedded in other documents should not be
        included. They will resolve to None as if the document was actually
        deleted.
        """
        # Set up and confirm embedded document
        _db = self.connection[MONGO_DBNAME]
        fake_contact = self.random_contacts(1)
        fake_contact_id = _db.contacts.insert(fake_contact)[0]
        fake_contact_url = self.known_resource_url + "/" + str(fake_contact_id)
        _db.invoices.update({'_id': ObjectId(self.invoice_id)},
                            {'$set': {'person': fake_contact_id}})

        invoices = self.domain['invoices']
        invoices['embedding'] = True
        invoices['schema']['person']['data_relation']['embeddable'] = True
        embedded = '{"person": 1}'

        r = self.test_client.get(
            self.invoice_id_url + '?embedded=%s' % embedded)
        data, status = self.parse_response(r)
        self.assert200(status)
        self.assertTrue('location' in data['person'])

        # Get embedded doc etag so we can delete it
        r = self.test_client.get(fake_contact_url)
        embedded_contact_etag = r.headers['ETag']

        # Delete embedded contact
        data, status = self.delete(
            fake_contact_url, headers=[('If-Match', embedded_contact_etag)])
        self.assert204(status)

        # embedded 'person' should now be empty
        r = self.test_client.get(
            self.invoice_id_url + '?embedded=%s' % embedded)
        data, status = self.parse_response(r)
        self.assert200(status)
        self.assertEqual(data['person'], None)

    def test_softdeleted_get_response_skips_embedded_expansion(self):
        """Soft deleted documents should not expand their embedded documents when
        returned in a 410 Gone response. The deleted document data should
        reflect the state of the document when it was deleted, not change if
        still active embedded documents are updated
        """
        # Confirm embedded document works before delete
        _db = self.connection[MONGO_DBNAME]
        fake_contact = self.random_contacts(1)
        fake_contact_id = _db.contacts.insert(fake_contact)[0]
        _db.invoices.update({'_id': ObjectId(self.invoice_id)},
                            {'$set': {'person': fake_contact_id}})

        invoices = self.domain['invoices']
        invoices['embedding'] = True
        invoices['schema']['person']['data_relation']['embeddable'] = True
        embedded = '{"person": 1}'

        r = self.test_client.get(
            self.invoice_id_url + '?embedded=%s' % embedded)
        invoice_etag = r.headers['ETag']
        data, status = self.parse_response(r)
        self.assert200(status)
        self.assertTrue('location' in data['person'])

        # Soft delete document
        data, status = self.delete(
            self.invoice_id_url, headers=[('If-Match', invoice_etag)])
        self.assert204(status)

        # Document in 410 should not expand person
        r = self.test_client.get(
            self.invoice_id_url + '?embedded=%s' % embedded)
        data, status = self.parse_response(r)
        self.assert410(status)
        self.assertEqual(data['person'], str(fake_contact_id))

    def test_softdelete_caching(self):
        """410 Gone responses after soft delete should be cacheable
        """
        # Soft delete item
        r, status = self.delete(self.item_id_url, headers=self.etag_headers)
        self.assert204(status)

        # delete should have invalidated any previously cached 200 responses
        r = self.test_client.get(
            self.item_id_url, headers=[('If-None-Match', self.item_etag)])
        self.assert410(r.status_code)

        post_delete_etag = r.headers['ETag']

        # validate cached 410 response data
        r = status = self.test_client.get(
            self.item_id_url, headers=[('If-None-Match', post_delete_etag)])
        self.assert304(r.status_code)

    def test_softdelete_datalayer(self):
        """Soft deleted items should not be returned by find methods in the Eve
        data layer unless show_deleted is explicitly configured in the request,
        the deleted field is included in the lookup, or the operation is 'raw'.
        """
        # Soft delete item
        r, status = self.delete(self.item_id_url, headers=self.etag_headers)
        self.assert204(status)

        with self.app.test_request_context():
            # find_one should only return item if a request w/ show_deleted ==
            # True is passed or if the deleted field is part of the lookup
            req = ParsedRequest()
            doc = self.app.data.find_one(
                self.known_resource, req, _id=self.item_id)
            self.assertEqual(doc, None)

            req.show_deleted = True
            doc = self.app.data.find_one(
                self.known_resource, req, _id=self.item_id)
            self.assertNotEqual(doc, None)
            self.assertEqual(doc.get(self.DELETED), True)

            req.show_deleted = False
            doc = self.app.data.find_one(
                self.known_resource, req, _id=self.item_id, _deleted=True)
            self.assertNotEqual(doc, None)
            self.assertEqual(doc.get(self.DELETED), True)

            # find_one_raw should always return a document, soft deleted or not
            doc = self.app.data.find_one_raw(
                self.known_resource, _id=ObjectId(self.item_id))
            self.assertNotEqual(doc, None)
            self.assertEqual(doc.get(self.DELETED), True)

            # find should only return deleted items if a request with
            # show_deleted == True is passed or if the deleted field is part of
            # the lookup
            req.show_deleted = False
            docs = self.app.data.find(self.known_resource, req, None)
            undeleted_count = docs.count()

            req.show_deleted = True
            docs = self.app.data.find(self.known_resource, req, None)
            with_deleted_count = docs.count()
            self.assertEqual(undeleted_count, with_deleted_count - 1)

            req.show_deleted = False
            docs = self.app.data.find(
                self.known_resource, req, {self.DELETED: True})
            deleted_count = docs.count()
            self.assertEqual(deleted_count, 1)

            # find_list_of_ids will return deleted documents if given their id
            docs = self.app.data.find_list_of_ids(
                self.known_resource, [ObjectId(self.item_id)])
            self.assertEqual(docs.count(), 1)


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
