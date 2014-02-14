import types
import simplejson as json
from datetime import datetime
from bson import ObjectId
from eve.tests import TestBase
from eve.tests.test_settings import MONGO_DBNAME
from eve.utils import date_to_str


class TestGet(TestBase):

    def test_get_empty_resource(self):
        response, status = self.get(self.empty_resource)
        self.assert200(status)

        resource = response['_items']
        self.assertEqual(len(resource), 0)

        links = response['_links']
        self.assertEqual(len(links), 2)
        self.assertResourceLink(links, self.empty_resource)
        self.assertHomeLink(links)

    def test_get_max_results(self):
        maxr = 10
        response, status = self.get(self.known_resource,
                                    '?max_results=%d' % maxr)
        self.assert200(status)

        resource = response['_items']
        self.assertEqual(len(resource), maxr)

        maxr = self.app.config['PAGINATION_LIMIT'] + 1
        response, status = self.get(self.known_resource,
                                    '?max_results=%d' % maxr)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_LIMIT'])

    def test_get_page(self):
        response, status = self.get(self.known_resource)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 2)
        self.assertLastLink(links, 5)

        page = 1
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 2)
        self.assertLastLink(links, 5)

        page = 2
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)
        self.assertLastLink(links, 5)

        page = 5
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertPrevLink(links, 4)
        self.assertLastLink(links, None)

    def test_get_paging_disabled(self):
        self.app.config['DOMAIN'][self.known_resource]['pagination'] = False
        response, status = self.get(self.known_resource, '?page=2')
        self.assert200(status)
        resource = response['_items']
        self.assertFalse(len(resource) ==
                         self.app.config['PAGINATION_DEFAULT'])
        links = response['_links']
        self.assertTrue('next' not in links)
        self.assertTrue('prev' not in links)

    def test_get_paging_disabled_no_args(self):
        self.app.config['DOMAIN'][self.known_resource]['pagination'] = False
        response, status = self.get(self.known_resource)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.known_resource_count)
        links = response['_links']
        self.assertTrue('next' not in links)
        self.assertTrue('prev' not in links)

    def test_get_where_mongo_syntax(self):
        where = '{"ref": "%s"}' % self.item_name
        response, status = self.get(self.known_resource,
                                    '?where=%s' % where)
        self.assert200(status)

        resource = response['_items']
        self.assertEqual(len(resource), 1)

    def test_get_where_mongo_combined_date(self):
        where = '{"$and": [{"ref": "%s"}, {"_created": \
                {"$gte": "Tue, 01 Oct 2013 00:59:22 GMT"}}]}' % self.item_name
        response, status = self.get(self.known_resource,
                                    '?where=%s' % where)
        self.assert200(status)

        resource = response['_items']
        self.assertEqual(len(resource), 1)

    def test_get_mongo_query_blacklist(self):
        where = '{"$where": "this.ref == ''%s''"}' % self.item_name
        _, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert400(status)

        where = '{"ref": {"$regex": "%s"}}' % self.item_name
        _, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert400(status)

    def test_get_where_mongo_objectid_as_string(self):
        where = '{"tid": "%s"}' % self.item_tid
        response, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), 1)

        self.app.config['DOMAIN']['contacts']['query_objectid_as_string'] = \
            True
        response, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), 0)

    def test_get_where_python_syntax(self):
        where = 'ref == %s' % self.item_name
        response, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert200(status)

        resource = response['_items']
        self.assertEqual(len(resource), 1)

    def test_get_where_python_syntax1(self):
        where = 'ref == %s and _created>="Tue, 01 Oct 2013 00:59:22 GMT"' \
                % self.item_name
        response, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert200(status)

        resource = response['_items']
        self.assertEqual(len(resource), 1)

    def test_get_projection(self):
        projection = '{"prog": 1}'
        response, status = self.get(self.known_resource, '?projection=%s' %
                                    projection)
        self.assert200(status)

        resource = response['_items']

        for r in resource:
            self.assertFalse('location' in r)
            self.assertFalse('role' in r)
            self.assertTrue('prog' in r)
            self.assertTrue(self.app.config['ID_FIELD'] in r)
            self.assertTrue(self.app.config['LAST_UPDATED'] in r)
            self.assertTrue(self.app.config['DATE_CREATED'] in r)

        projection = '{"prog": 0}'
        response, status = self.get(self.known_resource, '?projection=%s' %
                                    projection)
        self.assert200(status)

        resource = response['_items']

        for r in resource:
            self.assertFalse('prog' in r)
            self.assertTrue('location' in r)
            self.assertTrue('role' in r)
            self.assertTrue(self.app.config['ID_FIELD'] in r)
            self.assertTrue(self.app.config['LAST_UPDATED'] in r)
            self.assertTrue(self.app.config['DATE_CREATED'] in r)

    def test_get_projection_noschema(self):
        self.app.config['DOMAIN'][self.known_resource]['schema'] = {}
        response, status = self.get(self.known_resource)
        self.assert200(status)

        resource = response['_items']

        # fields are returned anyway since no schema = return all fields
        for r in resource:
            self.assertTrue('location' in r)
            self.assertTrue(self.app.config['ID_FIELD'] in r)
            self.assertTrue(self.app.config['LAST_UPDATED'] in r)
            self.assertTrue(self.app.config['DATE_CREATED'] in r)

    def test_get_where_disabled(self):
        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = []
        where = 'ref == %s' % self.item_name
        response, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_DEFAULT'])

    def test_get_sort_mongo_syntax(self):
        sort = '[("prog",-1)]'
        response, status = self.get(self.known_resource,
                                    '?sort=%s' % sort)
        self.assert200(status)

        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_DEFAULT'])
        topvalue = 100
        for i in range(len(resource)):
            self.assertEqual(resource[i]['prog'], topvalue - i)

    def test_get_sort_disabled(self):
        self.app.config['DOMAIN'][self.known_resource]['sorting'] = False
        sort = '[("prog",-1)]'
        response, status = self.get(self.known_resource,
                                    '?sort=%s' % sort)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_DEFAULT'])
        for i in range(len(resource)):
            self.assertEqual(resource[i]['prog'], i)

    def test_get_default_sort(self):
        s = self.app.config['DOMAIN'][self.known_resource]['datasource']

        # set default sort to 'prog', desc.
        s['default_sort'] = [('prog', -1)]
        self.app.set_defaults()
        response, _ = self.get(self.known_resource)
        self.assertEqual(response['_items'][0]['prog'], 100)

        # set default sort to 'prog', asc.
        s['default_sort'] = [('prog', 1)]
        self.app.set_defaults()
        response, _ = self.get(self.known_resource)
        self.assertEqual(response['_items'][0]['prog'], 0)

    def test_get_if_modified_since(self):
        self.assertIfModifiedSince(self.known_resource_url)

    def test_cache_control(self):
        self.assertCacheControl(self.known_resource_url)

    def test_expires(self):
        self.assertExpires(self.known_resource_url)

    def test_get(self):
        response, status = self.get(self.known_resource)
        self.assertGet(response, status)

    def test_get_same_collection_different_resource(self):
        """ the 'users' resource is actually using the same db collection as
        'contacts'. Let's verify that base filters are being applied, and
        the right amount of items/links and the correct titles etc. are being
        returned. Of course 'contacts' itself has its own base filter, which
        excludes the 'users' (those with a 'username' field).
        """
        response, status = self.get(self.different_resource)
        self.assert200(status)

        links = response['_links']
        self.assertEqual(len(links), 2)
        self.assertHomeLink(links)
        self.assertResourceLink(links, self.different_resource)

        resource = response['_items']
        self.assertEqual(len(resource), 2)

        for item in resource:
            # 'user' title instead of original 'contact'
            self.assertItem(item)

        etag = item.get(self.app.config['ETAG'])
        self.assertTrue(etag is not None)

    def test_documents_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        contacts = self.random_contacts(1, False)
        ref = 'test_update_field'
        contacts[0]['ref'] = ref
        _db = self.connection[MONGO_DBNAME]
        _db.contacts.insert(contacts)
        where = '{"ref": "%s"}' % ref
        response, status = self.get(self.known_resource,
                                    '?where=%s' % where)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), 1)
        self.assertItem(resource[0])

    def test_get_where_allowed_filters(self):
        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = \
            ['notreally']
        where = '{"ref": "%s"}' % self.item_name
        r = self.test_client.get('%s%s' % (self.known_resource_url,
                                           '?where=%s' % where))
        self.assert400(r.status_code)
        self.assertTrue(b"'ref' not allowed" in r.get_data())

        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = \
            ['*']
        r = self.test_client.get('%s%s' % (self.known_resource_url,
                                           '?where=%s' % where))
        self.assert200(r.status_code)

    def test_get_with_post_override(self):
        # POST request with GET override turns into a GET
        headers = [('X-HTTP-Method-Override', 'GET')]
        r = self.test_client.post(self.known_resource_url, headers=headers)
        response, status = self.parse_response(r)
        self.assertGet(response, status)

    def test_get_custom_items(self):
        self.app.config['ITEMS'] = '_documents'
        response, _ = self.get(self.known_resource)
        self.assertTrue('_documents' in response and '_items' not in response)

    def test_get_custom_links(self):
        self.app.config['LINKS'] = '_navigation'
        response, _ = self.get(self.known_resource)
        self.assertTrue('_navigation' in response and '_links' not in response)

    def test_get_custom_auto_document_fields(self):
        self.app.config['LAST_UPDATED'] = '_updated_on'
        self.app.config['DATE_CREATED'] = '_created_on'
        self.app.config['ETAG'] = '_the_etag'
        response, _ = self.get(self.known_resource)
        for document in response['_items']:
            self.assertTrue('_updated_on' in document)
            self.assertTrue('_created_on' in document)
            self.assertTrue('_the_etag' in document)

    def test_get_embedded(self):
        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]

        fake_contact = self.random_contacts(1)
        fake_contact_id = _db.contacts.insert(fake_contact)[0]
        _db.invoices.update({'_id': ObjectId(self.invoice_id)},
                            {'$set': {'person': fake_contact_id}})

        invoices = self.domain['invoices']

        # Test that we get 400 if can't parse dict
        embedded = 'not-a-dict'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert400(r.status_code)

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is False by default)
        embedded = '{"person": 1}'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['person'], self.item_id)

        # Set field to be embedded
        invoices['schema']['person']['data_relation']['embeddable'] = True

        # Test that global setting applies even if field is set to embedded
        invoices['embedding'] = False
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['person'], self.item_id)

        # Test that it works
        invoices['embedding'] = True
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['_items'][0]['person'])

        # Test that it ignores a bogus field
        embedded = '{"person": 1, "not-a-real-field": 1}'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['_items'][0]['person'])

        # Test that it ignores a real field with a bogus value
        embedded = '{"person": 1, "inv_number": "not-a-real-value"}'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['_items'][0]['person'])

        # Test that it works with item endpoint too
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['person'])

    def test_get_default_embedding(self):
        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]

        fake_contact = self.random_contacts(1)
        fake_contact_id = _db.contacts.insert(fake_contact)[0]
        _db.invoices.update({'_id': ObjectId(self.invoice_id)},
                            {'$set': {'person': fake_contact_id}})

        invoices = self.domain['invoices']

        # Turn default field embedding on
        invoices['embedded_fields'] = ['person']

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is False by default)
        r = self.test_client.get(invoices['url'])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['person'], self.item_id)

        # Set field to be embedded
        invoices['schema']['person']['data_relation']['embeddable'] = True

        # Test that global setting applies even if field is set to embedded
        invoices['embedding'] = False
        r = self.test_client.get(invoices['url'])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['person'], self.item_id)

        # Test that it works
        invoices['embedding'] = True
        r = self.test_client.get(invoices['url'])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['_items'][0]['person'])

        # Test that it ignores a bogus field
        invoices['embedded_fields'] = ['person', 'not-really']
        r = self.test_client.get(invoices['url'])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['_items'][0]['person'])

        # Test that it works with item endpoint too
        r = self.test_client.get('%s/%s' % (invoices['url'], self.invoice_id))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['person'])

    def test_get_nested_resource(self):
        response, status = self.get('users/overseas')
        self.assertGet(response, status, 'users_overseas')

    def test_cursor_extra_find(self):
        self.app.data._find = self.app.data.find
        hits = {'total_hits': 0}

        def find(self, resource, req, sub_resource_lookup):
            def extra(self, response):
                response['_hits'] = hits
            cursor = self._find(resource, req, sub_resource_lookup)
            cursor.extra = types.MethodType(extra, cursor)
            return cursor

        self.app.data.find = types.MethodType(find, self.app.data)
        r, status = self.get(self.known_resource)
        self.assert200(status)
        self.assertTrue('_hits' in r)
        self.assertEquals(r['_hits'], hits)

    def test_get_resource_title(self):
        # test that resource endpoints accepts custom titles.
        self.app.config['DOMAIN'][self.known_resource]['resource_title'] = \
            'new title'
        response, _ = self.get(self.known_resource)
        self.assertTrue('new title' in response['_links']['self']['title'])
        # test that the home page accepts custom titles.
        response, _ = self.get('/')
        found = False
        for link in response['_links']['child']:
            if link['title'] == 'new title':
                found = True
                break
        self.assertTrue(found)

    def test_get_subresource(self):
        _db = self.connection[MONGO_DBNAME]

        # create random contact
        fake_contact = self.random_contacts(1)
        fake_contact_id = _db.contacts.insert(fake_contact)[0]
        # update first invoice to reference the new contact
        _db.invoices.update({'_id': ObjectId(self.invoice_id)},
                            {'$set': {'person': fake_contact_id}})

        # GET all invoices by new contact
        response, status = self.get('users/%s/invoices' % fake_contact_id)
        self.assert200(status)
        # only 1 invoice
        self.assertEqual(len(response['_items']), 1)
        self.assertEqual(len(response['_links']), 2)
        # which links to the right contact
        self.assertEqual(response['_items'][0]['person'], str(fake_contact_id))

    def test_get_ifmatch_disabled(self):
        # when IF_MATCH is disabled no etag is present in payload
        self.app.config['IF_MATCH'] = False
        response, status = self.get(self.known_resource)
        resource = response['_items']

        for r in resource:
            self.assertTrue(self.app.config['ETAG'] not in r)

    def test_get_ims_empty_resource(self):
        # test that a GET with a If-Modified-Since on an empty resource does
        # not trigger a 304 and returns a empty resource instead (#243).

        # get the resource and retrieve its IMS.
        r = self.test_client.get(self.known_resource_url)
        last_modified = r.headers.get('Last-Modified')

        # delete the whole resource content.
        r = self.test_client.delete(self.known_resource_url)

        # send a get with a IMS header from previous GET.
        r = self.test_client.get(self.known_resource_url,
                                 headers=[('If-Modified-Since',
                                           last_modified)])
        self.assert200(r.status_code)
        self.assertEqual(json.loads(r.get_data())['_items'], [])

    def assertGet(self, response, status, resource=None):
        self.assert200(status)

        links = response['_links']
        self.assertEqual(len(links), 4)
        self.assertHomeLink(links)
        if not resource:
            resource = self.known_resource
        self.assertResourceLink(links, resource)
        self.assertNextLink(links, 2)

        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_DEFAULT'])

        for item in resource:
            self.assertItem(item)

        etag = item.get(self.app.config['ETAG'])
        self.assertTrue(etag is not None)


