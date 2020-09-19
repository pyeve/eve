# -*- coding: utf-8 -*-
import simplejson as json

from bson import ObjectId

import eve
from eve import Eve
from eve.auth import BasicAuth, TokenAuth, HMACAuth
from eve.tests import TestBase
from eve.tests.test_settings import MONGO_DBNAME
from io import BytesIO


class ValidBasicAuth(BasicAuth):
    def __init__(self):
        self.request_auth_value = "admin"
        super(ValidBasicAuth, self).__init__()

    def check_auth(self, username, password, allowed_roles, resource, method):
        self.set_request_auth_value(self.request_auth_value)
        return (
            username in ("admin", "alt")
            and password == "secret"
            and ("admin" in allowed_roles if allowed_roles else True)
        )


class BadBasicAuth(BasicAuth):
    pass


class ValidTokenAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        return token == "test_token" and (
            "admin" in allowed_roles if allowed_roles else True
        )


class BadTokenAuth(TokenAuth):
    pass


class ValidHMACAuth(HMACAuth):
    def check_auth(
        self, userid, hmac_hash, headers, data, allowed_roles, resource, method
    ):
        self.set_request_auth_value(userid)
        return (
            userid == "admin"
            and hmac_hash == "secret"
            and ("admin" in allowed_roles if allowed_roles else True)
        )


class BadHMACAuth(HMACAuth):
    pass


