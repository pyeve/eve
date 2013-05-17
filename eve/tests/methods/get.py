from eve.tests import TestBase
from eve.tests.test_settings import MONGO_DBNAME


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

        page = 1
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 2)

        page = 2
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)

        page = 3
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 4)
        self.assertPrevLink(links, 2)

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

    def test_get_mongo_query_blacklist(self):
        where = '{"$where": "this.ref == ''%s''"}' % self.item_name
        response, status = self.get(self.known_resource,
                                    '?where=%s' % where)
        self.assert400(status)

        where = '{"ref": {"$regex": "%s"}}' % self.item_name
        response, status = self.get(self.known_resource,
                                    '?where=%s' % where)
        self.assert400(status)

    # TODO need more tests here, to verify that the parser is behaving
    # correctly
    def test_get_where_python_syntax(self):
        where = 'ref == %s' % self.item_name
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

    def test_get_where_disabled(self):
        self.app.config['DOMAIN'][self.known_resource]['filters'] = False
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
        topvalue = 99
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

    def test_get_if_modified_since(self):
        self.assertIfModifiedSince(self.known_resource_url)

    def test_cache_control(self):
        self.assertCacheControl(self.known_resource_url)

    def test_expires(self):
        self.assertExpires(self.known_resource_url)

    def test_get(self):
        response, status = self.get(self.known_resource)
        self.assert200(status)

        links = response['_links']
        self.assertEqual(len(links), 3)
        self.assertHomeLink(links)
        self.assertResourceLink(links, self.known_resource)
        self.assertNextLink(links, 2)

        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_DEFAULT'])

        for item in resource:
            self.assertItem(item)

        etag = item.get('etag')
        self.assertTrue(etag is not None)
        # TODO figure a way to test etag match. Even removing the etag field
        # itself won't help since the 'item' dict is unordered (and therefore
        # doesn't match the original representation)
        #del(item['etag'])
        #self.assertEqual(hashlib.sha1(str(item)).hexdigest(), etag)

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

        etag = item.get('etag')
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


class TestGetItem(TestBase):

    def assertItemResponse(self, response, status,
                           resource=None):
        self.assert200(status)
        self.assertTrue('etag' in response)
        links = response['_links']
        self.assertEqual(len(links), 3)
        self.assertHomeLink(links)
        self.assertCollectionLink(links, resource or self.known_resource)
        self.assertItem(response)

    def test_disallowed_getitem(self):
        response, status = self.get(self.empty_resource,
                                    item=self.item_id)
        self.assert404(status)

    def test_getitem_by_id(self):
        response, status = self.get(self.known_resource,
                                    item=self.item_id)
        self.assertItemResponse(response, status)

        response, status = self.get(self.known_resource,
                                    item=self.unknown_item_id)
        self.assert404(status)

    def test_getitem_by_name(self):
        response, status = self.get(self.known_resource,
                                    item=self.item_name)
        self.assertItemResponse(response, status)
        response, status = self.get(self.known_resource,
                                    item=self.unknown_item_name)
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
        self.assertEqual(r.data, '')

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
                                    item=self.user_name)
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
        response, status = self.get(self.known_resource,
                                    item=ref)
        self.assertItemResponse(response, status)


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
        self.assertEqual(h.data, '')
        self.assertEqual(r.headers, h.headers)
