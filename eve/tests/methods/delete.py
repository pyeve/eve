from eve.tests import TestBase


class TestDelete(TestBase):
    def test_unknown_resource(self):
        url = '%s%s/' % (self.unknown_resource_url, self.item_id)
        r, status = self.delete(url)
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
        r, status = self.delete(url)
        self.assert404(status)

    def test_delete_readonly_resource(self):
        r, status = self.delete(self.readonly_id_url)
        self.assert405(status)

    def test_delete_unknown_item(self):
        url = '%s%s/' % (self.known_resource_url, self.unknown_item_id)
        r, status = self.delete(url)
        self.assert404(status)

    def test_delete_ifmatch_missing(self):
        r, status = self.delete(self.item_id_url)
        self.assert403(status)

    def test_delete_ifmatch_bad_etag(self):
        r, status = self.delete(self.item_id_url,
                                headers=[('If-Match', 'not-quite-right')])
        self.assert412(status)

    def test_delete(self):
        r, status = self.delete(self.item_id_url,
                                headers=[('If-Match', self.item_etag)])
        self.assert200(status)

        r = self.test_client.get(self.item_id_url)
        self.assert404(r.status_code)

    def test_delete_different_resource(self):
        r, status = self.delete(self.user_id_url,
                                headers=[('If-Match', self.user_etag)])
        self.assert200(status)

        r = self.test_client.get(self.user_id_url)
        self.assert404(r.status_code)

    def delete(self, url, headers=None):
        r = self.test_client.delete(url, headers=headers)
        return self.parse_response(r)
