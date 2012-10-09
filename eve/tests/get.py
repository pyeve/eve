from eva.tests import TestMethodsBase
#import time
#import flask

# TODO update/complete when we have a reliable set of test data


class TestGet(TestMethodsBase):

    def test_get_empty_resource(self):
        response, status = self.response(self.empty_resource)
        self.assert200(status)

        resource = response[self.empty_resource]
        self.assertEqual(len(resource), 0)

        links = response['links']
        self.assertEqual(len(links), 2)
        self.assertHomeLink(links)

    def test_get_max_results(self):
        maxr = 10
        response, status = self.response(self.known_resource,
                                         '?max_results=%d' % maxr)
        self.assert200(status)

        resource = response[self.known_resource]
        self.assertEqual(len(resource), maxr)

        maxr = self.app.config['PAGING_LIMIT'] + 1
        response, status = self.response(self.known_resource,
                                         '?max_results=%d' % maxr)
        self.assert200(status)

        resource = response[self.known_resource]
        self.assertEqual(len(resource), self.app.config['PAGING_LIMIT'])

    def test_get_page(self):
        response, status = self.response(self.known_resource)
        self.assert200(status)

        links = response['links']
        self.assertNextLink(links, 2)

        page = 1
        response, status = self.response(self.known_resource,
                                         '?page=%d' % page)
        self.assert200(status)

        links = response['links']
        self.assertNextLink(links, 2)

        page = 2
        response, status = self.response(self.known_resource,
                                         '?page=%d' % page)
        self.assert200(status)

        links = response['links']
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)

        page = 3
        response, status = self.response(self.known_resource,
                                         '?page=%d' % page)
        self.assert200(status)

        links = response['links']
        self.assertNextLink(links, 4)
        self.assertPrevLink(links, 2)

    def test_get_where_mongo_syntax(self):
        where = '{"name": "anna"}'
        response, status = self.response(self.known_resource,
                                         '?where=%s' % where)
        self.assert200(status)

        resource = response[self.known_resource]
        self.assertEqual(len(resource), 7)

    def test_get_sort_mongo_syntax(self):
        # TODO complete when we have a proper set of testing data(db)
        sort = '[("name",1)]'
        response, status = self.response(self.known_resource,
                                         '?sort=%s' % sort)
        self.assert200(status)

        resource = response[self.known_resource]
        self.assertEqual(len(resource), 25)     # should test 1st item match

    def test_get_if_modified_since(self):
        resource = '/%s/' % self.domain[self.known_resource]['url']
        self.assertIfModifiedSince(resource)

    def test_cache_control(self):
        resource = '/%s/' % self.domain[self.known_resource]['url']
        self.assertCacheControl(resource)

    def test_expires(self):
        resource = '/%s/' % self.domain[self.known_resource]['url']
        self.assertExpires(resource)

    def test_get(self):
        response, status = self.response(self.known_resource)
        self.assert200(status)

        links = response['links']
        self.assertEqual(len(links), 3)
        self.assertHomeLink(links)
        self.assertResourceLink(links, self.known_resource)
        self.assertNextLink(links, 2)

        resource = response[self.known_resource]
        self.assertEqual(len(resource), self.app.config['PAGING_DEFAULT'])

        # TODO should we iterate all the items? Guess not (performance)
        item = resource[0]
        self.assertItem(item)

        # TODO figure a way to test etag match. Even removing the etag field
        # itself won't help since the 'item' dict is unordered (and therefore
        # doesn't match the original representation)
        etag = item.get('etag')
        self.assertTrue(etag is not None)


class TestGetItem(TestMethodsBase):

    def assertItemResponse(self, response, status):
        self.assert200(status)
        self.assertEqual(len(response), 2)

        links = response['links']
        self.assertEqual(len(links), 2)
        self.assertHomeLink(links)
        self.assertResourceLink(links, self.known_resource)

        item = response.get(self.known_resource)
        self.assertItem(item)

    def test_getitem_by_id(self):
        response, status = self.response(self.known_resource,
                                         item=self.known_item_by_id)
        self.assertItemResponse(response, status)

    def test_getitem_by_name(self):
        response, status = self.response(self.known_resource,
                                         item=self.known_item_by_name)
        self.assertItemResponse(response, status)

    def test_getitem_if_modified_since(self):
        resource = '/%s/%s/' % (self.domain[self.known_resource]['url'],
                                self.known_item_by_id)
        self.assertIfModifiedSince(resource)

    def test_getitem_if_none_match(self):
        resource = '/%s/%s/' % (self.domain[self.known_resource]['url'],
                                self.known_item_by_id)
        r = self.test_client.get(resource)

        etag = r.headers.get('ETag')
        self.assertTrue(etag is not None)
        r = self.test_client.get(resource, headers=[('If-None-Match', etag)])
        self.assert304(r.status_code)
        self.assertEqual(r.data, '')

    def test_cache_control(self):
        resource = '/%s/%s/' % (self.domain[self.known_resource]['url'],
                                self.known_item_by_id)
        self.assertCacheControl(resource)

    def test_expires(self):
        resource = '/%s/' % self.domain[self.known_resource]['url']
        self.assertExpires(resource)
