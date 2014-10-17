import simplejson as json
from datetime import datetime
from eve.tests.utils import DummyEvent
from eve.tests import TestBaseSQL
from eve.utils import date_to_str, str_to_date


class TestGetSQL(TestBaseSQL):

    def test_get_empty_resource(self):
        response, status = self.get(self.empty_resource)
        self.assert404(status)

    def test_get_page(self):
        response, status = self.get(self.known_resource)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 2)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 1, 101, 25)

        page = 1
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 2)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 1, 101, 25)

        page = 2
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 2, 101, 25)

        page = 5
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertPrevLink(links, 4)
        self.assertLastLink(links, None)
        self.assertPagination(response, 5, 101, 25)

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

    def test_get_paging_disabled(self):
        self.app.config['DOMAIN'][self.known_resource]['pagination'] = False
        response, status = self.get(self.known_resource, '?page=2')
        self.assert200(status)
        resource = response['_items']
        self.assertFalse(len(resource) ==
                         self.app.config['PAGINATION_DEFAULT'])
        self.assertTrue(self.app.config['META'] not in response)
        links = response['_links']
        self.assertTrue('next' not in links)
        self.assertTrue('prev' not in links)

    def test_get_paging_disabled_no_args(self):
        self.app.config['DOMAIN'][self.known_resource]['pagination'] = False
        response, status = self.get(self.known_resource)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.known_resource_count)
        self.assertTrue(self.app.config['META'] not in response)
        links = response['_links']
        self.assertTrue('next' not in links)
        self.assertTrue('prev' not in links)

    def test_get_projection(self):
        projection = '{"firstname": 1}'
        response, status = self.get(self.known_resource, '?projection=%s' %
                                    projection)
        self.assert200(status)

        resource = response['_items']

        for r in resource:
            self.assertFalse('lastname' in r)
            self.assertFalse('fullname' in r)
            self.assertTrue('firstname' in r)
            self.assertTrue(self.app.config['ID_FIELD'] in r)
            self.assertTrue(self.app.config['ETAG'] in r)
            self.assertTrue(self.app.config['LAST_UPDATED'] in r)
            self.assertTrue(self.app.config['DATE_CREATED'] in r)
            self.assertTrue(r[self.app.config['LAST_UPDATED']] != self.epoch)
            self.assertTrue(r[self.app.config['DATE_CREATED']] != self.epoch)

        projection = '{"firstname": 0}'
        response, status = self.get(self.known_resource, '?projection=%s' %
                                    projection)
        self.assert200(status)

        resource = response['_items']

        for r in resource:
            self.assertFalse('firstname' in r)
            self.assertTrue('lastname' in r)
            self.assertTrue('fullname' in r)
            self.assertTrue(self.app.config['ID_FIELD'] in r)
            self.assertTrue(self.app.config['ETAG'] in r)
            self.assertTrue(self.app.config['LAST_UPDATED'] in r)
            self.assertTrue(self.app.config['DATE_CREATED'] in r)
            self.assertTrue(r[self.app.config['LAST_UPDATED']] != self.epoch)
            self.assertTrue(r[self.app.config['DATE_CREATED']] != self.epoch)

    def test_get_projection_noschema(self):
        self.app.config['DOMAIN'][self.known_resource]['schema'] = {}
        response, status = self.get(self.known_resource)
        self.assert200(status)

        resource = response['_items']

        # fields are returned anyway since no schema = return all fields
        for r in resource:
            self.assertTrue('firstname' in r)
            self.assertTrue('lastname' in r)
            self.assertTrue('fullname' in r)
            self.assertTrue(self.app.config['ID_FIELD'] in r)
            self.assertTrue(self.app.config['LAST_UPDATED'] in r)
            self.assertTrue(self.app.config['DATE_CREATED'] in r)

    def test_get_where_disabled(self):
        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = []
        where = 'firstname == %s' % self.item_firstname
        response, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_DEFAULT'])

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