class TestBasicAuth(TestBase):
    def setUp(self):
        super(TestBasicAuth, self).setUp()
        self.app = Eve(settings=self.settings_file, auth=ValidBasicAuth)
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")
        self.valid_auth = [
            ("Authorization", "Basic YWRtaW46c2VjcmV0"),
            self.content_type,
        ]
        self.invalid_auth = [
            ("Authorization", "Basic YWRtaW46c2VjcmV1"),
            self.content_type,
        ]
        self.valid_media_auth = [
            ("Authorization", "Basic YWRtaW46c2VjcmV0"),
            ("Content-Type", "multipart/form-data"),
        ]
        self.setUpRoles()
        self.app.set_defaults()

    def setUpRoles(self):
        for _, schema in self.app.config["DOMAIN"].items():
            schema["allowed_roles"] = ["admin"]
            schema["allowed_read_roles"] = ["reader"]
            schema["allowed_item_roles"] = ["admin"]
            schema["allowed_item_read_roles"] = ["reader"]
            schema["allowed_item_write_roles"] = ["editor"]

    def test_custom_auth(self):
        self.assertTrue(isinstance(self.app.auth, ValidBasicAuth))

    def test_restricted_home_access(self):
        r = self.test_client.get("/")
        self.assert401(r.status_code)

    def test_restricted_resource_access(self):
        r = self.test_client.get(self.known_resource_url)
        self.assert401(r.status_code)
        r = self.test_client.post(self.known_resource_url)
        self.assert401(r.status_code)
        r = self.test_client.delete(self.known_resource_url)
        self.assert401(r.status_code)

    def test_restricted_item_access(self):
        r = self.test_client.get(self.item_id_url)
        self.assert401(r.status_code)
        r = self.test_client.patch(self.item_id_url)
        self.assert401(r.status_code)
        r = self.test_client.delete(self.item_id_url)
        self.assert401(r.status_code)

    def test_authorized_home_access(self):
        r = self.test_client.get("/", headers=self.valid_auth)
        self.assert200(r.status_code)

    def test_authorized_resource_access(self):
        r = self.test_client.get(self.known_resource_url, headers=self.valid_auth)
        self.assert200(r.status_code)
        r = self.test_client.post(
            self.known_resource_url,
            data=json.dumps({"k": "value"}),
            headers=self.valid_auth,
        )
        self.assertValidationErrorStatus(r.status_code)
        r = self.test_client.delete(self.known_resource_url, headers=self.valid_auth)
        self.assert204(r.status_code)

    def test_authorized_item_access(self):
        r = self.test_client.get(self.item_id_url, headers=self.valid_auth)
        self.assert200(r.status_code)
        r = self.test_client.patch(
            self.item_id_url, data=json.dumps({"k": "value"}), headers=self.valid_auth
        )
        self.assert428(r.status_code)
        r = self.test_client.delete(self.item_id_url, headers=self.valid_auth)
        self.assert428(r.status_code)

    def test_authorized_media_access(self):
        self.app.config["RETURN_MEDIA_AS_BASE64_STRING"] = False
        self.app.config["RETURN_MEDIA_AS_URL"] = True
        self.app.config["BANDWIDTH_SAVER"] = False
        self.app._init_media_endpoint()

        clean = b"my new file contents"
        test_field, test_value = "ref", "9234567890123456789054321"
        data = {"media": (BytesIO(clean), "test.txt"), test_field: test_value}
        r, s = self.parse_response(
            self.test_client.post(
                self.known_resource_url, data=data, headers=self.valid_media_auth
            )
        )
        self.assert201(s)

        file_url = r["media"]
        r = self.test_client.get(file_url, headers=self.invalid_auth)
        self.assert401(r.status_code)
        r = self.test_client.get(file_url, headers=self.valid_auth)
        self.assert200(r.status_code)

    def test_authorized_schema_access(self):
        self.app.config["SCHEMA_ENDPOINT"] = "schema"
        self.app._init_schema_endpoint()

        r = self.test_client.get(
            "/schema/%s" % self.known_resource, headers=self.valid_auth
        )
        self.assert200(r.status_code)

    def test_unauthorized_home_access(self):
        r = self.test_client.get("/", headers=self.invalid_auth)
        self.assert401(r.status_code)

    def test_unauthorized_resource_access(self):
        r = self.test_client.get(self.known_resource_url, headers=self.invalid_auth)
        self.assert401(r.status_code)
        r = self.test_client.post(self.known_resource_url, headers=self.invalid_auth)
        self.assert401(r.status_code)
        r = self.test_client.delete(self.known_resource_url, headers=self.invalid_auth)
        self.assert401(r.status_code)

    def test_unauthorized_item_access(self):
        r = self.test_client.get(self.item_id_url, headers=self.invalid_auth)
        self.assert401(r.status_code)
        r = self.test_client.patch(self.item_id_url, headers=self.invalid_auth)
        self.assert401(r.status_code)
        r = self.test_client.delete(self.item_id_url, headers=self.invalid_auth)
        self.assert401(r.status_code)

    def test_unauthorized_schema_access(self):
        self.app.config["SCHEMA_ENDPOINT"] = "schema"
        self.app._init_schema_endpoint()

        r = self.test_client.get(
            "/schema/%s" % self.known_resource, headers=self.invalid_auth
        )
        self.assert401(r.status_code)

    def test_home_public_methods(self):
        self.app.config["PUBLIC_METHODS"] = ["GET"]
        r = self.test_client.get("/")
        self.assert200(r.status_code)
        self.test_restricted_resource_access()
        self.test_restricted_item_access()

    def test_public_methods_resource(self):
        self.app.config["PUBLIC_METHODS"] = ["GET"]
        domain = self.app.config["DOMAIN"]
        for resource, settings in domain.items():
            del settings["public_methods"]
        self.app.set_defaults()
        del domain["peopleinvoices"]
        del domain["peoplerequiredinvoices"]
        del domain["peoplesearches"]
        del domain["internal_transactions"]
        del domain["child_products"]
        for resource in domain:
            url = self.app.config["URLS"][resource]
            r = self.test_client.get(url)
            self.assert200(r.status_code)
            r = self.test_client.post(url, data={"key1": "value1"})
            self.assert401or405(r.status_code)
            r = self.test_client.delete(url)
            self.assert401or405(r.status_code)
        self.test_restricted_item_access()

    def test_public_methods_but_locked_resource(self):
        self.app.config["PUBLIC_METHODS"] = ["GET"]
        domain = self.app.config["DOMAIN"]
        for _, settings in domain.items():
            del settings["public_methods"]
        self.app.set_defaults()
        domain[self.known_resource]["public_methods"] = []
        r = self.test_client.get(self.known_resource_url)
        self.assert401(r.status_code)

    def test_public_methods_but_locked_item(self):
        self.app.config["PUBLIC_ITEM_METHODS"] = ["GET"]
        domain = self.app.config["DOMAIN"]
        for _, settings in domain.items():
            del settings["public_item_methods"]
        self.app.set_defaults()
        domain[self.known_resource]["public_item_methods"] = []
        r = self.test_client.get(self.item_id_url)
        self.assert401(r.status_code)

    def test_public_methods_item(self):
        self.app.config["PUBLIC_ITEM_METHODS"] = ["GET"]
        for _, settings in self.app.config["DOMAIN"].items():
            del settings["public_item_methods"]
        self.app.set_defaults()
        # we're happy with testing just one client endpoint, but for sake of
        # completeness we shold probably test item endpoints for every resource
        r = self.test_client.get(self.item_id_url)
        self.assert200(r.status_code)
        r = self.test_client.patch(self.item_id_url)
        self.assert401(r.status_code)
        r = self.test_client.delete(self.item_id_url)
        self.assert401(r.status_code)

    def test_bad_auth_class(self):
        self.app = Eve(settings=self.settings_file, auth=BadBasicAuth)
        self.test_client = self.app.test_client()
        r = self.test_client.get("/", headers=self.valid_auth)
        # will fail because check_auth() is not implemented in the custom class
        self.assert500(r.status_code)

    def test_instanced_auth(self):
        # tests that the 'auth' argument can also be a class instance. See
        # #248.

        # current self.app instance has an instanced auth class already, and it
        # is consistent with the super class running the test (Token, HMAC or
        # Basic), so we are just going to use it (self.app.auth) on a new Eve
        # instance.

        auth = self.app.auth
        self.app = Eve(settings=self.settings_file, auth=auth)
        self.test_client = self.app.test_client()
        r = self.test_client.get("/", headers=self.valid_auth)
        self.assert200(r.status_code)

    def test_rfc2617_response(self):
        r = self.test_client.get("/")
        self.assert401(r.status_code)
        self.assertTrue(
            ("WWW-Authenticate", 'Basic realm="%s"' % eve.__package__)
            in r.headers.to_wsgi_list()
        )

    def test_allowed_roles_does_not_change(self):
        self.test_client.get(self.known_resource_url)
        resource = self.app.config["DOMAIN"][self.known_resource]
        self.assertEqual(resource["allowed_roles"], ["admin"])

    def test_allowed_item_roles_does_not_change(self):
        self.test_client.get(self.item_id_url)
        resource = self.app.config["DOMAIN"][self.known_resource]
        self.assertEqual(resource["allowed_item_roles"], ["admin"])

    def test_ALLOWED_ROLES_does_not_change(self):
        self.app.config["ALLOWED_ROLES"] = ["admin"]
        self.app.config["ALLOWED_READ_ROLES"] = ["reader"]
        self.test_client.get("/")
        self.assertEqual(self.app.config["ALLOWED_ROLES"], ["admin"])