class TestGetItem(TestBase):

    def assertItemResponse(self, response, status,
                           resource=None):
        self.assert200(status)
        self.assertTrue(self.app.config['ETAG'] in response)
        links = response['_links']
        self.assertEqual(len(links), 3)
        self.assertHomeLink(links)
        self.assertCollectionLink(links, resource or self.known_resource)
        self.assertItem(response)

    def test_disallowed_getitem(self):
        _, status = self.get(self.empty_resource, item=self.item_id)
        self.assert404(status)

    def test_getitem_by_id(self):
        response, status = self.get(self.known_resource,
                                    item=self.item_id)
        self.assertItemResponse(response, status)

        response, status = self.get(self.known_resource,
                                    item=self.unknown_item_id)
        self.assert404(status)

    def test_getitem_noschema(self):
        self.app.config['DOMAIN'][self.known_resource]['schema'] = {}
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assertItemResponse(response, status)

    def test_getitem_by_name(self):
        response, status = self.get(self.known_resource,
                                    item=self.item_name)
        self.assertItemResponse(response, status)
        response, status = self.get(self.known_resource,
                                    item=self.unknown_item_name)
        self.assert404(status)

    def test_getitem_by_name_self_href(self):
        response, status = self.get(self.known_resource,
                                    item=self.item_id)
        self_href = response['_links']['self']['href']

        response, status = self.get(self.known_resource,
                                    item=self.item_name)

        self.assertEquals(self_href, response['_links']['self']['href'])

    def test_getitem_by_integer(self):
        self.domain['contacts']['additional_lookup'] = {
            'field': 'prog'
        }
        self.app._add_url_rules()
        response, status = self.get(self.known_resource,
                                    item=1)
        self.assertItemResponse(response, status)
        response, status = self.get(self.known_resource,
                                    item=self.known_resource_count)
        self.assert404(status)

    def test_getitem_if_modified_since(self):
        self.assertIfModifiedSince(self.item_id_url)

    def test_getitem_if_none_match(self):
        r = self.test_client.get(self.item_id_url)
        etag = r.headers.get('ETag')
        self.assertTrue(etag is not None)
        r = self.test_client.get(self.item_id_url,
                                 headers=[('If-None-Match', etag)])
        self.assert304(r.status_code)
        self.assertTrue(not r.get_data())

    def test_cache_control(self):
        self.assertCacheControl(self.item_id_url)

    def test_expires(self):
        self.assertExpires(self.item_id_url)

    def test_getitem_by_id_different_resource(self):
        response, status = self.get(self.different_resource,
                                    item=self.user_id)
        self.assertItemResponse(response, status, self.different_resource)

        response, status = self.get(self.different_resource,
                                    item=self.item_id)
        self.assert404(status)

    def test_getitem_by_name_different_resource(self):
        response, status = self.get(self.different_resource,
                                    item=self.user_username)
        self.assertItemResponse(response, status, self.different_resource)
        response, status = self.get(self.different_resource,
                                    item=self.unknown_item_name)
        self.assert404(status)

    def test_getitem_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        contacts = self.random_contacts(1, False)
        ref = 'test_update_field'
        contacts[0]['ref'] = ref
        _db = self.connection[MONGO_DBNAME]
        _db.contacts.insert(contacts)
        response, status = self.get(self.known_resource, item=ref)
        self.assertItemResponse(response, status)

    def test_get_with_post_override(self):
        # POST request with GET override turns into a GET
        headers = [('X-HTTP-Method-Override', 'GET')]
        r = self.test_client.post(self.item_id_url, headers=headers)
        response, status = self.parse_response(r)
        self.assertItemResponse(response, status)

    def test_getitem_embedded(self):
        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]

        fake_contact = self.random_contacts(1)
        fake_contact_id = _db.contacts.insert(fake_contact)[0]
        _db.invoices.update({'_id': ObjectId(self.invoice_id)},
                            {'$set': {'person': fake_contact_id}})

        invoices = self.domain['invoices']

        # Test that we get 400 if can't parse dict
        embedded = 'not-a-dict'
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert400(r.status_code)

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is True by default)
        embedded = '{"person": 1}'
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['person'], self.item_id)

        # Set field to be embedded
        invoices['schema']['person']['data_relation']['embeddable'] = True

        # Test that global setting applies even if field is set to embedded
        invoices['embedding'] = False
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['person'], self.item_id)

        # Test that it works
        invoices['embedding'] = True
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['person'])

        # Test that it ignores a bogus field
        embedded = '{"person": 1, "not-a-real-field": 1}'
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['person'])

        # Test that it ignores a real field with a bogus value
        embedded = '{"person": 1, "inv_number": "not-a-real-value"}'
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['person'])

        # Test that it works with item endpoint too
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('location' in content['person'])

    def test_subresource_getitem(self):
        _db = self.connection[MONGO_DBNAME]

        # create random contact
        fake_contact = self.random_contacts(1)
        fake_contact_id = _db.contacts.insert(fake_contact)[0]
        # update first invoice to reference the new contact
        _db.invoices.update({'_id': ObjectId(self.invoice_id)},
                            {'$set': {'person': fake_contact_id}})

        # GET all invoices by new contact
        response, status = self.get('users/%s/invoices/%s' % (fake_contact_id,
                                                              self.invoice_id))
        self.assert200(status)
        self.assertEqual(response['person'], str(fake_contact_id))
        self.assertEqual(response['_id'], self.invoice_id)

    def test_getitem_ifmatch_disabled(self):
        # when IF_MATCH is disabled no etag is present in payload
        self.app.config['IF_MATCH'] = False
        response, _ = self.get(self.known_resource, item=self.item_id)
        self.assertTrue(self.app.config['ETAG'] not in response)

    def test_getitem_ifmatch_disabled_if_mod_since(self):
        # Test that #239 is fixed.
        # IF_MATCH is disabled and If-Modified-Since request comes through. If
        # a 304 was expected, we would crash like a mofo.
        self.app.config['IF_MATCH'] = False

        # IMS needs to see as recent as possible since the test db has just
        # been built
        header = [("If-Modified-Since", date_to_str(datetime.now()))]

        r = self.test_client.get(self.item_id_url, headers=header)
        self.assert304(r.status_code)

    def test_getitem_custom_auto_document_fields(self):
        self.app.config['LAST_UPDATED'] = '_updated_on'
        self.app.config['DATE_CREATED'] = '_created_on'
        self.app.config['ETAG'] = '_the_etag'
        response, _ = self.get(self.known_resource, item=self.item_id)
        self.assertTrue('_updated_on' in response)
        self.assertTrue('_created_on' in response)
        self.assertTrue('_the_etag' in response)


class TestHead(TestBase):

    def test_head_home(self):
        self.assertHead('/')

    def test_head_resource(self):
        self.assertHead(self.known_resource_url)

    def test_head_item(self):
        self.assertHead(self.item_id_url)

    def assertHead(self, url):
        h = self.test_client.head('/')
        r = self.test_client.get('/')
        self.assertTrue(not h.data)
        self.assertEqual(r.headers, h.headers)