#    why it should be 304?
#    def test_get_if_modified_since(self):
#        self.assertIfModifiedSince(self.known_resource_url)

    def test_cache_control(self):
        self.assertCacheControl(self.known_resource_url)

    def test_expires(self):
        self.assertExpires(self.known_resource_url)

    def test_get(self):
        response, status = self.get(self.known_resource)
        self.assert_get(response, status)

    def assert_get(self, response, status, resource=None):
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

    def test_get_where_allowed_filters(self):
        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = \
            ['notreally']
        where = '{"firstname": "%s"}' % self.item_firstname
        r = self.test_client.get('%s%s' % (self.known_resource_url,
                                           '?where=%s' % where))
        self.assert400(r.status_code)
        self.assertTrue(b"'firstname' not allowed" in r.get_data())

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
        self.assert_get(response, status)

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

    def test_get_nested_resource(self):
        response, status = self.get('users/overseas')
        self.assert_get(response, status, 'users_overseas')

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

    def test_get_idfield_doesnt_exist(self):
        # test that a non-existing ID_FIELD will be silently handled when
        # building HATEOAS document link (#351).
        self.app.config['ID_FIELD'] = 'id'
        response, status = self.get(self.known_resource)
        self.assert200(status)

    def test_get_invalid_idfield_cors(self):
        """ test that #381 is fixed. """
        request = '/%s/badid' % self.known_resource
        self.app.config['X_DOMAINS'] = '*'
        r = self.test_client.get(request, headers=[('Origin', 'test.com')])
        self.assert404(r.status_code)

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
        self.assertEqual(len(resource), 5)

        for item in resource:
            # 'user' title instead of original 'contact'
            self.assertItem(item)

        etag = item.get(self.app.config['ETAG'])
        self.assertTrue(etag is not None)

    def test_documents_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        _db = self.app.data.driver
        firstname = 'Douglas'
        person = self.test_sql_tables.People(firstname=firstname,
                                             lastname='Adams', prog=1)
        _db.session.add(person)
        _db.session.flush()
        where = '{"firstname": "%s"}' % firstname
        response, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), 1)
        self.assertItem(resource[0])

        _db.session.rollback()

    def test_get_embedded(self):
        _db = self.app.data.driver

        # create random person
        fake_person = self.test_sql_tables.People.\
            from_tuple(self.random_people(1)[0])
        fake_person._created = datetime.now()
        fake_person._updated = datetime.now()
        _db.session.add(fake_person)
        _db.session.flush()
        fake_invoice = self.test_sql_tables.Invoices(number=4)
        fake_invoice.people_id = fake_person._id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.flush()

        invoices = self.domain['invoices']

        # Test that we get 400 if can't parse dict
        embedded = 'not-a-dict'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert400(r.status_code)

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is False by default)
        embedded = '{"people": 1}'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['people_id'], self.item_id)

        # Set field to be embedded
        invoices['schema']['people']['data_relation']['embeddable'] = True

        # Test that it works
        invoices['embedding'] = True
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        # Test that it ignores a bogus field
        embedded = '{"people": 1, "not-a-real-field": 1}'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        # Test that it ignores a real field with a bogus value
        embedded = '{"people": 1, "number": "not-a-real-value"}'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        # Test that it works with item endpoint too
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people_id' in content)

        _db.session.rollback()

    def test_get_default_embedding(self):
        _db = self.app.data.driver

        # create random person
        fake_person = self.test_sql_tables.People.\
            from_tuple(self.random_people(1)[0])
        fake_person._created = datetime.now()
        fake_person._updated = datetime.now()
        _db.session.add(fake_person)
        _db.session.flush()
        fake_invoice = self.test_sql_tables.Invoices(number=4)
        fake_invoice.person_id = fake_person._id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.flush()

        invoices = self.domain['invoices']

        # Turn default field embedding on
        invoices['embedded_fields'] = ['people']

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is False by default)
        r = self.test_client.get(invoices['url'])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['people_id'], self.item_id)

        # Set field to be embedded
        invoices['schema']['people']['data_relation']['embeddable'] = True

        # Test that global setting applies even if field is set to embedded
        invoices['embedding'] = False
        r = self.test_client.get(invoices['url'])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['people_id'], self.item_id)

        # Test that it works
        invoices['embedding'] = True
        r = self.test_client.get('{0}?embedded={{"people": 1}}'.
                                 format(invoices['url']))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        # Test that it ignores a bogus field
        invoices['embedded_fields'] = ['people', 'not-really']
        r = self.test_client.get('{0}?embedded={{"people": 1}}'.
                                 format(invoices['url']))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        _db.session.rollback()

    def test_cursor_extra_find(self):
        _find = self.app.data.find
        hits = {'total_hits': 0}

        def find(resource, req, sub_resource_lookup):
            def extra(response):
                response['_hits'] = hits
            cursor = _find(resource, req, sub_resource_lookup)
            cursor.extra = extra
            return cursor

        self.app.data.find = find
        r, status = self.get(self.known_resource)
        self.assert200(status)
        self.assertTrue('_hits' in r)
        self.assertEqual(r['_hits'], hits)

    def test_get_subresource(self):
        _db = self.app.data.driver

        # create random person
        fake_person = self.test_sql_tables.People.\
            from_tuple(self.random_people(1)[0])
        fake_person._created = datetime.now()
        fake_person._updated = datetime.now()
        _db.session.add(fake_person)
        _db.session.flush()
        fake_invoice = self.test_sql_tables.Invoices(number=4)
        fake_invoice.people_id = fake_person._id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.flush()

        # GET all invoices by new contact
        response, status = self.get('users/%s/invoices' % fake_person._id)
        self.assert200(status)
        # only 2 invoices
        self.assertEqual(len(response['_items']), 2)
        self.assertEqual(len(response['_links']), 2)
        # which links to the right contact
        self.assertEqual(response['_items'][1]['people']['_id'],
                         fake_person._id)

        _db.session.rollback()


