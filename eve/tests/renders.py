# -*- coding: utf-8 -*-

from bson import ObjectId
from eve.tests import TestBase
from eve.utils import api_prefix
from eve.tests.test_settings import MONGO_DBNAME
import simplejson as json


class TestRenders(TestBase):
    def test_default_render(self):
        r = self.test_client.get("/")
        self.assertEqual(r.content_type, "application/json")

    def test_json_render(self):
        r = self.test_client.get("/", headers=[("Accept", "application/json")])
        self.assertEqual(r.content_type, "application/json")

    def test_xml_render(self):
        r = self.test_client.get("/", headers=[("Accept", "application/xml")])
        self.assertTrue("application/xml" in r.content_type)

    def test_xml_url_escaping(self):
        r = self.test_client.get(
            "%s?max_results=1" % self.known_resource_url,
            headers=[("Accept", "application/xml")],
        )
        self.assertTrue(b"&amp;" in r.get_data())

    def test_xml_leaf_escaping(self):
        # test that even xml leaves content is being properly escaped

        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]
        fake_contact = self.random_contacts(1)[0]
        fake_contact["ref"] = "12345 & 67890"
        fake_contact_id = _db.contacts.insert_one(fake_contact).inserted_id

        r = self.test_client.get(
            "%s/%s" % (self.known_resource_url, fake_contact_id),
            headers=[("Accept", "application/xml")],
        )
        self.assertTrue(b"12345 &amp; 6789" in r.get_data())

    def test_xml_ordered_nodes(self):
        """Test that xml nodes are ordered and #441 is addressed."""
        r = self.test_client.get(
            "%s?max_results=1" % self.known_resource_url,
            headers=[("Accept", "application/xml")],
        )
        data = r.get_data()
        idx1 = data.index(b"_created")
        idx2 = data.index(b"_etag")
        idx3 = data.index(b"_id")
        idx4 = data.index(b"_updated")
        self.assertTrue(idx1 < idx2 < idx3 < idx4)
        idx1 = data.index(b"max_results")
        idx2 = data.index(b"page")
        idx3 = data.index(b"total")
        self.assertTrue(idx1 < idx2 < idx3)
        idx1 = data.index(b"last")
        idx2 = data.index(b"next")
        idx3 = data.index(b"parent")
        self.assertTrue(idx1 < idx2 < idx3)

    def test_xml_data_relation_hateoas(self):
        # We need to assign a `person` to our test invoice
        _db = self.connection[MONGO_DBNAME]

        fake_contact = self.random_contacts(1)[0]
        fake_contact_id = _db.contacts.insert_one(fake_contact).inserted_id
        url = self.domain[self.known_resource]["url"]
        item_title = self.domain[self.known_resource]["item_title"]
        invoices = self.domain["invoices"]

        # Test object id data relation fields
        _db.invoices.update_one(
            {"_id": ObjectId(self.invoice_id)}, {"$set": {"person": fake_contact_id}}
        )

        r = self.test_client.get(
            "%s/%s" % (invoices["url"], self.invoice_id),
            headers=[("Accept", "application/xml")],
        )
        data_relation_opening_tag = '<person href="%s/%s" title="%s">' % (
            url,
            fake_contact_id,
            item_title,
        )
        self.assertTrue(data_relation_opening_tag in r.data.decode())

    def test_unknown_render(self):
        r = self.test_client.get("/", headers=[("Accept", "application/html")])
        self.assertEqual(r.content_type, "application/json")

    def test_json_xml_disabled(self):
        self.app.config["RENDERERS"] = tuple()
        r = self.test_client.get(
            self.known_resource_url, headers=[("Accept", "application/json")]
        )
        self.assert500(r.status_code)
        r = self.test_client.get(
            self.known_resource_url, headers=[("Accept", "application/xml")]
        )
        self.assert500(r.status_code)
        r = self.test_client.get(self.known_resource_url)
        self.assert500(r.status_code)

    def test_json_disabled(self):
        self.app.config["RENDERERS"] = ("eve.render.XMLRenderer",)
        r = self.test_client.get(
            self.known_resource_url, headers=[("Accept", "application/json")]
        )
        self.assertTrue("application/xml" in r.content_type)
        r = self.test_client.get(
            self.known_resource_url, headers=[("Accept", "application/xml")]
        )
        self.assertTrue("application/xml" in r.content_type)
        r = self.test_client.get(self.known_resource_url)
        self.assertTrue("application/xml" in r.content_type)

    def test_xml_disabled(self):
        self.app.config["RENDERERS"] = ("eve.render.JSONRenderer",)
        r = self.test_client.get(
            self.known_resource_url, headers=[("Accept", "application/xml")]
        )
        self.assertEqual(r.content_type, "application/json")
        r = self.test_client.get(
            self.known_resource_url, headers=[("Accept", "application/json")]
        )
        self.assertEqual(r.content_type, "application/json")
        r = self.test_client.get(self.known_resource_url)
        self.assertEqual(r.content_type, "application/json")

    def test_json_keys_sorted(self):
        self.app.config["JSON_SORT_KEYS"] = True
        r = self.test_client.get(
            self.known_resource_url, headers=[("Accept", "application/json")]
        )
        self.assertEqual(
            json.dumps(json.loads(r.get_data()), sort_keys=True).encode(), r.get_data()
        )

    def test_jsonp_enabled(self):
        arg = "callback"
        self.app.config["JSONP_ARGUMENT"] = arg
        val = "JSON_CALLBACK"
        r = self.test_client.get("/?%s=%s" % (arg, val))
        self.assertTrue(r.get_data().decode("utf-8").startswith(val))

    def test_CORS(self):
        # no CORS headers if Origin is not provided with the request.
        r = self.test_client.get("/")
        self.assertFalse("Access-Control-Allow-Origin" in r.headers)
        self.assertFalse("Access-Control-Allow-Methods" in r.headers)
        self.assertFalse("Access-Control-Max-Age" in r.headers)
        self.assertFalse("Access-Control-Expose-Headers" in r.headers)
        self.assertFalse("Access-Control-Allow-Credentials" in r.headers)
        self.assert200(r.status_code)

        # test that if X_DOMAINS is set to '*', then any Origin value is
        # allowed. Also test that only the Origin header included with the
        # request will be returned to the client.
        self.app.config["X_DOMAINS"] = "*"
        r = self.test_client.get("/", headers=[("Origin", "http://example.com")])
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://example.com")
        self.assertEqual(r.headers["Vary"], "Origin")

        # Given that CORS is activated with X_DOMAINS = '*',
        # test that if X_ALLOW_CREDENTIALS is set to True
        # then the relevant header is included in the response
        self.app.config["X_ALLOW_CREDENTIALS"] = True
        r = self.test_client.get("/", headers=[("Origin", "http://example.com")])
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Credentials"], "true")

        # with any other non-True value, it is missing
        self.app.config["X_ALLOW_CREDENTIALS"] = False
        r = self.test_client.get("/", headers=[("Origin", "http://example.com")])
        self.assert200(r.status_code)
        self.assertFalse("Access-Control-Allow-Credentials" in r.headers)

        # test that if a list is set for X_DOMAINS, then:
        # 1. only list values are accepted;
        # 2. only the value included with the request is returned back.
        self.app.config["X_DOMAINS"] = ["http://1of2.com", "http://2of2.com"]
        r = self.test_client.get("/", headers=[("Origin", "http://1of2.com")])
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://1of2.com")

        r = self.test_client.get("/", headers=[("Origin", "http://2of2.com")])
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://2of2.com")

        r = self.test_client.get("/", headers=[("Origin", "http://notreally.com")])
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "")

        # other Access-Control-Allow- headers are included.
        self.assertTrue("Access-Control-Allow-Headers" in r.headers)
        self.assertTrue("Access-Control-Allow-Methods" in r.headers)
        self.assertTrue("Access-Control-Max-Age" in r.headers)
        self.assertTrue("Access-Control-Expose-Headers" in r.headers)

        # unescaped dots of old (pre v0.7) or malicious X_DOMAINS definitions
        # would be interpreted as any character, causing security issue with
        # bad guy registering wwwxgithub.com to pass as www.github.com (see
        # #660).

        self.app.config["X_DOMAINS"] = ["http://www.github.com"]
        r = self.test_client.get("/", headers=[("Origin", "http://wwwxgithub.com")])
        self.assert200(r.status_code)
        self.assertFalse(
            "http://wwwxgithub.com" in r.headers["Access-Control-Allow-Origin"]
        )

        # test that X_DOMAINS does not match
        # if the origin contains extra characters (#974)
        r = self.test_client.get("/", headers=[("Origin", "http://1of2.com:8000")])
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "")

    def test_CORS_regex(self):
        # test if X_DOMAINS_RE is set with a list of regexes,
        # origins are matched against this list (#974)
        self.app.config["X_DOMAINS_RE"] = [r"^http://sub-\d{3}\.domain\.com$"]

        r = self.test_client.get("/", headers=[("Origin", "http://sub-123.domain.com")])
        self.assert200(r.status_code)
        self.assertEqual(
            r.headers["Access-Control-Allow-Origin"], "http://sub-123.domain.com"
        )

        # test that similar domains are not allowed
        r = self.test_client.get(
            "/", headers=[("Origin", "http://sub-1234.domain.com")]
        )
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "")

        r = self.test_client.get(
            "/", headers=[("Origin", "http://sub-123.domain.com:8000")]
        )
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "")

        r = self.test_client.get("/", headers=[("Origin", "http://sub-123xdomain.com")])
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "")

        # test that invalid regexes are ignored, especially '*'
        self.app.config["X_DOMAINS_RE"] = ["*"]
        r = self.test_client.get("/", headers=[("Origin", "http://www.example.com")])
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "")

    def test_CORS_MAX_AGE(self):
        self.app.config["X_DOMAINS"] = "*"
        r = self.test_client.get("/", headers=[("Origin", "http://example.com")])
        self.assertEqual(r.headers["Access-Control-Max-Age"], "21600")

        self.app.config["X_MAX_AGE"] = 2000
        r = self.test_client.get("/", headers=[("Origin", "http://example.com")])
        self.assertEqual(r.headers["Access-Control-Max-Age"], "2000")

    def test_CORS_OPTIONS(self, url="/", methods=None):
        if methods is None:
            methods = []

        r = self.test_client.open(url, method="OPTIONS")
        self.assertFalse("Access-Control-Allow-Origin" in r.headers)
        self.assertFalse("Access-Control-Allow-Methods" in r.headers)
        self.assertFalse("Access-Control-Max-Age" in r.headers)
        self.assertFalse("Access-Control-Expose-Headers" in r.headers)
        self.assertFalse("Access-Control-Allow-Credentials" in r.headers)
        self.assert200(r.status_code)

        # test that if X_DOMAINS is set to '*', then any Origin value is
        # allowed. Also test that only the Origin header included with the
        # request will be # returned back to the client.
        self.app.config["X_DOMAINS"] = "*"
        r = self.test_client.open(
            url, method="OPTIONS", headers=[("Origin", "http://example.com")]
        )
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://example.com")
        self.assertEqual(r.headers["Vary"], "Origin")
        for m in methods:
            self.assertTrue(m in r.headers["Access-Control-Allow-Methods"])

        # Given that CORS is activated with X_DOMAINS = '*'
        # test that if X_ALLOW_CREDENTIALS is set to True
        # then the relevant header is included in the response
        self.app.config["X_ALLOW_CREDENTIALS"] = True
        r = self.test_client.open(
            url, method="OPTIONS", headers=[("Origin", "http://example.com")]
        )
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Credentials"], "true")

        # with any other non-True value, it is missing
        self.app.config["X_ALLOW_CREDENTIALS"] = False
        r = self.test_client.open(
            url, method="OPTIONS", headers=[("Origin", "http://example.com")]
        )
        self.assert200(r.status_code)
        self.assertFalse("Access-Control-Allow-Credentials" in r.headers)

        self.app.config["X_DOMAINS"] = ["http://1of2.com", "http://2of2.com"]
        r = self.test_client.open(
            url, method="OPTIONS", headers=[("Origin", "http://1of2.com")]
        )
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://1of2.com")
        r = self.test_client.open(
            url, method="OPTIONS", headers=[("Origin", "http://2of2.com")]
        )
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://2of2.com")

        for m in methods:
            self.assertTrue(m in r.headers["Access-Control-Allow-Methods"])

        self.assertTrue("Access-Control-Allow-Origin" in r.headers)
        self.assertTrue("Access-Control-Max-Age" in r.headers)
        self.assertTrue("Access-Control-Expose-Headers" in r.headers)

        r = self.test_client.get(url, headers=[("Origin", "http://not_an_example.com")])
        self.assert200(r.status_code)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "")
        for m in methods:
            self.assertTrue(m in r.headers["Access-Control-Allow-Methods"])

    def test_CORS_OPTIONS_resources(self):
        prefix = api_prefix(
            self.app.config["URL_PREFIX"], self.app.config["API_VERSION"]
        )

        del self.domain["peopleinvoices"]
        del self.domain["peoplerequiredinvoices"]
        del self.domain["peoplesearches"]
        del self.domain["internal_transactions"]
        del self.domain["child_products"]
        for _, settings in self.app.config["DOMAIN"].items():
            # resource endpoint
            url = "%s/%s/" % (prefix, settings["url"])
            methods = settings["resource_methods"] + ["OPTIONS"]
            self.test_CORS_OPTIONS(url, methods)

    def test_CORS_OPTIONS_item(self):
        prefix = api_prefix(
            self.app.config["URL_PREFIX"], self.app.config["API_VERSION"]
        )

        url = "%s%s" % (prefix, self.item_id_url)
        methods = self.domain[self.known_resource]["resource_methods"] + ["OPTIONS"]
        self.test_CORS_OPTIONS(url, methods)
        url = "%s%s/%s" % (prefix, self.known_resource_url, self.item_ref)
        methods = ["GET", "OPTIONS"]

    def test_CORS_OPTIONS_schema(self):
        """ Test that CORS is also supported at SCHEMA_ENDPOINT """
        self.app.config["SCHEMA_ENDPOINT"] = "schema"
        self.app._init_schema_endpoint()
        methods = ["GET", "OPTIONS"]
        self.test_CORS_OPTIONS("schema", methods)

    def test_deprecated_renderers_supports_py27(self):
        """ Make sure #1175 is fixed """
        self.app.config["RENDERES"] = False
        try:
            self.app.check_deprecated_features()
        except AttributeError:
            self.fail("AttributeError raised unexpectedly.")