class TestTokenAuth(TestBasicAuth):
    def setUp(self):
        super(TestTokenAuth, self).setUp()
        self.app = Eve(settings=self.settings_file, auth=ValidTokenAuth)
        self.test_client = self.app.test_client()
        self.valid_auth = [
            ("Authorization", "Basic dGVzdF90b2tlbjo="),
            self.content_type,
        ]
        self.valid_media_auth = [
            ("Authorization", "Basic dGVzdF90b2tlbjo="),
            ("Content-Type", "multipart/form-data"),
        ]
        self.setUpRoles()

    def test_custom_auth(self):
        self.assertTrue(isinstance(self.app.auth, ValidTokenAuth))


class TestBearerTokenAuth(TestTokenAuth):
    def setUp(self):
        super(TestBearerTokenAuth, self).setUp()
        self.valid_auth = [("Authorization", "Token test_token"), self.content_type]
        self.valid_media_auth = [
            ("Authorization", "Token test_token"),
            ("Content-Type", "multipart/form-data"),
        ]

    def test_bad_auth_class(self):
        self.app = Eve(settings=self.settings_file, auth=BadTokenAuth)
        self.test_client = self.app.test_client()
        r = self.test_client.get("/", headers=self.valid_auth)
        # will fail because check_auth() is not implemented in the custom class
        self.assert500(r.status_code)