class TestGetItem(TestBaseSQL):

    def assert_item_response(self, response, status,
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
        self.assert_item_response(response, status)

        response, status = self.get(self.known_resource,
                                    item=self.unknown_item_id)
        self.assert404(status)

    def test_getitem_noschema(self):
        self.app.config['DOMAIN'][self.known_resource]['schema'] = {}
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assert_item_response(response, status)

    def test_getitem_by_name(self):
        response, status = self.get(self.known_resource,
                                    item=self.item_firstname)
        self.assert_item_response(response, status)
        response, status = self.get(self.known_resource,
                                    item=self.unknown_item_name)
        self.assert404(status)

    def test_getitem_by_name_self_href(self):
        response, status = self.get(self.known_resource,
                                    item=self.item_id)
        self_href = response['_links']['self']['href']

        response, status = self.get(self.known_resource,
                                    item=self.item_firstname)

        self.assertEqual(self_href, response['_links']['self']['href'])

    def test_getitem_by_integer(self):
        self.domain[self.known_resource]['additional_lookup'] = {
            'field': 'prog'
        }
        self.app._add_resource_url_rules(self.known_resource,
                                         self.domain[self.known_resource])
        response, status = self.get(self.known_resource,
                                    item=1)
        self.assert_item_response(response, status)
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

    def test_get_with_post_override(self):
        # POST request with GET override turns into a GET
        headers = [('X-HTTP-Method-Override', 'GET')]
        r = self.test_client.post(self.item_id_url, headers=headers)
        response, status = self.parse_response(r)
        self.assert_item_response(response, status)

    def test_getitem_projection(self):
        projection = '{"prog": 1}'
        r, status = self.get(self.known_resource, '?projection=%s' %
                             projection, item=self.item_id)
        self.assert200(status)
        self.assertFalse('firstname' in r)
        self.assertFalse('lastname' in r)
        self.assertTrue('prog' in r)
        self.assertTrue(self.app.config['ID_FIELD'] in r)
        self.assertTrue(self.app.config['ETAG'] in r)
        self.assertTrue(self.app.config['LAST_UPDATED'] in r)
        self.assertTrue(self.app.config['DATE_CREATED'] in r)
        self.assertTrue(r[self.app.config['LAST_UPDATED']] != self.epoch)
        self.assertTrue(r[self.app.config['DATE_CREATED']] != self.epoch)

        projection = '{"prog": 0}'
        r, status = self.get(self.known_resource, '?projection=%s' %
                             projection, item=self.item_id)
        self.assert200(status)
        self.assertFalse('prog' in r)
        self.assertTrue('firstname' in r)
        self.assertTrue('lastname' in r)
        self.assertTrue(self.app.config['ID_FIELD'] in r)
        self.assertTrue(self.app.config['ETAG'] in r)
        self.assertTrue(self.app.config['LAST_UPDATED'] in r)
        self.assertTrue(self.app.config['DATE_CREATED'] in r)
        self.assertTrue(r[self.app.config['LAST_UPDATED']] != self.epoch)
        self.assertTrue(r[self.app.config['DATE_CREATED']] != self.epoch)

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

    def test_getitem_by_id_different_resource(self):
        response, status = self.get(self.different_resource,
                                    item=self.user_id)
        self.assert_item_response(response, status, self.different_resource)

        # I'm not really sure this apply to SQL DBs
        # response, status = self.get(self.different_resource,
        #                             item=self.item_id)
        # self.assert404(status)

    def test_getitem_by_name_different_resource(self):
        response, status = self.get(self.different_resource,
                                    item=self.user_firstname)
        self.assert_item_response(response, status, self.different_resource)
        response, status = self.get(self.different_resource,
                                    item=self.unknown_item_name)
        self.assert404(status)

    def test_getitem_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        _db = self.app.data.driver
        firstname = 'Douglas'
        person = self.test_sql_tables.People(firstname=firstname,
                                             lastname='Adams', prog=1)
        _db.session.add(person)
        _db.session.flush()
        response, status = self.get(self.known_resource, item=firstname)
        self.assert_item_response(response, status)

        _db.session.rollback()

    def test_getitem_embedded(self):
        _db = self.app.data.driver

        # create random person
        fake_person = self.test_sql_tables.People.\
            from_tuple(self.random_people(1)[0])
        _db.session.add(fake_person)
        _db.session.flush()
        fake_person_id = fake_person._id
        fake_invoice = self.test_sql_tables.Invoices(number=4)
        fake_invoice.people_id = fake_person_id
        _db.session.add(fake_invoice)
        _db.session.flush()

        invoices = self.domain['invoices']

        # Test that we get 400 if can't parse dict
        embedded = 'not-a-dict'
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert400(r.status_code)

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is True by default)
        embedded = '{"people": 1}'
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['people_id'], self.item_id)

        # Set field to be embedded
        invoices['schema']['people']['data_relation']['embeddable'] = True

        # Test that global setting applies even if field is set to embedded
        invoices['embedding'] = True
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['people_id'], self.item_id)

        # Test that it works
        invoices['embedding'] = True
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content)

        # Test that it ignores a bogus field
        embedded = '{"people": 1, "not-a-real-field": 1}'
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content)

        # Test that it ignores a real field with a bogus value
        embedded = '{"people": 1, "number": "not-a-real-value"}'
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content)

        # Test that it works with item endpoint too
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content)

        _db.session.rollback()

    def test_subresource_getitem(self):
        _db = self.app.data.driver

        # create random person
        fake_person = self.test_sql_tables.People.\
            from_tuple(self.random_people(1)[0])
        fake_person._created = datetime.now()
        fake_person._updated = datetime.now()
        _db.session.add(fake_person)
        _db.session.flush()
        fake_invoice = self.test_sql_tables.Invoices(number=4)
        fake_invoice.people_id = fake_person._id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.flush()

        # GET all invoices by new contact
        response, status = self.get('users/%s/invoices/%s' %
                                    (fake_person._id, fake_invoice._id))
        self.assert200(status)
        self.assertEqual(response['people']['_id'], fake_person._id)
        self.assertEqual(response['_id'], fake_invoice._id)

        _db.session.rollback()


