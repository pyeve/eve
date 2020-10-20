import base64
import time
from io import BytesIO
import simplejson as json
from datetime import datetime, timedelta
from bson import ObjectId
from bson.dbref import DBRef
from bson.son import SON
from werkzeug.datastructures import ImmutableMultiDict, MultiDict
from eve.tests import TestBase
from eve.tests.utils import DummyEvent
from eve.tests.test_settings import MONGO_DBNAME
from eve.utils import str_to_date, date_to_rfc1123
from eve.methods.get import get_internal, getitem_internal


class TestGet(TestBase):
    def test_get_empty_resource(self):
        response, status = self.get(self.empty_resource)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), 0)

        links = response["_links"]
        self.assertEqual(len(links), 2)
        self.assertResourceLink(links, self.empty_resource)
        self.assertHomeLink(links)

    def test_get_max_results(self):
        maxr = 10
        response, status = self.get(self.known_resource, "?max_results=%d" % maxr)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), maxr)

        maxr = self.app.config["PAGINATION_LIMIT"] + 1
        response, status = self.get(self.known_resource, "?max_results=%d" % maxr)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), self.app.config["PAGINATION_LIMIT"])

    def test_get_custom_max_results(self):
        self.app.config["QUERY_MAX_RESULTS"] = "size"
        maxr = 10
        response, status = self.get(self.known_resource, "?size=%d" % maxr)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), maxr)

    def test_get_custom_params(self):
        page = 2
        custom_params = MultiDict([("my_param", "value1"), ("my_param", "value2")])
        custom_query = "&".join(
            "%s=%s" % (param, value)
            for param, values in custom_params.lists()
            for value in values
        )
        response, status = self.get(
            self.known_resource, "?%s&page=%d" % (custom_query, page)
        )
        self.assert200(status)

        links = response["_links"]
        self.assertCustomParams(links["prev"], custom_params)
        self.assertCustomParams(links["next"], custom_params)
        self.assertCustomParams(links["self"], custom_params)
        self.assertCustomParams(links["last"], custom_params)

    def test_get_page(self):
        response, status = self.get(self.known_resource)
        self.assert200(status)
        self.assertPage(response, status)

    def test_get_perform_count_on_pagination_disabled(self):
        self.app.config["OPTIMIZE_PAGINATION_FOR_SPEED"] = True

        r = self.test_client.get("%s?page=2" % self.known_resource_url)
        self.assert200(r.status_code)

        body = json.loads(r.get_data())
        links = body["_links"]
        self.assertFalse("last" in links)
        self.assertFalse("total" in body["_meta"])
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)
        self.assertFalse(self.app.config["HEADER_TOTAL_COUNT"] in r.headers)

    def test_get_internal_page(self):
        with self.app.test_request_context(self.known_resource_url):
            response, _, _, status, _ = get_internal(self.known_resource)
        self.assertPage(response, status)

    def assertPage(self, response, status):
        links = response["_links"]
        self.assertNextLink(links, 2)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 1, 101, 25)

        page = 1
        response, status = self.get(self.known_resource, "?page=%d" % page)
        self.assert200(status)

        links = response["_links"]
        self.assertNextLink(links, 2)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 1, 101, 25)

        page = 2
        response, status = self.get(self.known_resource, "?page=%d" % page)
        self.assert200(status)

        links = response["_links"]
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 2, 101, 25)

        page = 5
        response, status = self.get(self.known_resource, "?page=%d" % page)
        self.assert200(status)

        links = response["_links"]
        self.assertPrevLink(links, 4)
        self.assertLastLink(links, None)
        self.assertPagination(response, 5, 101, 25)

    def test_get_custom_page(self):
        self.app.config["QUERY_PAGE"] = "custom"

        page = 2
        response, status = self.get(self.known_resource, "?custom=%d" % page)
        self.assert200(status)

        links = response["_links"]
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 2, 101, 25)

    def test_get_pagination_no_documents(self):
        """test that pagination meta is present even when no records are being
        returned. #415.
        """
        response, status = self.get(self.known_resource, '?where={"ref": "not_really"}')
        self.assert200(status)
        self.assertPagination(response, 1, 0, 25)

    def test_get_paging_disabled_no_args(self):
        self.app.config["DOMAIN"][self.known_resource]["pagination"] = False
        response, status = self.get(self.known_resource)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), self.known_resource_count)
        self.assertTrue(self.app.config["META"] not in response)
        links = response["_links"]
        self.assertTrue("next" not in links)
        self.assertTrue("prev" not in links)

    def test_get_total_count_header(self):
        url = self.domain[self.known_resource]["url"]
        r = self.test_client.head(url)
        response, status = self.parse_response(r)
        self.assert200(status)
        self.assertEqual(response, None)

        total_count = r.headers[self.app.config["HEADER_TOTAL_COUNT"]]
        self.assertEqual(int(total_count), self.known_resource_count)

    def test_get_total_count_header_on_empty_resource(self):
        url = self.domain[self.empty_resource]["url"]
        r = self.test_client.head(url)
        response, status = self.parse_response(r)
        self.assert200(status)
        self.assertEqual(response, None)

        self.assertIn(self.app.config["HEADER_TOTAL_COUNT"], r.headers)
        total_count = r.headers[self.app.config["HEADER_TOTAL_COUNT"]]
        self.assertEqual(int(total_count), 0)

    def test_get_where_mongo_syntax(self):
        where = '{"ref": "%s"}' % self.item_name
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), 1)

    def test_get_where_mongo_combined_date(self):
        where = (
            '{"$and": [{"ref": "%s"}, {"_created": \
                {"$gte": "Tue, 01 Oct 2013 00:59:22 GMT"}}]}'
            % self.item_name
        )
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), 1)

    def test_get_custom_where(self):
        self.app.config["QUERY_WHERE"] = "whereas"
        where = '{"ref": "%s"}' % self.item_name
        response, status = self.get(self.known_resource, "?whereas=%s" % where)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), 1)

    def test_get_mongo_query_blacklist(self):
        where = '{"$where": "this.ref == ' "%s" '"}' % self.item_name
        _, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert400(status)

        where = '{"ref": {"$regex": "%s"}}' % self.item_name
        _, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert400(status)

    def test_get_mongo_query_blacklist_nested(self):
        where = '{"$or": [{"$where": "this.ref == ' "%s" '"}]}' % self.item_name
        _, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert400(status)

        where = '{"$or": [{"ref": {"$regex": "%s"}}]}' % self.item_name
        _, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert400(status)

    def test_get_mongo_query_whitelist(self):
        where = '{"$expr": {"$eq": [{"$year": "$_created"}, 2020]}}'
        _, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert400(status)

        settings = self.app.config["DOMAIN"][self.known_resource]
        settings["mongo_query_whitelist"] = ["$year"]
        _, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)

    def test_get_mongo_query_whitelist_nested(self):
        where = '{"$or": [{"$expr": {"$eq": [{"$year": "$_created"}, 2020]}}]}'
        _, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert400(status)

        settings = self.app.config["DOMAIN"][self.known_resource]
        settings["mongo_query_whitelist"] = ["$year"]
        _, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)

    def test_get_where_mongo_objectid_as_string(self):
        where = '{"tid": "%s"}' % self.item_tid
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), 1)

        self.app.config["DOMAIN"]["contacts"]["query_objectid_as_string"] = True
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), 1)

    def test_get_where_mongo_objectid_as_string_with_nested_documents(self):
        where = '{"tid": { "$in": ["%s"]}}' % self.item_tid
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), 1)

        self.app.config["DOMAIN"]["contacts"]["query_objectid_as_string"] = True
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), 1)

    def test_get_where_mongo_objectid_as_string_but_field_is_id(self):
        skus = self.to_list_string([item["sku"] for item in self.item_rows])
        where_in = '{"tid": "%s", "rows.sku": { "$in": %s} }' % (self.item_tid, skus)
        response, status = self.get(self.known_resource, "?where=%s" % where_in)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), 0)

        self.app.config["DOMAIN"]["contacts"]["query_objectid_as_string"] = True
        response, status = self.get(self.known_resource, "?where=%s" % where_in)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), 1)

    def test_get_where_python_syntax(self):
        where = "ref == %s" % self.item_name
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), 1)

    def test_get_where_python_syntax1(self):
        where = (
            'ref == %s and _created>="Tue, 01 Oct 2013 00:59:22 GMT"' % self.item_name
        )
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), 1)

    def test_get_query_in_links(self):
        """Make sure that query strings appear in all HATEOAS links (#464)."""
        # find a role with enough results
        for role in ("agent", "client", "vendor"):
            where = "role == %s" % role
            response, _ = self.get(self.known_resource, "?where=%s" % where)
            if response["_meta"]["total"] >= self.app.config["PAGINATION_DEFAULT"] + 1:
                break
        links = response["_links"]
        total = response["_meta"]["total"]
        max_results = response["_meta"]["max_results"]
        last_page = total / max_results + (1 if total % max_results else 0)
        self.assertTrue("?where=%s" % where in links["self"]["href"])
        self.assertTrue("?where=%s" % where in links["next"]["href"])
        self.assertTrue("?where=%s" % where in links["last"]["href"])
        self.assertNextLink(links, 2)
        self.assertLastLink(links, last_page)

        page = 2
        response, _ = self.get(self.known_resource, "?where=%s&page=%d" % (where, page))
        links = response["_links"]
        self.assertTrue("?where=%s" % where in links["prev"]["href"])
        self.assertPrevLink(links, 1)

    def test_get_projection_consistent_etag(self):
        """Test that #369 is fixed and projection queries return consistent
        etags (as they are now stored along with the document).
        """
        etag_field = self.app.config["ETAG"]
        data = {"inv_number": self.random_string(10)}

        # post a new item so etag storage kicks in
        r, status = self.post(self.empty_resource_url, data=data)
        etag = r[etag_field]

        # hit the resource endpoint with a projection query
        projection = '{"prog": 1}'
        r, status = self.get(self.empty_resource, "?projection=%s" % projection)
        # compare original etag with retrieved one
        self.assertEqual(etag, r["_items"][0][etag_field])

    def test_get_projection(self):
        projection = '{"prog": 1}'
        response, status = self.get(self.known_resource, "?projection=%s" % projection)
        self.assert200(status)

        resource = response["_items"]

        for r in resource:
            self.assertFalse("location" in r)
            self.assertFalse("role" in r)
            self.assertTrue("prog" in r)
            self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
            self.assertTrue(self.app.config["ETAG"] in r)
            self.assertTrue(self.app.config["LAST_UPDATED"] in r)
            self.assertTrue(self.app.config["DATE_CREATED"] in r)
            self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
            self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

        projection = '{"prog": 0}'
        response, status = self.get(self.known_resource, "?projection=%s" % projection)
        self.assert200(status)

        resource = response["_items"]

        for r in resource:
            self.assertFalse("prog" in r)
            self.assertTrue("location" in r)
            self.assertTrue("role" in r)
            self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
            self.assertTrue(self.app.config["ETAG"] in r)
            self.assertTrue(self.app.config["LAST_UPDATED"] in r)
            self.assertTrue(self.app.config["DATE_CREATED"] in r)
            self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
            self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

    def test_get_static_projection(self):
        """ Test that static projections are honoured """
        response, status = self.get(self.different_resource)
        self.assert200(status)

        resource = response["_items"]

        # 'users' has a static inclusive projection with 'username' and 'ref'
        # fields, so other document fields should be excluded.
        for r in resource:
            self.assertFalse("location" in r)
            self.assertFalse("role" in r)
            self.assertFalse("prog" in r)
            self.assertTrue("username" in r)
            self.assertTrue("ref" in r)
            self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
            self.assertTrue(self.app.config["ETAG"] in r)
            self.assertTrue(self.app.config["LAST_UPDATED"] in r)
            self.assertTrue(self.app.config["DATE_CREATED"] in r)
            self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
            self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

    def test_get_server_include_projection_can_exclude(self):
        """Test that static projection only expose fields included
        and support client projection on these fields.
        """
        # exclude `ref` by client side
        projection = '{"ref": 0}'
        response, status = self.get(
            self.different_resource, "?projection=%s" % projection
        )
        self.assert200(status)

        resource = response["_items"]

        # 'users' has a static inclusive projection with 'username' and 'ref'
        # fields, so other document fields should be excluded.
        # and client can further exclude 'ref' or 'username'.
        for r in resource:
            self.assertFalse("location" in r)
            self.assertFalse("role" in r)
            self.assertFalse("prog" in r)
            self.assertTrue("username" in r)
            self.assertFalse("ref" in r)
            self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
            self.assertTrue(self.app.config["ETAG"] in r)
            self.assertTrue(self.app.config["LAST_UPDATED"] in r)
            self.assertTrue(self.app.config["DATE_CREATED"] in r)
            self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
            self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

    def test_get_server_include_projection_block_sniff(self):
        """Test that static projection only expose fields included
        and client projection on other fields will fail.
        """
        # shouldn't work when including `prog` (excluded) by client side
        projection = '{"prog": 1}'
        response, status = self.get(
            self.different_resource, "?projection=%s" % projection
        )
        self.assert200(status)

        resource = response["_items"]
        for r in resource:
            self.assertFalse("location" in r)
            self.assertFalse("role" in r)
            # shouldn't work
            self.assertFalse("prog" in r)
            self.assertFalse("username" in r)
            self.assertFalse("ref" in r)
            self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
            self.assertTrue(self.app.config["ETAG"] in r)
            self.assertTrue(self.app.config["LAST_UPDATED"] in r)
            self.assertTrue(self.app.config["DATE_CREATED"] in r)
            self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
            self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

    def test_get_server_exclude_projection_can_project_others(self):
        """Test that static projection expose fields other than excluded
        and support client projection on exposed fields.
        """
        projection = '{"prog": 1, "location":1}'
        response, status = self.get(
            self.different_resource_exclude, "?projection=%s" % projection
        )
        self.assert200(status)

        resource = response["_items"]

        # 'users' has a static inclusive projection with 'username' and 'ref'
        # fields, so other document fields should be excluded.
        # and client can further exclude 'ref' or 'username'.
        for r in resource:
            self.assertTrue("location" in r)
            self.assertFalse("role" in r)
            self.assertTrue("prog" in r)
            self.assertFalse("born" in r)
            self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
            self.assertTrue(self.app.config["ETAG"] in r)
            self.assertTrue(self.app.config["LAST_UPDATED"] in r)
            self.assertTrue(self.app.config["DATE_CREATED"] in r)
            self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
            self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

    def test_get_server_exlcude_projection_can_sniff(self):
        """Test that static projection expose fields other than excluded
        and client projection on excluded **will work**.
        """
        projection = '{"born": 1}'
        response, status = self.get(
            self.different_resource_exclude, "?projection=%s" % projection
        )
        self.assert200(status)

        resource = response["_items"]
        for r in resource:
            self.assertFalse("location" in r)
            self.assertFalse("role" in r)
            self.assertFalse("prog" in r)
            # should work
            self.assertTrue("born" in r)
            self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
            self.assertTrue(self.app.config["ETAG"] in r)
            self.assertTrue(self.app.config["LAST_UPDATED"] in r)
            self.assertTrue(self.app.config["DATE_CREATED"] in r)
            self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
            self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

    def test_get_custom_projection(self):
        self.app.config["QUERY_PROJECTION"] = "view"
        projection = '{"prog": 1}'
        response, status = self.get(self.known_resource, "?view=%s" % projection)
        self.assert200(status)

        resource = response["_items"]

        for r in resource:
            self.assertFalse("location" in r)
            self.assertFalse("role" in r)
            self.assertTrue("prog" in r)

    def test_get_projection_subdocument(self):
        projection = '{"location.address": 1}'
        response, status = self.get(self.known_resource, "?projection=%s" % projection)
        self.assert200(status)

        resource = response["_items"]

        for r in resource:
            self.assertTrue("location" in r)
            self.assertTrue("address" in r["location"])
            self.assertFalse("city" in r["location"])
            self.assertFalse("role" in r)
            self.assertFalse("prog" in r)
            self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
            self.assertTrue(self.app.config["ETAG"] in r)
            self.assertTrue(self.app.config["LAST_UPDATED"] in r)
            self.assertTrue(self.app.config["DATE_CREATED"] in r)
            self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
            self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

    def test_get_projection_noschema(self):
        self.app.config["DOMAIN"][self.known_resource]["schema"] = {}
        response, status = self.get(self.known_resource)
        self.assert200(status)

        resource = response["_items"]

        # fields are returned anyway since no schema = return all fields
        for r in resource:
            self.assertTrue("location" in r)
            self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
            self.assertTrue(self.app.config["LAST_UPDATED"] in r)
            self.assertTrue(self.app.config["DATE_CREATED"] in r)

    def test_get_where_disabled(self):
        self.app.config["DOMAIN"][self.known_resource]["allowed_filters"] = []
        where = "ref == %s" % self.item_name
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), self.app.config["PAGINATION_DEFAULT"])

    def test_get_sort_comma_delimited_syntax(self):
        sort = "-prog"
        response, status = self.get(self.known_resource, "?sort=%s" % sort)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), self.app.config["PAGINATION_DEFAULT"])
        topvalue = 100
        for i in range(len(resource)):
            self.assertEqual(resource[i]["prog"], topvalue - i)

    def test_get_sort_mongo_syntax(self):
        sort = '[("prog",-1)]'
        response, status = self.get(self.known_resource, "?sort=%s" % sort)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), self.app.config["PAGINATION_DEFAULT"])
        topvalue = 100
        for i in range(len(resource)):
            self.assertEqual(resource[i]["prog"], topvalue - i)

    def test_get_custom_sort(self):
        self.app.config["QUERY_SORT"] = "orderby"
        sort = '[("prog",-1)]'
        response, status = self.get(self.known_resource, "?orderby=%s" % sort)
        self.assert200(status)

        resource = response["_items"]
        self.assertEqual(len(resource), self.app.config["PAGINATION_DEFAULT"])
        topvalue = 100
        for i in range(len(resource)):
            self.assertEqual(resource[i]["prog"], topvalue - i)

    def test_get_sort_disabled(self):
        self.app.config["DOMAIN"][self.known_resource]["sorting"] = False
        sort = '[("prog",-1)]'
        response, status = self.get(self.known_resource, "?sort=%s" % sort)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), self.app.config["PAGINATION_DEFAULT"])

        # this might actually fail on very rare occurences as mongodb
        # 'natural' order is not granted to return documents in insertion order
        self.assertEqual(resource[0]["prog"], 0)

    def test_get_default_sort(self):
        s = self.app.config["DOMAIN"][self.known_resource]["datasource"]

        # set default sort to 'prog', desc.
        s["default_sort"] = [("prog", -1)]
        self.app.set_defaults()
        response, _ = self.get(self.known_resource)
        self.assertEqual(response["_items"][0]["prog"], 100)

        # set default sort to 'prog', asc.
        s["default_sort"] = [("prog", 1)]
        self.app.set_defaults()
        response, _ = self.get(self.known_resource)
        self.assertEqual(response["_items"][0]["prog"], 0)

    def test_cache_control(self):
        self.assertCacheControl(self.known_resource_url)

    def test_expires(self):
        self.assertExpires(self.known_resource_url)

    def test_get(self):
        response, status = self.get(self.known_resource)
        self.assertGet(response, status)

    def test_get_same_collection_different_resource(self):
        """the 'users' resource is actually using the same db collection as
        'contacts'. Let's verify that base filters are being applied, and
        the right amount of items/links and the correct titles etc. are being
        returned. Of course 'contacts' itself has its own base filter, which
        excludes the 'users' (those with a 'username' field).
        """
        response, status = self.get(self.different_resource)
        self.assert200(status)

        links = response["_links"]
        self.assertEqual(len(links), 2)
        self.assertHomeLink(links)
        self.assertResourceLink(links, self.different_resource)

        resource = response["_items"]
        self.assertEqual(len(resource), 2)

        for item in resource:
            # 'user' title instead of original 'contact'
            self.assertItem(item, self.different_resource)

        etag = item.get(self.app.config["ETAG"])
        self.assertTrue(etag is not None)

    def test_documents_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        contacts = self.random_contacts(1, False)
        ref = "test_update_field"
        contacts[0]["ref"] = ref
        _db = self.connection[MONGO_DBNAME]
        _db.contacts.insert_one(contacts[0])
        where = '{"ref": "%s"}' % ref
        response, status = self.get(self.known_resource, "?where=%s" % where)
        self.assert200(status)
        resource = response["_items"]
        self.assertEqual(len(resource), 1)
        self.assertItem(resource[0], self.known_resource)

    def test_get_where_allowed_filters(self):
        self.app.config["DOMAIN"][self.known_resource]["allowed_filters"] = [
            "notreally"
        ]
        where = '{"ref": "%s"}' % self.item_name
        r = self.test_client.get(
            "%s%s" % (self.known_resource_url, "?where=%s" % where)
        )
        self.assert400(r.status_code)
        self.assertTrue(b"'ref' not allowed" in r.get_data())

        self.app.config["DOMAIN"][self.known_resource]["allowed_filters"] = ["*"]
        r = self.test_client.get(
            "%s%s" % (self.known_resource_url, "?where=%s" % where)
        )
        self.assert200(r.status_code)

        # `allowed_filters` contains "rows" --> filter key "rows.price"
        # must be allowed
        self.app.config["DOMAIN"][self.known_resource]["allowed_filters"] = ["rows"]
        where = '{"rows.price": 10}'
        r = self.test_client.get(
            "%s%s" % (self.known_resource_url, "?where=%s" % where)
        )
        self.assert200(r.status_code)

        # `allowed_filters` contains "rows.price" --> filter key "rows.price"
        # must be allowed
        self.app.config["DOMAIN"][self.known_resource]["allowed_filters"] = [
            "rows.price"
        ]
        r = self.test_client.get(
            "%s%s" % (self.known_resource_url, "?where=%s" % where)
        )
        self.assert200(r.status_code)

        # `allowed_filters` contains "rows.price" --> filter key "rows"
        # must NOT be allowed
        where = '{"rows": {"sku": "value", "price": 10}}'
        r = self.test_client.get(
            "%s%s" % (self.known_resource_url, "?where=%s" % where)
        )
        self.assert400(r.status_code)
        self.assertTrue(b"'rows' not allowed" in r.get_data())

    def test_get_with_post_override(self):
        # POST request with GET override turns into a GET
        headers = [("X-HTTP-Method-Override", "GET")]
        r = self.test_client.post(self.known_resource_url, headers=headers)
        response, status = self.parse_response(r)
        self.assertGet(response, status)

    def test_get_custom_items(self):
        self.app.config["ITEMS"] = "_documents"
        response, _ = self.get(self.known_resource)
        self.assertTrue("_documents" in response and "_items" not in response)

    def test_get_custom_links(self):
        self.app.config["LINKS"] = "_navigation"
        response, _ = self.get(self.known_resource)
        self.assertTrue("_navigation" in response and "_links" not in response)

    def test_get_custom_hateoas_links(self):
        def change_links(response):
            response["_links"] = {"self": {"title": "Custom", "href": "/custom/1"}}

        self.app.on_fetched_resource_contacts += change_links

        response, _ = self.get(self.known_resource)
        self.assertTrue("Custom" in response["_links"]["self"]["title"])
        self.assertTrue("/custom/1" in response["_links"]["self"]["href"])

    def test_get_custom_auto_document_fields(self):
        self.app.config["LAST_UPDATED"] = "_updated_on"
        self.app.config["DATE_CREATED"] = "_created_on"
        self.app.config["ETAG"] = "_the_etag"
        response, _ = self.get(self.known_resource)
        for document in response["_items"]:
            self.assertTrue("_updated_on" in document)
            self.assertTrue("_created_on" in document)
            self.assertTrue("_the_etag" in document)

    def test_get_embedded_media_validate_rest_of_fields(self):
        """test multipart/form-data resource fields that are JSON
        encoded are validated correctly. #806
        """

        self.app.config["MULTIPART_FORM_FIELDS_AS_JSON"] = True
        resource_with_media = {
            "image_file": {"type": "media"},
            "some_text": {"type": "string"},
            "some_boolean": {"type": "boolean"},
            "some_number": {"type": "number"},
            "some_list": {"type": "list", "schema": {"type": "string"}},
        }
        self.app.register_resource("res_img", {"schema": resource_with_media})

        img = b"some_image"

        # fail on boolean validate
        data = {"image_file": (BytesIO(img), "test.txt"), "some_boolean": "123"}
        response, status = self.parse_response(
            self.test_client.post(
                "res_img", data=data, headers=[("Content-Type", "multipart/form-data")]
            )
        )
        self.assert422(status)

        # fail on number validattion
        data = {"image_file": (BytesIO(img), "test.txt"), "some_number": "xyz"}
        response, status = self.parse_response(
            self.test_client.post(
                "res_img", data=data, headers=[("Content-Type", "multipart/form-data")]
            )
        )
        self.assert422(status)

        # fail on list validation
        data = {"image_file": (BytesIO(img), "test.txt"), "some_list": "true"}
        response, status = self.parse_response(
            self.test_client.post(
                "res_img", data=data, headers=[("Content-Type", "multipart/form-data")]
            )
        )
        self.assert422(status)

        # validate all fields correctly
        data = {
            "image_file": (BytesIO(img), "test.txt"),
            "some_text": '"abc"',
            "some_boolean": "true",
            "some_number": "123",
            "some_list": '["abc", "xyz"]',
        }
        response, status = self.parse_response(
            self.test_client.post(
                "res_img", data=data, headers=[("Content-Type", "multipart/form-data")]
            )
        )
        self.assert201(status)
        self.app.config["MULTIPART_FORM_FIELDS_AS_JSON"] = False

    def test_get_embedded_media(self):
        """test that embeedded images are properly rendered and #305 is fixed."""

        # add a 'digital_assets' endpoint to the API
        self.app.register_resource(
            "digital_assets", {"schema": {"file": {"type": "media"}}}
        )

        # add an 'images' endpoint to the API. this will expose the embedded
        # digital assets
        images = {
            "image_file": {
                "type": "objectid",
                "data_relation": {
                    "resource": "digital_assets",
                    "field": "_id",
                    "embeddable": True,
                },
            }
        }
        self.app.register_resource("images", {"schema": images})

        # post an asset
        asset = b"a_file"
        data = {"file": (BytesIO(asset), "test.txt")}
        response, status = self.parse_response(
            self.test_client.post(
                "digital_assets",
                data=data,
                headers=[("Content-Type", "multipart/form-data")],
            )
        )
        self.assert201(status)

        # post a document to the 'images' endpoint. the document is referencing
        # the newly posted digital asset.
        data = {"image_file": ObjectId(response["_id"])}
        response, status = self.parse_response(
            self.test_client.post("images", data=data)
        )
        self.assert201(status)

        # retrieve the document from the same endpoint, requesting for the
        # digital asset to be embedded within the retrieved document
        image_id = response["_id"]
        response, status = self.parse_response(
            self.test_client.get(
                "%s/%s%s" % ("images", image_id, '?embedded={"image_file": 1}')
            )
        )
        self.assert200(status)

        # test that the embedded document contains the same data as orignially
        # posted on the digital_asset endpoint.
        returned = response["image_file"]["file"]
        # encodedstring will raise a DeprecationWarning under Python3.3, but
        # the alternative encodebytes is not available in Python 2.
        encoded = base64.b64encode(asset).decode("utf-8")
        self.assertEqual(returned, encoded)
        self.assertEqual(base64.b64decode(returned.encode()), asset)

    def test_get_embedded(self):
        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]

        fake_contact = self.random_contacts(1)[0]
        fake_contact_id = _db.contacts.insert_one(fake_contact).inserted_id
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)}, {"$set": {"person": fake_contact_id}}
        )

        invoices = self.domain["invoices"]

        # Test that we get 400 if can't parse dict
        embedded = "not-a-dict"
        r = self.test_client.get("%s/%s" % (invoices["url"], "?embedded=%s" % embedded))
        self.assert400(r.status_code)

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is False by default)
        embedded = '{"person": 1}'
        r = self.test_client.get("%s/%s" % (invoices["url"], "?embedded=%s" % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertEqual(content["_items"][0]["person"], str(fake_contact_id))

        # Set field to be embedded
        invoices["schema"]["person"]["data_relation"]["embeddable"] = True

        # Test that global setting applies even if field is set to embedded
        invoices["embedding"] = False
        r = self.test_client.get("%s/%s" % (invoices["url"], "?embedded=%s" % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertEqual(content["_items"][0]["person"], str(fake_contact_id))

        # Test that it works
        invoices["embedding"] = True
        r = self.test_client.get("%s/%s" % (invoices["url"], "?embedded=%s" % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["_items"][0]["person"])

        # Test that it ignores a bogus field
        embedded = '{"person": 1, "not-a-real-field": 1}'
        r = self.test_client.get("%s/%s" % (invoices["url"], "?embedded=%s" % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["_items"][0]["person"])

        # Test that it ignores a real field with a bogus value
        embedded = '{"person": 1, "inv_number": "not-a-real-value"}'
        r = self.test_client.get("%s/%s" % (invoices["url"], "?embedded=%s" % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["_items"][0]["person"])

        # Test that it works with item endpoint too
        r = self.test_client.get(
            "%s/%s/%s" % (invoices["url"], self.invoice_id, "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["person"])

        # Add new embeddable field to schema
        invoices["schema"]["missing-field"] = {
            "type": "objectid",
            "data_relation": {"resource": "contacts", "embeddable": True},
        }

        # Test that it ignores embeddable field that is missing from document
        embedded = '{"missing-field": 1}'
        r = self.test_client.get("%s/%s" % (invoices["url"], "?embedded=%s" % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertFalse("missing-field" in content["_items"][0])

        # Test default fields to be embedded
        invoices["embedded_fields"] = ["person"]
        r = self.test_client.get("%s/" % invoices["url"])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["_items"][0]["person"])

        # Test that default fields are overwritten by ?embedded=...0
        embedded = '{"person": 0}'
        r = self.test_client.get("%s/%s" % (invoices["url"], "?embedded=%s" % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertFalse("location" in content["_items"][0]["person"])

    def test_get_custom_embedded(self):
        self.app.config["QUERY_EMBEDDED"] = "included"
        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]

        fake_contact = self.random_contacts(1)[0]
        fake_contact_id = _db.contacts.insert_one(fake_contact).inserted_id
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)}, {"$set": {"person": fake_contact_id}}
        )

        invoices = self.domain["invoices"]
        invoices["schema"]["person"]["data_relation"]["embeddable"] = True

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is False by default)
        embedded = '{"person": 1}'
        invoices["embedding"] = True
        r = self.test_client.get("%s/%s" % (invoices["url"], "?included=%s" % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["_items"][0]["person"])

    def test_get_reference_embedded_in_subdocuments(self):
        _db = self.connection[MONGO_DBNAME]

        holding_contacts = self.random_contacts(2)
        holding_contact_ids = _db.contacts.insert_many(holding_contacts).inserted_ids
        contacts = self.random_contacts(2)
        contact_ids = _db.contacts.insert_many(contacts).inserted_ids
        holding = {
            "departments": [{"title": "managment", "members": holding_contact_ids}]
        }
        holding_id = _db.companies.insert_one(holding).inserted_id
        company = {
            "holding": holding_id,
            "departments": [{"title": "development", "members": contact_ids}],
        }
        company_id = _db.companies.insert_one(company).inserted_id
        # Add a documents with no reference that should be ignored
        _db.companies.insert_one({})
        _db.companies.insert_one({"departments": []})

        companies = self.domain["companies"]
        contact_ids = list(map(str, contact_ids))

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded ('embeddable' is False by default)
        embedded = (
            '{"departments.members": 1,'
            + ' "holding": 1, "holding.departments.members": 1}'
        )
        r = self.test_client.get(
            "%s/%s" % (companies["url"], "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertEqual(content["_items"][1]["departments"][0]["members"], contact_ids)
        # Set field to be embedded
        department_def = companies["schema"]["departments"]["schema"]
        member_def = department_def["schema"]["members"]["schema"]
        member_def["data_relation"]["embeddable"] = True
        companies["schema"]["holding"]["data_relation"]["embeddable"] = True

        # Test that global setting applies even if field is set to embedded
        companies["embedding"] = False
        r = self.test_client.get(
            "%s/%s" % (companies["url"], "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertEqual(content["_items"][1]["departments"][0]["members"], contact_ids)

        # Test that it works
        companies["embedding"] = True
        r = self.test_client.get(
            "%s/%s" % (companies["url"], "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(
            "location" in content["_items"][0]["departments"][0]["members"][0]
        )
        # Test that the second company is associated with the holding
        self.assertTrue(
            "location"
            in content["_items"][1]["holding"]["departments"][0]["members"][0]
        )

        # Test that it ignores a bogus field
        embedded = '{"departments.members": 1, "not-a-real-field": 1}'
        r = self.test_client.get(
            "%s/%s" % (companies["url"], "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(
            "location" in content["_items"][0]["departments"][0]["members"][0]
        )

        # Test that it works with item endpoint too
        embedded = '{"departments.members": 1}'
        r = self.test_client.get(
            "%s/%s/%s" % (companies["url"], company_id, "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["departments"][0]["members"][0])

        # Test default fields to be embedded
        companies["embedded_fields"] = ["departments.members"]
        r = self.test_client.get("%s/" % companies["url"])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(
            "location" in content["_items"][0]["departments"][0]["members"][0]
        )

        # Test that default fields are overwritten by ?embedded=...0
        embedded = '{"departments.members": 0}'
        r = self.test_client.get(
            "%s/%s" % (companies["url"], "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertFalse(
            "location" in content["_items"][0]["departments"][0]["members"][0]
        )

    def test_get_reference_embedded_in_subdocuments_with_nested_dicts(self):
        _db = self.connection[MONGO_DBNAME]
        cpu_brand_name = self.random_string(10)
        cpu_brand = {
            "name": cpu_brand_name,
            "address": self.random_string(30),
        }
        motherboard_brand_name = self.random_string(15)
        motherboard_brand = {
            "name": motherboard_brand_name,
            "address": self.random_string(30),
        }
        cpu_brand_id, motherboard_brand_id = _db.brands.insert_many(
            [cpu_brand, motherboard_brand]
        ).inserted_ids
        cpu_component = {
            "name": self.random_string(12),
            "price": 499,
            "brand": cpu_brand_id,
        }
        motherboard_component = {
            "name": self.random_string(18),
            "price": 199,
            "brand": motherboard_brand_id,
        }
        cpu_component_id, motherboard_component_id = _db.components.insert_many(
            [cpu_component, motherboard_component]
        ).inserted_ids
        computer = {
            "name": self.random_string(25),
            "components": {
                "cpu": cpu_component_id,
                "motherboard": motherboard_component_id,
            },
        }
        computer_id = _db.computers.insert_one(computer).inserted_id
        computers = self.domain["computers"]
        components = self.domain["components"]
        # Test that doesn't come embedded if asking for a field that
        # isn't embedded ('embeddable' is False by default)
        embedded = (
            '{"components.cpu": 1, "components.motherboard": 1,'
            + ' "components.cpu.brand": 1, "components.motherboard.brand": 1}'
        )
        result = self.test_client.get(
            "%s/%s/%s" % (computers["url"], computer_id, "?embedded=%s" % embedded)
        )
        self.assert200(result.status_code)
        content = json.loads(result.get_data())
        self.assertEqual(content["components"]["cpu"], str(cpu_component_id))
        self.assertEqual(
            content["components"]["motherboard"], str(motherboard_component_id)
        )
        # Set field to be embedded
        computers["schema"]["components"]["schema"]["cpu"]["data_relation"][
            "embeddable"
        ] = True
        computers["schema"]["components"]["schema"]["motherboard"]["data_relation"][
            "embeddable"
        ] = True
        components["schema"]["brand"]["data_relation"]["embeddable"] = True
        # Test that global setting applies even if field is set to embedded
        computers["embedding"] = False
        components["embedding"] = False
        result = self.test_client.get(
            "%s/%s/%s" % (computers["url"], computer_id, "?embedded=%s" % embedded)
        )
        self.assert200(result.status_code)
        content = json.loads(result.get_data())
        self.assertEqual(content["components"]["cpu"], str(cpu_component_id))
        self.assertEqual(
            content["components"]["motherboard"], str(motherboard_component_id)
        )
        # Test that it works
        computers["embedding"] = True
        components["embedding"] = True
        result = self.test_client.get(
            "%s/%s/%s" % (computers["url"], computer_id, "?embedded=%s" % embedded)
        )
        self.assert200(result.status_code)
        content = json.loads(result.get_data())
        self.assertEqual(
            content["components"]["cpu"]["brand"]["name"],
            cpu_brand_name,
        )
        self.assertEqual(
            content["components"]["motherboard"]["brand"]["name"],
            motherboard_brand_name,
        )

    def test_get_nested_resource(self):
        response, status = self.get("users/overseas")
        self.assertGet(response, status, "users_overseas")

    def test_cursor_extra_find(self):
        _find = self.app.data.find
        hits = {"total_hits": 0}

        def find(resource, req, sub_resource_lookup, perform_count=True):
            def extra(response):
                response["_hits"] = hits

            cursor, _ = _find(resource, req, sub_resource_lookup)
            cursor.extra = extra
            return cursor, _

        self.app.data.find = find
        r, status = self.get(self.known_resource)
        self.assert200(status)
        self.assertTrue("_hits" in r)
        self.assertEqual(r["_hits"], hits)

    def test_get_resource_title(self):
        # test that resource endpoints accepts custom titles.
        self.app.config["DOMAIN"][self.known_resource]["resource_title"] = "new title"
        response, _ = self.get(self.known_resource)
        self.assertTrue("new title" in response["_links"]["self"]["title"])
        # test that the home page accepts custom titles.
        response, _ = self.get("/")
        found = False
        for link in response["_links"]["child"]:
            if link["title"] == "new title":
                found = True
                break
        self.assertTrue(found)

    def test_get_subresource(self):
        _db = self.connection[MONGO_DBNAME]

        # create random contact
        fake_contact = self.random_contacts(1)[0]
        fake_contact_id = _db.contacts.insert_one(fake_contact).inserted_id
        # update first invoice to reference the new contact
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)}, {"$set": {"person": fake_contact_id}}
        )

        # GET all invoices by new contact
        response, status = self.get("users/%s/invoices" % fake_contact_id)
        self.assert200(status)
        # only 1 invoice
        self.assertEqual(len(response["_items"]), 1)
        self.assertEqual(len(response["_links"]), 2)
        # which links to the right contact
        self.assertEqual(response["_items"][0]["person"], str(fake_contact_id))

    def test_get_ifmatch_disabled(self):
        # when IF_MATCH is disabled no etag is present in payload
        self.app.config["IF_MATCH"] = False
        response, status = self.get(self.known_resource)
        resource = response["_items"]

        for r in resource:
            self.assertTrue(self.app.config["ETAG"] not in r)

    def test_get_ims_empty_resource(self):
        # test that a GET with a If-Modified-Since on an empty resource does
        # not trigger a 304 and returns a empty resource instead (#243).

        # get the resource and retrieve its IMS.
        r = self.test_client.get(self.known_resource_url)
        last_modified = r.headers.get("Last-Modified")

        # delete the whole resource content.
        r = self.test_client.delete(self.known_resource_url)

        # send a get with a IMS header from previous GET.
        r = self.test_client.get(
            self.known_resource_url, headers=[("If-Modified-Since", last_modified)]
        )
        self.assert200(r.status_code)
        self.assertEqual(json.loads(r.get_data())["_items"], [])

    def test_get_idfield_doesnt_exist(self):
        # test that a non-existing id field will be silently handled when
        # building HATEOAS document link (#351).
        self.domain[self.known_resource]["id_field"] = "id"
        response, status = self.get(self.known_resource)
        self.assert200(status)

    def test_get_invalid_idfield_cors(self):
        """ test that #381 is fixed. """
        request = "/%s/badid" % self.known_resource
        self.app.config["X_DOMAINS"] = "*"
        r = self.test_client.get(request, headers=[("Origin", "test.com")])
        self.assert404(r.status_code)

    def test_get_invalid_where_syntax(self):
        """ test that 'where' syntax with unknown '$' operator returns 400. """
        response, status = self.get(
            self.known_resource, '?where={"field": {"$foo": "bar"}}'
        )
        self.assert400(status)

    def test_get_invalid_sort_syntax(self):
        """ test that invalid sort syntax returns a 400 """
        response, status = self.get(self.known_resource, '?sort=[("prog":1)]')
        self.assert400(status)
        response, status = self.get(self.known_resource, '?sort="firstname"')
        self.assert400(status)

    def test_get_allowed_filters_operators(self):
        """test that supported operators are not considered invalid filters
        (#388). Also, test that nested filters are validated.
        """
        where = '?where={"$and": [{"field1": "value1"}, {"field2": "value2"}]}'
        settings = self.app.config["DOMAIN"][self.known_resource]

        # valid
        settings["allowed_filters"] = ["field1", "field2"]
        response, status = self.get(self.known_resource, where)
        self.assert200(status)

        # invalid
        settings["allowed_filters"] = ["field2"]
        response, status = self.get(self.known_resource, where)
        self.assert400(status)

    def test_get_nested_filter_operators_unvalidated(self):
        """test that nested filter operators are working correctly."""
        where = "".join(
            (
                '?where={"$and":[{"$or":[{"fldA":"valA"},',
                '{"fldB":"valB"}]},{"fld2":"val2"}]}',
            )
        )
        response, status = self.get(self.known_resource, where)
        self.assert200(status)

    def test_get_nested_filter_operators_validated(self):
        """test that nested filter operators are working correctly."""
        self.app.config["VALIDATE_FILTERS"] = True

        where = "".join(
            (
                '?where={"$and":[{"$or":[{"fldA":"valA"},',
                '{"fldB":"valB"}]},{"fld2":"val2"}]}',
            )
        )
        response, status = self.get(self.known_resource, where)
        self.assert400(status)

        where = "".join(
            (
                '?where={"$and":[{"$or":[{"role":',
                '["agent","client"]},{"key1":"str"}]}, {"prog":1}]}',
            )
        )
        response, status = self.get(self.known_resource, where)
        self.assert200(status)

    def test_get_invalid_where_fields(self):
        """test that checks all fields of the where clause to be valid
        resource fields according to the resource schema.
        """
        self.app.config["VALIDATE_FILTERS"] = True

        # test for an outright missing/invalid field present
        where = '?where={"$and": [{"bad_field": "val"}, {"fld2": "val2"}]}'
        response, status = self.get(self.known_resource, where)
        self.assert400(status)

        # test for resource field not validating correctly (prog is number)
        where = '?where={"prog": "stringValue"}'
        response, status = self.get(self.known_resource, where)
        self.assert400(status)

        # test for resource field validating correctly (key1 is string)
        where = '?where={"key1": "qwerty"}'
        response, status = self.get(self.known_resource, where)
        self.assert200(status)

        # test for nested resource field validating correctly
        # (location is dict)
        where = '?where={"location":{"address":"str 1","city":"SomeCity"}}'
        response, status = self.get(self.known_resource, where)
        self.assert200(status)

        # test for nested resource field validating correctly
        # (location is dict)
        where = '?where={"location.address": "str 1"}'
        response, status = self.get(self.known_resource, where)
        self.assert200(status)

        # test for nested resource field validating correctly
        # (rows is list of dicts)
        where = '?where={"rows.price": 10}'
        response, status = self.get(self.known_resource, where)
        self.assert200(status)

        # test for nested resource field validating correctly
        # (dict_list_fixed_len is a fixed-size list of dicts)
        where = '?where={"dict_list_fixed_len.key2": 1}'
        response, status = self.get(self.known_resource, where)
        self.assert200(status)

        # test for nested resource field not validating correctly
        # (bad_base_key doesn't exist in the base resource schema)
        where = '?where={"bad_base_key.sub": 1}'
        response, status = self.get(self.known_resource, where)
        self.assert400(status)

        # test for nested resource field not validating correctly
        # (bad_sub_key doesn't exist in the dict_list_fixed_len schema)
        where = '?where={"dict_list_fixed_len.bad_sub_key": 1}'
        response, status = self.get(self.known_resource, where)
        self.assert400(status)

    def test_get_lookup_field_as_string(self):
        # Test that a resource where 'item_lookup_field' is set to a field
        # of string type and which value is castable to a ObjectId is still
        # treated as a string when 'query_objectid_as_string' is set to True.
        # See PR #552.
        self.app.config["DOMAIN"]["contacts"]["query_objectid_as_string"] = True
        data = {"id": "507c7f79bcf86cd7994f6c0e", "name": "507c7f79bcf86cd7994f6c0e"}
        response, status = self.post("ids", data=data)
        self.assert201(status)

        where = '?where={"name": "507c7f79bcf86cd7994f6c0e"}'
        response, status = self.get("ids", where)
        self.assert200(status)
        items = response["_items"]
        self.assertEqual(1, len(items))

    def test_get_custom_idfield(self):
        response, status = self.get("products")
        self.assert200(status)
        links = response["_links"]
        self.assertEqual(2, len(links))
        self.assertHomeLink(links)
        self.assertResourceLink(links, "products")
        items = response["_items"]
        self.assertEqual(10, len(items))
        for item in items:
            self.assertItem(item, "products")

    def test_get_subresource_with_custom_idfield(self):
        db = self.connection[MONGO_DBNAME]
        parent_product_sku = db.products.find_one()["sku"]
        product = {
            "sku": "BAZ",
            "title": "Child product",
            "parent_product": parent_product_sku,
        }
        db.products.insert_one(product)
        response, status = self.get("products/%s/children" % parent_product_sku)
        self.assert200(status)
        self.assertEqual(len(response["_items"]), 1)
        self.assertEqual(len(response["_links"]), 2)
        self.assertEqual(response["_items"][0]["parent_product"], parent_product_sku)

    def test_get_aggregation_endpoint(self):

        _db = self.connection[MONGO_DBNAME]
        _db.aggregate_test.insert_many(
            [
                {"x": 1, "tags": ["dog", "cat"]},
                {"x": 2, "tags": ["cat"]},
                {"x": 2, "tags": ["mouse", "cat", "dog"]},
                {"x": 3, "tags": []},
            ]
        )

        self.devent = DummyEvent(lambda: True)
        self.app.before_aggregation += self.devent

        self.app.register_resource(
            "aggregate_test",
            {
                "datasource": {
                    "aggregation": {
                        "pipeline": [
                            {"$unwind": "$tags"},
                            {"$group": {"_id": "$tags", "count": {"$sum": "$field1"}}},
                            {"$sort": SON([("count", -1), ("_id", -1)])},
                        ]
                    }
                }
            },
        )

        response, status = self.get("aggregate_test?aggregate=ciao")
        self.assert400(status)
        self.assertTrue(self.devent.called is None)

        def assertOutput(doc, count, id):
            self.assertEqual(doc["count"], count)
            self.assertEqual(doc["_id"], id)

        response, status = self.get('aggregate_test?aggregate={"$field1":1}')
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 3)
        assertOutput(docs[0], 3, "cat")
        assertOutput(docs[1], 2, "dog")
        assertOutput(docs[2], 1, "mouse")
        self.assertEqual("aggregate_test", self.devent.called[0])

        response, status = self.get('aggregate_test?aggregate={"$field1":2}')
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 3)
        assertOutput(docs[0], 6, "cat")
        assertOutput(docs[1], 4, "dog")
        assertOutput(docs[2], 2, "mouse")
        self.assertEqual("aggregate_test", self.devent.called[0])

        # this will return 0 for all documents 'count' fields as no $field1
        # will be gien with the query (actually, no query will be there at all)
        response, status = self.get("aggregate_test")
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 3)
        self.assertEqual(docs[0]["count"], 0)
        self.assertEqual(docs[1]["count"], 0)
        self.assertEqual(docs[2]["count"], 0)
        self.assertEqual("aggregate_test", self.devent.called[0])

        # malformed field name is ignored
        response, status = self.get('aggregate_test?aggregate={"field1":1}')
        self.assert200(status)
        self.assertEqual("aggregate_test", self.devent.called[0])

        # unknown field is ignored
        response, status = self.get('aggregate_test?aggregate={"$unknown":1}')
        self.assert200(status)

        # max_results is considered
        response, status = self.get(
            'aggregate_test?aggregate={"$field1":1}&max_results=1'
        )
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 1)

    def test_get_aggregation_parsing(self):

        date = datetime.utcnow()

        _db = self.connection[MONGO_DBNAME]
        _db.aggregate_test.insert_many(
            [
                {"x": 1, "date": date},
                {"x": 2, "date": date},
                {"x": 3, "date": date},
                {"x": 4, "date": date + timedelta(days=-1)},
            ]
        )

        self.app.register_resource(
            "aggregate_test",
            {
                "datasource": {
                    "aggregation": {
                        "pipeline": [{"$match": {"date": {"$gte": "$date"}}}]
                    }
                }
            },
        )

        challenge = date.strftime(self.app.config["DATE_FORMAT"])
        response, status = self.get(
            'aggregate_test?aggregate={"$date": "%s"}' % challenge
        )
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 3)

        challenge = (date + timedelta(days=-1)).strftime(self.app.config["DATE_FORMAT"])
        response, status = self.get(
            'aggregate_test?aggregate={"$date": "%s"}' % challenge
        )
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 4)

    def test_get_aggregation_with_lists(self):
        _db = self.connection[MONGO_DBNAME]
        _db.aggregate_test.insert_many(
            [
                {"x": 1, "tags": ["a", "b", "c"]},
                {"x": 2, "tags": ["a"]},
                {"x": 3, "tags": ["a", "b"]},
                {"x": [4], "tags": []},
            ]
        )

        self.app.register_resource(
            "aggregate_test",
            {
                "datasource": {
                    "aggregation": {
                        "pipeline": [
                            {
                                "$match": {
                                    "$or": [{"tags": "$match_tags"}, {"x": ["$x"]}]
                                }
                            }
                        ]
                    }
                }
            },
        )

        response, status = self.get('aggregate_test?aggregate={"$match_tags": "a"}')
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 3)

        response, status = self.get(
            'aggregate_test?aggregate={"$match_tags": ["a", "b"]}'
        )
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 1)

        response, status = self.get('aggregate_test?aggregate={"$x": 4}')
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 1)

    def test_get_aggregation_pruning(self):

        date = datetime.utcnow()

        _db = self.connection[MONGO_DBNAME]
        _db.aggregate_test.insert_many(
            [
                {"x": 1, "date": date},
                {"x": 2, "date": date},
                {"x": 3, "date": date},
                {"x": 4, "date": date + timedelta(days=-1)},
            ]
        )

        self.app.register_resource(
            "aggregate_test",
            {
                "datasource": {
                    "aggregation": {
                        "pipeline": [{"$match": {"date": {"$gte": "$date"}, "x": "$x"}}]
                    }
                }
            },
        )

        # look for date = now, x = 4, which shall return empty result
        challenge = date.strftime(self.app.config["DATE_FORMAT"])
        response, status = self.get(
            'aggregate_test?aggregate={"$date": "%s", "$x": 4}' % challenge
        )
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 0)

        # look for date = yesterday, x = 4, which shall return only one result
        challenge = (date + timedelta(days=-1)).strftime(self.app.config["DATE_FORMAT"])
        response, status = self.get(
            'aggregate_test?aggregate={"$date": "%s", "$x": 4}' % challenge
        )
        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["x"], 4)

        # look  for date = yesterday, which shall return all four results
        challenge = (date + timedelta(days=-1)).strftime(self.app.config["DATE_FORMAT"])
        response, status = self.get(
            'aggregate_test?aggregate={"$date": "%s", "$x": {}}' % challenge
        )

        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 4)

        # look  for x = 3, which shall return only one result
        response, status = self.get('aggregate_test?aggregate={"$x": 3, "$date": {}}')

        self.assert200(status)
        docs = response["_items"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["x"], 3)

    def test_get_aggregation_pagination(self):
        _db = self.connection[MONGO_DBNAME]

        num = 75
        _db.aggregate_test.insert_many([{"x": x} for x in range(num)])

        self.app.register_resource(
            "aggregate_test",
            {
                "datasource": {
                    "aggregation": {"pipeline": [{"$sort": SON([("x", -1)])}]}
                }
            },
        )

        # first page
        response, status = self.get("aggregate_test")
        self.assert200(status)

        links = response["_links"]
        self.assertNextLink(links, 2)
        self.assertLastLink(links, 3)
        self.assertPagination(response, 1, 75, 25)

        items = response["_items"]
        expected_length = self.app.config["PAGINATION_DEFAULT"]
        self.assertEqual(len(items), expected_length)

        item, value = 0, num - 1
        self.assertEqual(items[item]["x"], value)
        item, value = expected_length - 1, num - expected_length
        self.assertEqual(items[item]["x"], value)

        # second page
        response, status = self.get("aggregate_test?page=2")
        self.assert200(status)

        links = response["_links"]
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)
        self.assertLastLink(links, 3)
        self.assertPagination(response, 2, 75, 25)

        items = response["_items"]
        expected_length = self.app.config["PAGINATION_DEFAULT"]
        self.assertEqual(len(items), expected_length)

        item, value = 0, num - 1 - self.app.config["PAGINATION_DEFAULT"]
        self.assertEqual(items[item]["x"], value)
        item, value = expected_length - 1, num - expected_length * 2
        self.assertEqual(items[item]["x"], value)

        # third page
        response, status = self.get("aggregate_test?page=3")
        self.assert200(status)

        links = response["_links"]
        self.assertPrevLink(links, 2)
        self.assertLastLink(links, None)
        self.assertPagination(response, 3, 75, 25)

        items = response["_items"]
        expected_length = num - self.app.config["PAGINATION_DEFAULT"] * 2
        self.assertEqual(len(items), expected_length)

        item, value = 0, expected_length - 1
        self.assertEqual(items[item]["x"], value)

        item, value = expected_length - 1, 0
        self.assertEqual(items[item]["x"], 0)

        # pagination is disabled for the endpoint
        self.domain["aggregate_test"]["pagination"] = False
        # hence we get all documents with a single request
        response, status = self.get("aggregate_test")
        self.assert200(status)
        items = response["_items"]
        self.assertEqual(len(items), num)
        # and pagination requests are ignored
        response, status = self.get("aggregate_test?page=2")
        self.assert200(status)
        items = response["_items"]
        self.assertEqual(len(items), num)

    def test_get_query_bitwise_query_operators(self):
        del self.domain["contacts"]["schema"]["ref"]["required"]
        response, status = self.delete(self.known_resource_url)
        self.assert204(status)

        data = {"prog": 20}  # 00010100
        response, status = self.post(self.known_resource_url, data=data)
        self.assert201(status)

        where = '?where={"prog": {"$bitsAllClear": [1, 5]}}'
        response, status = self.get(self.known_resource, where)
        self.assert200(status)
        items = response["_items"]
        self.assertEqual(1, len(items))

        where = '?where={"prog": {"$bitsAllClear": [2, 5]}}'
        response, status = self.get(self.known_resource, where)
        self.assert200(status)
        items = response["_items"]
        self.assertEqual(0, len(items))

    def assertGet(self, response, status, resource=None):
        self.assert200(status)

        links = response["_links"]
        self.assertEqual(len(links), 4)
        self.assertHomeLink(links)
        if not resource:
            resource = self.known_resource
        self.assertResourceLink(links, resource)
        self.assertNextLink(links, 2)

        resource = response["_items"]
        self.assertEqual(len(resource), self.app.config["PAGINATION_DEFAULT"])

        for item in resource:
            self.assertItem(item, self.known_resource)

        etag = item.get(self.app.config["ETAG"])
        self.assertTrue(etag is not None)


class TestGetItem(TestBase):
    def assertItemResponse(self, response, status, resource=None):
        self.assert200(status)
        self.assertTrue(self.app.config["ETAG"] in response)
        links = response["_links"]
        self.assertTrue(len(links) == 3 or len(links) == 4)
        self.assertHomeLink(links)
        self.assertCollectionLink(links, resource or self.known_resource)
        self.assertItem(response, resource or self.known_resource)

    def test_disallowed_getitem(self):
        _, status = self.get(self.empty_resource, item=self.item_id)
        self.assert404(status)

    def test_getitem_by_id(self):
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assertItemResponse(response, status)

        response, status = self.get(self.known_resource, item=self.unknown_item_id)
        self.assert404(status)

    def test_getitem_internal_by_id(self):
        with self.app.test_request_context(self.known_resource_url):
            response, _, _, status = getitem_internal(self.known_resource)
        self.assert200(status)

    def test_getitem_noschema(self):
        self.app.config["DOMAIN"][self.known_resource]["schema"] = {}
        response, status = self.get(self.known_resource, item=self.item_id)
        self.assertItemResponse(response, status)

    def test_getitem_by_name(self):
        response, status = self.get(self.known_resource, item=self.item_name)
        self.assertItemResponse(response, status)
        response, status = self.get(self.known_resource, item=self.unknown_item_name)
        self.assert404(status)

    def test_getitem_by_name_self_href(self):
        response, status = self.get(self.known_resource, item=self.item_id)
        self_href = response["_links"]["self"]["href"]

        response, status = self.get(self.known_resource, item=self.item_name)

        self.assertEqual(self_href, response["_links"]["self"]["href"])

    def test_getitem_by_integer(self):
        self.domain["contacts"]["additional_lookup"] = {"field": "prog"}
        self.app._add_resource_url_rules("contacts", self.domain["contacts"])
        response, status = self.get(self.known_resource, item=1)
        self.assertItemResponse(response, status)
        response, status = self.get(self.known_resource, item=self.known_resource_count)
        self.assert404(status)

    def test_getitem_if_modified_since(self):
        self.assertIfModifiedSince(self.item_id_url)

    def test_getitem_if_none_match(self):
        r = self.test_client.get(self.item_id_url)
        etag = r.headers.get("ETag")
        self.assertTrue(etag is not None)

        # test that ETag is compliant to RFC 7232-2.3 and #794 is fixed.
        self.assertTrue(etag[0] == '"')
        self.assertTrue(etag[-1] == '"')

        r = self.test_client.get(self.item_id_url, headers=[("If-None-Match", etag)])
        self.assert304(r.status_code)
        self.assertTrue(not r.get_data())

        # test that we also support doublequote-less etags, for legacy
        # reasons. See #794.
        r = self.test_client.get(
            self.item_id_url, headers=[("If-None-Match", etag.replace('"', ""))]
        )
        self.assert304(r.status_code)
        self.assertTrue(not r.get_data())

        # test that we support weak etags
        weak_etag = "W/" + etag
        r = self.test_client.get(
            self.item_id_url, headers=[("If-None-Match", weak_etag)]
        )
        self.assert304(r.status_code)
        self.assertTrue(not r.get_data())

    def test_cache_control(self):
        self.assertCacheControl(self.item_id_url)

    def test_expires(self):
        self.assertExpires(self.item_id_url)

    def test_getitem_by_id_different_resource(self):
        response, status = self.get(self.different_resource, item=self.user_id)
        self.assertItemResponse(response, status, self.different_resource)

        response, status = self.get(self.different_resource, item=self.item_id)
        self.assert404(status)

    def test_getitem_by_name_different_resource(self):
        response, status = self.get(self.different_resource, item=self.user_username)
        self.assertItemResponse(response, status, self.different_resource)
        response, status = self.get(
            self.different_resource, item=self.unknown_item_name
        )
        self.assert404(status)

    def test_getitem_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        contacts = self.random_contacts(1, False)
        ref = "test_update_field"
        contacts[0]["ref"] = ref
        _db = self.connection[MONGO_DBNAME]
        _db.contacts.insert_one(contacts[0])
        response, status = self.get(self.known_resource, item=ref)
        self.assertItemResponse(response, status)

    def test_get_with_post_override(self):
        # POST request with GET override turns into a GET
        headers = [("X-HTTP-Method-Override", "GET")]
        r = self.test_client.post(self.item_id_url, headers=headers)
        response, status = self.parse_response(r)
        self.assertItemResponse(response, status)

    def test_getitem_embedded(self):
        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]

        fake_contact = self.random_contacts(1)[0]
        fake_contact_id = _db.contacts.insert_one(fake_contact).inserted_id
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)}, {"$set": {"person": fake_contact_id}}
        )

        invoices = self.domain["invoices"]

        # Test that we get 400 if can't parse dict
        embedded = "not-a-dict"
        r = self.test_client.get(
            "%s/%s/%s" % (invoices["url"], self.invoice_id, "?embedded=%s" % embedded)
        )
        self.assert400(r.status_code)

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is True by default)
        embedded = '{"person": 1}'
        r = self.test_client.get(
            "%s/%s/%s" % (invoices["url"], self.invoice_id, "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content["person"], self.item_id)

        # Set field to be embedded
        invoices["schema"]["person"]["data_relation"]["embeddable"] = True

        # Test that global setting applies even if field is set to embedded
        invoices["embedding"] = False
        r = self.test_client.get(
            "%s/%s/%s" % (invoices["url"], self.invoice_id, "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content["person"], self.item_id)

        # Test that it works
        invoices["embedding"] = True
        r = self.test_client.get(
            "%s/%s/%s" % (invoices["url"], self.invoice_id, "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["person"])

        # Test that it ignores a bogus field
        embedded = '{"person": 1, "not-a-real-field": 1}'
        r = self.test_client.get(
            "%s/%s/%s" % (invoices["url"], self.invoice_id, "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["person"])

        # Test that it ignores a real field with a bogus value
        embedded = '{"person": 1, "inv_number": "not-a-real-value"}'
        r = self.test_client.get(
            "%s/%s/%s" % (invoices["url"], self.invoice_id, "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["person"])

        # Test that it works with item endpoint too
        r = self.test_client.get(
            "%s/%s/%s" % (invoices["url"], self.invoice_id, "?embedded=%s" % embedded)
        )
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue("location" in content["person"])

        # Test that changes to embedded document invalidate parent cache
        invoice_last_modified = r.headers.get("Last-Modified")
        contact_url = "%s/%s" % (self.domain["contacts"]["url"], fake_contact_id)
        r = self.test_client.get(contact_url)
        contact_etag = r.headers.get("Etag")

        # wait for contact and invoice updated at diff to pass 1s resolution
        time.sleep(2)
        changes = {"location": {"city": "new city"}}
        response, status = self.patch(
            contact_url, data=changes, headers=[("If-Match", contact_etag)]
        )
        self.assert200(status)

        invoice_url = "%s/%s/%s" % (
            invoices["url"],
            self.invoice_id,
            "?embedded=%s" % embedded,
        )
        r = self.test_client.get(
            invoice_url, headers=[("If-Modified-Since", invoice_last_modified)]
        )
        self.assert200(r.status_code)

    def test_subresource_getitem(self):
        _db = self.connection[MONGO_DBNAME]

        # create random contact
        fake_contact = self.random_contacts(1)[0]
        fake_contact_id = _db.contacts.insert_one(fake_contact).inserted_id
        # update first invoice to reference the new contact
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)}, {"$set": {"person": fake_contact_id}}
        )

        # GET all invoices by new contact
        response, status = self.get(
            "users/%s/invoices/%s" % (fake_contact_id, self.invoice_id)
        )
        self.assert200(status)
        self.assertEqual(response["person"], str(fake_contact_id))
        self.assertEqual(response["_id"], self.invoice_id)

    def test_getitem_data_relation_hateoas(self):
        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]

        fake_contact = self.random_contacts(1)[0]
        fake_contact_id = _db.contacts.insert_one(fake_contact).inserted_id
        url = self.domain[self.known_resource]["url"]
        item_title = self.domain[self.known_resource]["item_title"]
        invoices = self.domain["invoices"]

        # Test nullable data relation fields
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)}, {"$set": {"person": None}}
        )

        response, status = self.get("%s/%s" % (invoices["url"], self.invoice_id))
        self.assertTrue("related" not in response["_links"])

        # Test object id data relation fields
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)}, {"$set": {"person": fake_contact_id}}
        )

        response, status = self.get("%s/%s" % (invoices["url"], self.invoice_id))
        self.assertRelatedLink(response["_links"], "person")
        related_links = response["_links"]["related"]
        self.assertEqual(related_links["person"]["title"], item_title)
        self.assertEqual(
            related_links["person"]["href"], "%s/%s" % (url, fake_contact_id)
        )

        # Test DBRef data relation fields
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)},
            {"$set": {"persondbref": DBRef("contacts", fake_contact_id)}},
        )

        response, status = self.get("%s/%s" % (invoices["url"], self.invoice_id))
        self.assertRelatedLink(response["_links"], "persondbref")
        related_links = response["_links"]["related"]
        self.assertEqual(related_links["persondbref"]["title"], item_title)
        self.assertEqual(
            related_links["persondbref"]["href"], "%s/%s" % (url, fake_contact_id)
        )

        # Test list of object id data relation fields
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)},
            {"$set": {"invoicing_contacts": [fake_contact_id] * 5}},
        )

        response, status = self.get("%s/%s" % (invoices["url"], self.invoice_id))
        self.assertRelatedLink(response["_links"], "invoicing_contacts")
        related_links = response["_links"]["related"]
        self.assertEqual(len(related_links["invoicing_contacts"]), 5)

    def test_getitem_ifmatch_disabled(self):
        # when IF_MATCH is disabled no etag is present in payload
        self.app.config["IF_MATCH"] = False
        response, _ = self.get(self.known_resource, item=self.item_id)
        self.assertTrue(self.app.config["ETAG"] not in response)

    def test_getitem_ifmatch_disabled_if_mod_since(self):
        # Test that #239 is fixed.
        # IF_MATCH is disabled and If-Modified-Since request comes through. If
        # a 304 was expected, we would crash like a mofo.
        self.app.config["IF_MATCH"] = False

        # IMS needs to see as recent as possible since the test db has just
        # been built
        header = [("If-Modified-Since", date_to_rfc1123(datetime.utcnow()))]

        r = self.test_client.get(self.item_id_url, headers=header)
        self.assert304(r.status_code)

    def test_getitem_custom_auto_document_fields(self):
        self.app.config["LAST_UPDATED"] = "_updated_on"
        self.app.config["DATE_CREATED"] = "_created_on"
        self.app.config["ETAG"] = "_the_etag"
        response, _ = self.get(self.known_resource, item=self.item_id)
        self.assertTrue("_updated_on" in response)
        self.assertTrue("_created_on" in response)
        self.assertTrue("_the_etag" in response)

    def test_getitem_projection(self):
        projection = '{"prog": 1}'
        r, status = self.get(
            self.known_resource, "?projection=%s" % projection, item=self.item_id
        )
        self.assert200(status)
        self.assertFalse("location" in r)
        self.assertFalse("role" in r)
        self.assertTrue("prog" in r)
        self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
        self.assertTrue(self.app.config["ETAG"] in r)
        self.assertTrue(self.app.config["LAST_UPDATED"] in r)
        self.assertTrue(self.app.config["DATE_CREATED"] in r)
        self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
        self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

        projection = '{"prog": 0}'
        r, status = self.get(
            self.known_resource, "?projection=%s" % projection, item=self.item_id
        )
        self.assert200(status)
        self.assertFalse("prog" in r)
        self.assertTrue("location" in r)
        self.assertTrue("role" in r)
        self.assertTrue(self.domain[self.known_resource]["id_field"] in r)
        self.assertTrue(self.app.config["ETAG"] in r)
        self.assertTrue(self.app.config["LAST_UPDATED"] in r)
        self.assertTrue(self.app.config["DATE_CREATED"] in r)
        self.assertTrue(r[self.app.config["LAST_UPDATED"]] != self.epoch)
        self.assertTrue(r[self.app.config["DATE_CREATED"]] != self.epoch)

    def test_getitem_lookup_field_as_string(self):
        # Test that a resource where 'item_lookup_field' is set to a field
        # of string type and which value is castable to a ObjectId is still
        # treated as a string when 'query_objectid_as_string' is set to True.
        # See PR #552.
        data = {"id": "507c7f79bcf86cd7994f6c0e", "name": "john"}
        response, status = self.post("ids", data=data)
        self.assert201(status)
        response, status = self.get("ids", item="507c7f79bcf86cd7994f6c0e")
        self.assert200(status)

    def test_getitem_with_custom_idfield(self):
        _db = self.connection[MONGO_DBNAME]
        sku = _db.products.find()[0]["sku"]
        response, status = self.get("products", item=sku)
        self.assertItemResponse(response, status, "products")