class TestCustomTokenAuth(TestTokenAuth):
    def setUp(self):
        super(TestCustomTokenAuth, self).setUp()
        self.valid_auth = [("Authorization", "Token test_token"), self.content_type]
        self.valid_media_auth = [
            ("Authorization", "Token test_token"),
            ("Content-Type", "multipart/form-data"),
        ]

    def test_bad_auth_class(self):
        self.app = Eve(settings=self.settings_file, auth=BadTokenAuth)
        self.test_client = self.app.test_client()
        r = self.test_client.get("/", headers=self.valid_auth)
        # will fail because check_auth() is not implemented in the custom class
        self.assert500(r.status_code)


class TestHMACAuth(TestBasicAuth):
    def setUp(self):
        super(TestHMACAuth, self).setUp()
        self.app = Eve(settings=self.settings_file, auth=ValidHMACAuth)
        self.test_client = self.app.test_client()
        self.valid_auth = [("Authorization", "admin:secret"), self.content_type]
        self.valid_media_auth = [
            ("Authorization", "admin:secret"),
            ("Content-Type", "multipart/form-data"),
        ]
        self.setUpRoles()

    def test_custom_auth(self):
        self.assertTrue(isinstance(self.app.auth, ValidHMACAuth))

    def test_bad_auth_class(self):
        self.app = Eve(settings=self.settings_file, auth=BadHMACAuth)
        self.test_client = self.app.test_client()
        r = self.test_client.get("/", headers=self.valid_auth)
        # will fail because check_auth() is not implemented in the custom class
        self.assert500(r.status_code)

    def test_rfc2617_response(self):
        r = self.test_client.get("/")
        self.assert401(r.status_code)

    def test_post_resource_hmac_auth(self):
        # Test that user restricted access works with HMAC auth.
        resource_def = self.app.config["DOMAIN"]["restricted"]
        resource_def["auth_field"] = "username"
        url = resource_def["url"]
        data = {"ref": "0123456789123456789012345"}

        r = self.app.test_client().post(
            url,
            data=json.dumps(data),
            headers=self.valid_auth,
            content_type="application/json",
        )

        # Verify that we can retrieve the same document
        r, status = self.parse_response(
            self.app.test_client().get(url, headers=self.valid_auth)
        )
        self.assert200(status)
        self.assertEqual(len(r["_items"]), 1)
        self.assertEqual(r["_items"][0]["ref"], data["ref"])


class TestResourceAuth(TestBase):
    def test_resource_only_auth(self):
        # no auth at the API level
        self.app = Eve(settings=self.settings_file)
        self.test_client = self.app.test_client()
        # explicit auth for just one resource
        self.app.config["DOMAIN"]["contacts"]["authentication"] = ValidBasicAuth()
        self.app.config["DOMAIN"]["empty"]["authentication"] = ValidTokenAuth()
        self.app.set_defaults()
        basic_auth = [("Authorization", "Basic YWRtaW46c2VjcmV0")]
        token_auth = [("Authorization", "Basic dGVzdF90b2tlbjo=")]

        # 'contacts' endpoints are protected
        r = self.test_client.get(self.known_resource_url)
        self.assert401(r.status_code)
        r = self.test_client.get(self.item_id_url)
        self.assert401(r.status_code)
        # both with BasicAuth.
        _, status = self.parse_response(
            self.test_client.get(self.known_resource_url, headers=basic_auth)
        )
        self.assert200(status)
        _, status = self.parse_response(
            self.test_client.get(self.item_id_url, headers=basic_auth)
        )
        self.assert200(status)

        # 'empty' resource endpoint is also protected
        r = self.test_client.get(self.empty_resource_url)
        self.assert401(r.status_code)
        # but with TokenAuth
        r = self.test_client.get(self.empty_resource_url, headers=token_auth)
        self.assert200(r.status_code)

        # other resources are not protected
        r = self.test_client.get(self.readonly_resource_url)
        self.assert200(r.status_code)