class TestHead(TestBaseSQL):

    def test_head_home(self):
        self.assert_head('/')

    def test_head_resource(self):
        self.assert_head(self.known_resource_url)

    def test_head_item(self):
        self.assert_head(self.item_id_url)

    def assert_head(self, url):
        h = self.test_client.head(url)
        r = self.test_client.get(url)
        self.assertTrue(not h.data)

        if 'Expires' in r.headers:
            # there's a tiny chance that the two expire values will differ by
            # one second. See #316.
            head_expire = str_to_date(r.headers.pop('Expires'))
            get_expire = str_to_date(h.headers.pop('Expires'))
            d = head_expire - get_expire
            self.assertTrue(d.seconds in (0, 1))

        self.assertEqual(r.headers, h.headers)


class TestEvents(TestBaseSQL):

    def setUp(self):
        super(TestEvents, self).setUp()
        self.devent = DummyEvent(lambda: True)

    def test_on_pre_GET_for_item(self):
        self.app.on_pre_GET += self.devent
        self.get_item()
        self.assertEqual('people', self.devent.called[0])
        self.assertFalse(self.devent.called[1] is None)

    def test_on_pre_GET_item_dynamic_filter(self):
        def filter_this(resource, request, lookup):
            lookup["_id"] = self.item_id
        self.app.on_pre_GET += filter_this
        # Would normally return a 404; will return one instead.
        r, s = self.parse_response(self.get_item())
        self.assert200(s)
        self.assertEqual(r[self.app.config['ID_FIELD']], self.item_id)

    def test_on_pre_GET_resource_for_item(self):
        self.app.on_pre_GET_people += self.devent
        self.get_item()
        self.assertFalse(self.devent.called is None)

    def test_on_pre_GET_for_resource(self):
        self.app.on_pre_GET += self.devent
        self.get_resource()
        self.assertFalse(self.devent.called is None)

    def test_on_pre_GET_resource_dynamic_filter(self):
        def filter_this(resource, request, lookup):
            lookup["_id"] = self.item_id
        self.app.on_pre_GET += filter_this
        # Would normally return all documents; will only just one.
        r, s = self.parse_response(self.get_resource())
        self.assertEqual(len(r[self.app.config['ITEMS']]), 1)

    def test_on_pre_GET_resource_for_resource(self):
        self.app.on_pre_GET_people += self.devent
        self.get_resource()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_for_item(self):
        self.app.on_post_GET += self.devent
        self.get_item()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_resource_for_item(self):
        self.app.on_post_GET_people += self.devent
        self.get_item()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_for_resource(self):
        self.app.on_post_GET += self.devent
        self.get_resource()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_resource_for_resource(self):
        self.app.on_post_GET_people += self.devent
        self.get_resource()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_homepage(self):
        self.app.on_post_GET += self.devent
        self.test_client.get('/')
        self.assertTrue(self.devent.called[0] is None)
        self.assertEqual(3, len(self.devent.called))

    def test_on_fetched_resource(self):
        self.app.on_fetched_resource += self.devent
        self.get_resource()
        self.assertEqual('people', self.devent.called[0])
        self.assertEqual(
            self.app.config['PAGINATION_DEFAULT'],
            len(self.devent.called[1][self.app.config['ITEMS']]))

    def test_on_fetched_resource_people(self):
        self.app.on_fetched_resource_people += self.devent
        self.get_resource()
        self.assertEqual(
            self.app.config['PAGINATION_DEFAULT'],
            len(self.devent.called[0][self.app.config['ITEMS']]))

    def test_on_fetched_item(self):
        self.app.on_fetched_item += self.devent
        self.get_item()
        self.assertEqual('people', self.devent.called[0])
        self.assertEqual(self.item_id,
                         self.devent.called[1][self.app.config['ID_FIELD']])
        self.assertEqual(2, len(self.devent.called))

    def test_on_fetched_item_contacts(self):
        self.app.on_fetched_item_people += self.devent
        self.get_item()
        self.assertEqual(self.item_id,
                         self.devent.called[0][self.app.config['ID_FIELD']])
        self.assertEqual(1, len(self.devent.called))

    def get_item(self, url=None):
        if not url:
            url = self.item_id_url
        return self.test_client.get(url)

    def get_resource(self):
        return self.test_client.get(self.known_resource_url)