class TestHead(TestBase):
    def test_head_home(self):
        self.assertHead("/")

    def test_head_resource(self):
        self.assertHead(self.known_resource_url)

    def test_head_item(self):
        self.assertHead(self.item_id_url)

    def assertHead(self, url):
        h = self.test_client.head(url)
        r = self.test_client.get(url)
        self.assertTrue(not h.data)

        if "Expires" in r.headers:
            # there's a tiny chance that the two expire values will differ by
            # one second. See #316.
            head_expire = str_to_date(r.headers.pop("Expires"))
            get_expire = str_to_date(h.headers.pop("Expires"))
            d = head_expire - get_expire
            self.assertTrue(d.seconds in (0, 1))

        self.assertEqual(r.headers, h.headers)


class TestEvents(TestBase):
    def setUp(self):
        super(TestEvents, self).setUp()
        self.devent = DummyEvent(lambda: True)

    def test_on_pre_GET_for_item(self):
        self.app.on_pre_GET += self.devent
        self.get_item()
        self.assertEqual("contacts", self.devent.called[0])
        self.assertFalse(self.devent.called[1] is None)

    def test_on_pre_GET_item_dynamic_filter(self):
        def filter_this(resource, request, lookup):
            lookup["_id"] = self.item_id

        self.app.on_pre_GET += filter_this
        # Would normally return a 404; will return one instead.
        r, s = self.parse_response(self.get_item())
        self.assert200(s)
        self.assertEqual(r[self.domain[self.known_resource]["id_field"]], self.item_id)

    def test_on_pre_GET_resource_for_item(self):
        self.app.on_pre_GET_contacts += self.devent
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
        self.assertEqual(len(r[self.app.config["ITEMS"]]), 1)

    def test_on_pre_GET_resource_dynamic_filter_12_chr_nonunicode_string(self):
        # Test for bug in _mongotize(). See
        # https://github.com/nicolaiarocci/eve/issues/508
        def filter_this(request, lookup):
            request.args = ImmutableMultiDict({"where": '{"name":"Alice Brooks"}'})

        self.app.register_resource("names", {"schema": {"name": {"type": "string"}}})
        # We want to test with a non-unicode string for 'where', so we need to
        # do it with a pre_GET callback
        self.app.on_pre_GET_names += filter_this
        self.post("names", data={"name": "Alice Brooks"})
        r, s = self.get("names")
        self.assertEqual(len(r[self.app.config["ITEMS"]]), 1)

    def test_on_pre_GET_resource_for_resource(self):
        self.app.on_pre_GET_contacts += self.devent
        self.get_resource()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_for_item(self):
        self.app.on_post_GET += self.devent
        self.get_item()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_resource_for_item(self):
        self.app.on_post_GET_contacts += self.devent
        self.get_item()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_for_resource(self):
        self.app.on_post_GET += self.devent
        self.get_resource()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_resource_for_resource(self):
        self.app.on_post_GET_contacts += self.devent
        self.get_resource()
        self.assertFalse(self.devent.called is None)

    def test_on_post_GET_homepage(self):
        self.app.on_post_GET += self.devent
        self.test_client.get("/")
        self.assertTrue(self.devent.called[0] is None)
        self.assertEqual(3, len(self.devent.called))

    def test_on_fetched_resource(self):
        self.app.on_fetched_resource += self.devent
        self.get_resource()
        self.assertEqual("contacts", self.devent.called[0])
        self.assertEqual(
            self.app.config["PAGINATION_DEFAULT"],
            len(self.devent.called[1][self.app.config["ITEMS"]]),
        )

    def test_on_fetched_resource_contacts(self):
        self.app.on_fetched_resource_contacts += self.devent
        self.get_resource()
        self.assertEqual(
            self.app.config["PAGINATION_DEFAULT"],
            len(self.devent.called[0][self.app.config["ITEMS"]]),
        )

    def test_on_fetched_item(self):
        self.app.on_fetched_item += self.devent
        self.get_item()
        self.assertEqual("contacts", self.devent.called[0])
        id_field = self.domain[self.known_resource]["id_field"]
        self.assertEqual(self.item_id, str(self.devent.called[1][id_field]))
        self.assertEqual(2, len(self.devent.called))

    def test_on_fetched_item_contacts(self):
        self.app.on_fetched_item_contacts += self.devent
        self.get_item()
        id_field = self.domain[self.known_resource]["id_field"]
        self.assertEqual(self.item_id, str(self.devent.called[0][id_field]))
        self.assertEqual(1, len(self.devent.called))

    def test_get_before_aggregation_hook(self):
        _db = self.connection[MONGO_DBNAME]
        _db.aggregate_test.insert_many(
            [
                {"x": 1, "tags": ["dog", "cat"]},
                {"x": 2, "tags": ["cat"]},
                {"x": 2, "tags": ["mouse", "cat", "dog"]},
                {"x": 3, "tags": []},
            ]
        )

        self.app.before_aggregation += self.devent

        self.app.register_resource(
            "aggregate_test",
            {
                "datasource": {
                    "aggregation": {
                        "pipeline": [
                            {"$unwind": "$tags"},
                            {"$group": {"_id": "$tags", "count": {"$sum": "$field1"}}},
                        ]
                    }
                }
            },
        )

        response, status = self.get("aggregate_test?aggregate=ciao")
        self.assert400(status)
        self.assertTrue(self.devent.called is None)

        response, status = self.get('aggregate_test?aggregate={"$field1":1}')
        self.assert200(status)
        self.assertEqual("aggregate_test", self.devent.called[0])

    def test_get_after_aggregation_hook(self):
        _db = self.connection[MONGO_DBNAME]
        _db.aggregate_test.insert_many(
            [
                {"x": 1, "tags": ["dog", "cat"]},
                {"x": 2, "tags": ["cat"]},
                {"x": 2, "tags": ["mouse", "cat", "dog"]},
                {"x": 3, "tags": []},
            ]
        )

        self.app.after_aggregation += self.devent

        self.app.register_resource(
            "aggregate_test",
            {
                "datasource": {
                    "aggregation": {
                        "pipeline": [
                            {"$unwind": "$tags"},
                            {"$group": {"_id": "$tags", "count": {"$sum": "$field1"}}},
                        ]
                    }
                }
            },
        )

        response, status = self.get("aggregate_test?aggregate=ciao")
        self.assert400(status)
        self.assertTrue(self.devent.called is None)

        response, status = self.get('aggregate_test?aggregate={"$field1":1}')
        self.assert200(status)
        self.assertEqual("aggregate_test", self.devent.called[0])

    def get_resource(self):
        return self.test_client.get(self.known_resource_url)

    def get_item(self, url=None):
        if not url:
            url = self.item_id_url
        return self.test_client.get(url)