class TestUserRestrictedAccess(TestBase):
    def setUp(self):
        super(TestUserRestrictedAccess, self).setUp()

        self.app = Eve(settings=self.settings_file, auth=ValidBasicAuth)

        # using this endpoint since it is a copy of 'contacts' with
        # no filter on the datasource
        self.url = "restricted"
        self.resource = self.app.config["DOMAIN"][self.url]
        self.test_client = self.app.test_client()

        self.valid_auth = [("Authorization", "Basic YWRtaW46c2VjcmV0")]
        self.invalid_auth = [("Authorization", "Basic IDontThinkSo")]
        self.field_name = "auth_field"
        self.data = json.dumps({"ref": "0123456789123456789012345"})

        for _, settings in self.app.config["DOMAIN"].items():
            settings[self.field_name] = "username"

        self.resource["public_methods"] = []

    def test_get(self):
        data, status = self.parse_response(
            self.test_client.get(self.url, headers=self.valid_auth)
        )
        self.assert200(status)
        # no data has been saved by user 'admin' yet,
        # so assert we get an empty result set back.
        self.assertEqual(len(data["_items"]), 0)

        # Add a user belonging to `admin`
        new_user = self.random_contacts(1)[0]
        new_user["username"] = "admin"
        _db = self.connection[self.app.config["MONGO_DBNAME"]]
        _db.contacts.insert_one(new_user)

        # Verify that we can retrieve it
        data2, status2 = self.parse_response(
            self.test_client.get(self.url, headers=self.valid_auth)
        )
        self.assert200(status2)
        self.assertEqual(len(data2["_items"]), 1)

    def test_get_by_auth_field_criteria(self):
        """If we attempt to retrieve an object by the same field
        that is in `auth_field`, then the request is /unauthorized/,
        and should fail and return 401.

        This test verifies that the `auth_field` does not overwrite
        a `client_filter` or url param.
        """
        _, status = self.parse_response(
            self.test_client.get(self.user_username_url, headers=self.valid_auth)
        )
        self.assert401(status)

    def test_get_by_auth_field_id(self):
        """To test handling of ObjectIds"""
        # set auth_field to `_id`
        self.domain["users"][self.field_name] = self.domain["users"]["id_field"]

        _, status = self.parse_response(
            self.test_client.get(self.user_id_url, headers=self.valid_auth)
        )
        self.assert401(status)

    def test_filter_by_auth_field_id(self):
        """To test handling of ObjectIds when using a `where` clause
        We need to make sure we *match* an object ID when it is the
        same
        """
        _id = ObjectId("deadbeefdeadbeefdeadbeef")
        resource_def = self.app.config["DOMAIN"]["users"]
        resource_def["authentication"].request_auth_value = _id

        # set auth_field to `_id`
        resource_def[self.field_name] = "_id"

        # Retrieving a /different user/ by id returns 401
        user_url = "/users/"
        filter_by_id = 'where=_id==ObjectId("%s")'
        filter_query = filter_by_id % self.user_id

        _, status = self.parse_response(
            self.test_client.get(
                "%s?%s" % (user_url, filter_query), headers=self.valid_auth
            )
        )
        self.assert401(status)

        # Create a user account belonging to admin
        new_user = self.random_contacts(1)[0]
        new_user["_id"] = _id
        new_user["username"] = "admin"
        _db = self.connection[self.app.config["MONGO_DBNAME"]]
        _db.contacts.insert_one(new_user)

        # Retrieving /the same/ user by id returns OK
        filter_query_2 = filter_by_id % "deadbeefdeadbeefdeadbeef"
        data2, status2 = self.parse_response(
            self.test_client.get(
                "%s?%s" % (user_url, filter_query_2), headers=self.valid_auth
            )
        )
        self.assert200(status2)
        self.assertEqual(len(data2["_items"]), 1)

    def test_collection_get_public(self):
        """Test that if GET is in `public_methods` the `auth_field`
        criteria is overruled
        """
        self.resource["public_methods"].append("GET")
        data, status = self.parse_response(self.test_client.get(self.url))  # no auth
        self.assert200(status)
        # no data has been saved by user 'admin' yet,
        # but we should get all the other results back
        self.assertEqual(len(data["_items"]), 25)

    def test_item_get_public(self):
        """Test that if GET is in `public_item_methods` the `auth_field`
        criteria is overruled
        """
        self.resource["public_item_methods"].append("GET")
        data, status = self.parse_response(
            self.test_client.get(self.item_id_url, headers=self.valid_auth)
        )
        self.assert200(status)
        self.assertEqual(data["_id"], self.item_id)

    def test_post(self):
        _, status = self.post()
        self.assert201(status)
        data, status = self.parse_response(
            self.test_client.get(self.url, headers=self.valid_auth)
        )
        self.assert200(status)
        # len of 1 as there are is only 1 doc saved by user

    def test_unique_to_user_on_post(self):
        # make the field unique to user, not globally.
        self.resource["schema"]["ref"]["unique"] = False
        self.resource["schema"]["ref"]["unique_to_user"] = True

        # first post as 'admin' is a success.
        _, status = self.post()
        self.assert201(status)

        # second post as 'admin' fails since value is not unique to user.
        _, status = self.post()
        self.assert422(status)

        self.resource["authentication"].request_auth_value = "alt"
        # first post as 'alt' succeeds as value is unique to this user.
        alt_auth = [("Authorization", "Basic YWx0OnNlY3JldA==")]
        r = self.test_client.post(
            self.url, data=self.data, headers=alt_auth, content_type="application/json"
        )

        self.assert201(r.status_code)

        # second post as 'alt' fails since value is not unique to user anymore.
        r = self.test_client.post(
            self.url, data=self.data, headers=alt_auth, content_type="application/json"
        )

        # post succeeds since value is unique to 'alt' user
        self.assert422(r.status_code)

    def test_post_resource_auth(self):
        # Ticket #231.
        # Test that user restricted access works fine if there's no global
        # level auth, which is set at resource level instead.

        # no global auth.
        self.app = Eve(settings=self.settings_file)

        # set auth at resource level instead.
        resource_def = self.app.config["DOMAIN"][self.url]
        resource_def["authentication"] = ValidBasicAuth
        resource_def["auth_field"] = "username"

        # post with valid auth - must store the document with the correct
        # auth_field.
        r = self.app.test_client().post(
            self.url,
            data=self.data,
            headers=self.valid_auth,
            content_type="application/json",
        )
        _, status = self.parse_response(r)

        # Verify that we can retrieve the same document
        data, status = self.parse_response(
            self.app.test_client().get(self.url, headers=self.valid_auth)
        )
        self.assert200(status)
        self.assertEqual(len(data["_items"]), 1)
        self.assertEqual(data["_items"][0]["ref"], json.loads(self.data)["ref"])

    def test_post_bandwidth_saver_off_resource_auth(self):
        """Test that when BANDWIDTH_SAVER is turned off the auth_field is
        not exposed in the response payload
        """
        self.app.config["BANDWIDTH_SAVER"] = False
        r = self.app.test_client().post(
            self.url,
            data=self.data,
            headers=self.valid_auth,
            content_type="application/json",
        )
        r, status = self.parse_response(r)
        self.assertTrue("username" not in r)

    def test_put(self):
        new_ref = "9999999999999999999999999"
        changes = json.dumps({"ref": new_ref})

        # post document
        data, status = self.post()

        # retrieve document metadata
        url = "%s/%s" % (self.url, data["_id"])
        response = self.test_client.get(url, headers=self.valid_auth)
        etag = response.headers["ETag"]

        # perform put
        headers = [("If-Match", etag), self.valid_auth[0]]
        response, status = self.parse_response(
            self.test_client.put(
                url,
                data=json.dumps(changes),
                headers=headers,
                content_type="application/json",
            )
        )
        self.assert200(status)
        etag = '"%s"' % response["_etag"]

        # document still accessible with same auth
        data, status = self.parse_response(
            self.test_client.get(url, headers=self.valid_auth)
        )
        self.assert200(status)
        self.assertEqual(data["ref"], new_ref)

        # put on same item with different auth fails
        original_auth_val = self.resource["authentication"].request_auth_value
        self.resource["authentication"].request_auth_value = "alt"
        alt_auth = ("Authorization", "Basic YWx0OnNlY3JldA==")
        alt_changes = {"ref": "1111111111111111111111111"}
        headers = [("If-Match", etag), alt_auth]
        response, status = self.parse_response(
            self.test_client.put(
                url,
                data=json.dumps(alt_changes),
                headers=headers,
                content_type="application/json",
            )
        )
        self.assert403(status)

        # document still accessible with original auth
        self.resource["authentication"].request_auth_value = original_auth_val
        data, status = self.parse_response(
            self.test_client.get(url, headers=self.valid_auth)
        )
        self.assert200(status)
        self.assertEqual(data["ref"], new_ref)

    def test_put_resource_auth(self):
        # no global auth.
        self.app = Eve(settings=self.settings_file)

        # set auth at resource level instead.
        resource_def = self.app.config["DOMAIN"][self.url]
        resource_def["authentication"] = ValidBasicAuth
        resource_def["auth_field"] = "username"

        # post
        r = self.app.test_client().post(
            self.url,
            data=self.data,
            headers=self.valid_auth,
            content_type="application/json",
        )
        data, status = self.parse_response(r)

        # retrieve document metadata
        url = "%s/%s" % (self.url, data["_id"])
        response = self.app.test_client().get(url, headers=self.valid_auth)
        etag = response.headers["ETag"]

        new_ref = "9999999999999999999999999"
        changes = json.dumps({"ref": new_ref})

        # put
        headers = [("If-Match", etag), self.valid_auth[0]]
        response, status = self.parse_response(
            self.app.test_client().put(
                url,
                data=json.dumps(changes),
                headers=headers,
                content_type="application/json",
            )
        )
        self.assert200(status)
        etag = '"%s"' % response["_etag"]

        # document still accessible with same auth
        data, status = self.parse_response(
            self.app.test_client().get(url, headers=self.valid_auth)
        )
        self.assert200(status)
        self.assertEqual(data["ref"], new_ref)

        # put on same item with different auth fails
        original_auth_val = resource_def["authentication"].request_auth_value
        resource_def["authentication"].request_auth_value = "alt"
        alt_auth = ("Authorization", "Basic YWx0OnNlY3JldA==")
        alt_changes = {"ref": "1111111111111111111111111"}
        headers = [("If-Match", etag), alt_auth]
        response, status = self.parse_response(
            self.app.test_client().put(
                url,
                data=json.dumps(alt_changes),
                headers=headers,
                content_type="application/json",
            )
        )
        self.assert403(status)

        # document still accessible with original auth
        resource_def["authentication"].request_auth_value = original_auth_val
        data, status = self.parse_response(
            self.app.test_client().get(url, headers=self.valid_auth)
        )
        self.assert200(status)
        self.assertEqual(data["ref"], new_ref)

    def test_put_bandwidth_saver_off_resource_auth(self):
        """Test that when BANDWIDTH_SAVER is turned off the auth_field is
        not exposed in the response payload
        """
        self.app.config["BANDWIDTH_SAVER"] = False

        new_ref = "9999999999999999999999999"
        changes = json.dumps({"ref": new_ref})

        # post document
        data, status = self.post()

        url = "%s/%s" % (self.url, data["_id"])

        # perform put
        headers = [("If-Match", data["_etag"]), self.valid_auth[0]]
        response, status = self.parse_response(
            self.test_client.put(
                url,
                data=json.dumps(changes),
                headers=headers,
                content_type="application/json",
            )
        )
        self.assertTrue("username" not in response)

    def test_patch(self):
        new_ref = "9999999999999999999999999"
        changes = json.dumps({"ref": new_ref})
        data, status = self.post()
        url = "%s/%s" % (self.url, data["_id"])
        response = self.test_client.get(url, headers=self.valid_auth)
        etag = response.headers["ETag"]
        headers = [("If-Match", etag), self.valid_auth[0]]
        response, status = self.parse_response(
            self.test_client.patch(
                url,
                data=json.dumps(changes),
                headers=headers,
                content_type="application/json",
            )
        )
        self.assert200(status)

        data, status = self.parse_response(
            self.test_client.get(url, headers=self.valid_auth)
        )
        self.assert200(status)
        self.assertEqual(data["ref"], new_ref)

    def test_delete(self):
        _db = self.connection[MONGO_DBNAME]

        # make sure that other documents in the collections are untouched.
        _db.contacts.find()
        docs_num = _db.contacts.count_documents({})

        _, _ = self.post()

        # after the post we only get back 1 document as it's the only one we
        # inserted directly (others are filtered out).
        response, status = self.parse_response(
            self.test_client.get(self.url, headers=self.valid_auth)
        )
        self.assert200(status)
        self.assertEqual(len(response[self.app.config["ITEMS"]]), 1)

        # delete the document we just inserted
        response, status = self.parse_response(
            self.test_client.delete(self.url, headers=self.valid_auth)
        )
        self.assert204(status)

        # we now get an empty items list (other documents in collection are
        # filtered by auth).
        response, status = self.parse_response(
            self.test_client.get(self.url, headers=self.valid_auth)
        )
        self.assert200(status)
        # if it's a dict, we only got 1 item back which is expected
        self.assertEqual(len(response[self.app.config["ITEMS"]]), 0)

        # make sure no other document has been deleted.
        self.assertEqual(_db.contacts.count_documents({}), docs_num)

    def test_delete_item(self):
        _db = self.connection[MONGO_DBNAME]

        # make sure that other documents in the collections are untouched.
        docs_num = _db.contacts.count_documents({})

        data, _ = self.post()

        # get back the document with its new etag
        url = "%s/%s" % (self.url, data["_id"])
        response = self.test_client.get(url, headers=self.valid_auth)
        etag = response.headers["ETag"]
        headers = [("If-Match", etag), ("Authorization", "Basic YWRtaW46c2VjcmV0")]

        # delete the document
        response, status = self.parse_response(
            self.test_client.delete(url, headers=headers)
        )
        self.assert204(status)

        # make sure no other document has been deleted.
        self.assertEqual(_db.contacts.count_documents({}), docs_num)

    def test_delete_item_soft_delete_enabled(self):
        self.app.config["DOMAIN"]["restricted"]["soft_delete"] = True
        _db = self.connection[MONGO_DBNAME]
        docs_num = _db.contacts.count_documents({})

        data, _ = self.post()

        url = "%s/%s" % (self.url, data["_id"])
        response = self.test_client.get(url, headers=self.valid_auth)
        etag = response.headers["ETag"]
        headers = [("If-Match", etag), ("Authorization", "Basic YWRtaW46c2VjcmV0")]

        # delete the document
        response, status = self.parse_response(
            self.test_client.delete(url, headers=headers)
        )
        self.assert204(status)

        # make sure no other document has been deleted.
        self.assertEqual(
            _db.contacts.count_documents({"_deleted": {"$ne": True}}), docs_num
        )
        self.assertEqual(_db.contacts.count_documents({"_deleted": True}), 1)

        challenge = _db.contacts.find_one({"_deleted": True})
        self.assertEqual(challenge["username"], "admin")

    def post(self):
        r = self.test_client.post(
            self.url,
            data=self.data,
            headers=self.valid_auth,
            content_type="application/json",
        )
        return self.parse_response(r)
