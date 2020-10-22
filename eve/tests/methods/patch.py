import simplejson as json

from bson import ObjectId
from pymongo import ReadPreference

from eve import ETAG
from eve import ISSUES
from eve import LAST_UPDATED
from eve import STATUS
from eve import STATUS_OK
from eve.methods.patch import patch_internal
from eve.tests import TestBase
from eve.tests.test_settings import MONGO_DBNAME
from eve.tests.utils import DummyEvent


class TestPatch(TestBase):
    def test_patch_not_override_other_fields(self):
        self.app.config["ENFORCE_IF_MATCH"] = False
        # create a data
        r, status = self.post(self.test_patch_url, data={"name": "name", "contact": {}})
        self.assert201(status)
        # check the data is created correctly
        data, status = self.get(self.test_patch, item=r["_id"])
        self.assert200(status)

        # patch the data
        _, status = self.patch(
            self.test_patch_url + "/" + data["_id"], data={"contact.phone": "new_phone"}
        )
        self.assert200(status)
        # other fields should not be touched
        data, status = self.get(self.test_patch, item=r["_id"])
        self.assert200(status)
        self.assertEqual(data["name"], "name")
        self.assertTrue("contact" in data)
        self.assertEqual(data["contact"]["phone"], "new_phone")
        self.assertEqual(data["contact"]["email"], "default_email")

        # patch other field of the data
        _, status = self.patch(
            self.test_patch_url + "/" + data["_id"], data={"contact.email": "new_email"}
        )
        self.assert200(status)
        # other fields should not be touched
        data, status = self.get(self.test_patch, item=r["_id"])
        self.assert200(status)
        self.assertEqual(data["name"], "name")
        self.assertTrue("contact" in data)
        self.assertEqual(data["contact"]["phone"], "new_phone")
        self.assertEqual(data["contact"]["email"], "new_email")

    def test_patch_to_resource_endpoint(self):
        _, status = self.patch(self.known_resource_url, data={})
        self.assert405(status)

    def test_readonly_resource(self):
        _, status = self.patch(self.readonly_id_url, data={})
        self.assert405(status)

    def test_unknown_id(self):
        _, status = self.patch(self.unknown_item_id_url, data={"key1": "value1"})
        self.assert404(status)

    def test_unknown_id_different_resource(self):
        # patching a 'user' with a valid 'contact' id will 404
        _, status = self.patch(
            "%s/%s/" % (self.different_resource, self.item_id), data={"key1": "value1"}
        )
        self.assert404(status)

        # of course we can still patch a 'user'
        _, status = self.patch(
            "%s/%s/" % (self.different_resource, self.user_id),
            data={"key1": '{"username": "username1"}'},
            headers=[("If-Match", self.user_etag)],
        )
        self.assert200(status)

    def test_by_name(self):
        _, status = self.patch(self.item_name_url, data={"key1": "value1"})
        self.assert405(status)

    def test_ifmatch_missing(self):
        res, status = self.patch(self.item_id_url, data={"key1": "value1"})
        self.assert428(status)

    def test_ifmatch_missing_enforce_ifmatch_disabled(self):
        self.app.config["ENFORCE_IF_MATCH"] = False
        r, status = self.patch(self.item_id_url, data={"key1": "value1"})
        self.assert200(status)
        self.assertTrue(ETAG in r)

    def test_ifmatch_disabled(self):
        self.app.config["IF_MATCH"] = False
        r, status = self.patch(self.item_id_url, data={"key1": "value1"})
        self.assert200(status)
        self.assertTrue(ETAG not in r)

    def test_ifmatch_disabled_enforce_ifmatch_disabled(self):
        self.app.config["ENFORCE_IF_MATCH"] = False
        self.app.config["IF_MATCH"] = False
        r, status = self.patch(self.item_id_url, data={"key1": "value1"})
        self.assert200(status)
        self.assertTrue(ETAG not in r)

    def test_ifmatch_bad_etag(self):
        _, status = self.patch(
            self.item_id_url,
            data={"key1": "value1"},
            headers=[("If-Match", "not-quite-right")],
        )
        self.assert412(status)

    def test_ifmatch_bad_etag_enforce_ifmatch_disabled(self):
        self.app.config["ENFORCE_IF_MATCH"] = False
        _, status = self.patch(
            self.item_id_url,
            data={"key1": "value1"},
            headers=[("If-Match", "not-quite-right")],
        )
        self.assert412(status)

    def test_unique_value(self):
        # TODO
        # for the time being we are happy with testing only Eve's custom
        # validation. We rely on Cerberus' own test suite for other validation
        # unit tests. This test also makes sure that response status is
        # syntactically correct in case of validation issues.
        # We should probably test every single case as well (seems overkill).
        r, status = self.patch(
            self.item_id_url,
            data={"ref": "%s" % self.alt_ref},
            headers=[("If-Match", self.item_etag)],
        )
        self.assertValidationErrorStatus(status)
        self.assertValidationError(
            r, {"ref": "value '%s' is not unique" % self.alt_ref}
        )

    def test_patch_string(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_integer(self):
        field = "prog"
        test_value = 9999
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_list_as_array(self):
        field = "role"
        test_value = ["vendor", "client"]
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertTrue(set(test_value).issubset(db_value))

    def test_patch_rows(self):
        field = "rows"
        test_value = [{"sku": "AT1234", "price": 99}, {"sku": "XF9876", "price": 9999}]
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)

        for test_item in test_value:
            self.assertTrue(test_item in db_value)

    def test_patch_list(self):
        field = "alist"
        test_value = ["a_string", 99]
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_dict(self):
        field = "location"
        test_value = {"address": "an address", "city": "a city"}
        changes = {field: test_value}
        original_city = []

        def keep_original_city(resource_name, updates, original):
            original_city.append(original["location"]["city"])

        self.app.on_update += keep_original_city
        self.app.on_updated += keep_original_city
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)
        self.assertEqual(original_city[0], original_city[1])

    def test_patch_datetime(self):
        field = "born"
        test_value = "Tue, 06 Nov 2012 10:33:31 GMT"
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_objectid(self):
        field = "tid"
        test_value = "4f71c129c88e2018d4000000"
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_null_objectid(self):
        # verify that #341 is fixed.
        field = "tid"
        test_value = None
        changes = {field: test_value}
        r = self.perform_patch(changes)
        db_value = self.compare_patch_with_get(field, r)
        self.assertEqual(db_value, test_value)

    def test_patch_missing_default(self):
        """PATCH an object which is missing a field with a default value.

        This should result in setting the field to its default value, even if
        the field is not provided in the PATCH's payload."""
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {field: test_value}
        r = self.perform_patch(changes)
        self.assertEqual(
            self.compare_patch_with_get("unsetted_default_value_field", r),
            self.domain["contacts"]["schema"]["unsetted_default_value_field"][
                "default"
            ],
        )

    def test_patch_missing_default_with_post_override(self):
        """PATCH an object which is missing a field with a default value.

        This should result in setting the field to its default value, even if
        the field is not provided in the PATCH's payload."""
        field = "ref"
        test_value = "1234567890123456789012345"
        r = self.perform_patch_with_post_override(field, test_value)
        self.assert200(r.status_code)
        unsetted_default_value_field = self.compare_patch_with_get(
            "unsetted_default_value_field", json.loads(r.get_data())
        )
        self.assertEqual(
            unsetted_default_value_field,
            self.domain["contacts"]["schema"]["unsetted_default_value_field"][
                "default"
            ],
        )

    def test_patch_missing_nested_default(self):
        """PATCH an object which is missing a field with a default value.

        This should result in setting the field to its default value, even if
        the field is not provided in the PATCH's payload."""
        field = "dict_with_nested_default"
        test_value = {}
        changes = {field: test_value}
        r = self.perform_patch(changes)

        item_id = r[self.domain[self.known_resource]["id_field"]]
        raw_r = self.test_client.get("%s/%s" % (self.known_resource_url, item_id))
        item, status = self.parse_response(raw_r)
        self.assertEqual(
            item["dict_with_nested_default"], {"nested_field_with_default": "nested"}
        )

    def test_patch_multiple_fields(self):
        fields = ["ref", "prog", "role"]
        test_values = ["9876543210987654321054321", 123, ["agent"]]
        changes = {
            "ref": test_values[0],
            "prog": test_values[1],
            "role": test_values[2],
        }
        r = self.perform_patch(changes)
        db_values = self.compare_patch_with_get(fields, r)
        for i in range(len(db_values)):
            self.assertEqual(db_values[i], test_values[i])

    def test_patch_with_post_override(self):
        # a POST request with PATCH override turns into a PATCH request
        r = self.perform_patch_with_post_override("prog", 1)
        self.assert200(r.status_code)

    def test_patch_internal(self):
        # test that patch_internal is available and working properly.
        test_field = "ref"
        test_value = "9876543210987654321098765"
        data = {test_field: test_value}
        with self.app.test_request_context(self.item_id_url):
            r, _, _, status = patch_internal(
                self.known_resource,
                data,
                concurrency_check=False,
                **{"_id": self.item_id}
            )
        db_value = self.compare_patch_with_get(test_field, r)
        self.assertEqual(db_value, test_value)
        self.assert200(status)

    def test_patch_internal_with_options(self):
        # test that patch_internal is available and working properly.
        test_field = "ref"
        test_value = "9876543210987654321098765"
        data = {test_field: test_value}
        mongo_options = {"read_preference": ReadPreference.PRIMARY}
        with self.app.test_request_context(self.item_id_url):
            r, _, _, status = patch_internal(
                self.known_resource,
                data,
                concurrency_check=False,
                mongo_options=mongo_options,
                **{"_id": self.item_id}
            )
        db_value = self.compare_patch_with_get(test_field, r)
        self.assertEqual(db_value, test_value)
        self.assert200(status)

    def test_patch_etag_header(self):
        # test that Etag is always included with response header. See #562.
        changes = {"ref": "1234567890123456789012345"}
        headers = [("Content-Type", "application/json"), ("If-Match", self.item_etag)]
        r = self.test_client.patch(
            self.item_id_url, data=json.dumps(changes), headers=headers
        )
        self.assertTrue("Etag" in r.headers)

        # test that ETag is compliant to RFC 7232-2.3 and #794 is fixed.
        etag = r.headers["ETag"]

        self.assertTrue(etag[0] == '"')
        self.assertTrue(etag[-1] == '"')

    def test_patch_etag_header_enforce_ifmatch_disabled(self):
        self.app.config["ENFORCE_IF_MATCH"] = False
        changes = {"ref": "1234567890123456789012345"}
        headers = [("Content-Type", "application/json"), ("If-Match", self.item_etag)]
        r, status = self.patch(
            self.item_id_url, data=json.dumps(changes), headers=headers
        )

        self.assertTrue(ETAG in r)
        self.assertTrue(self.item_etag != r[ETAG])

    def test_patch_nested(self):
        changes = {
            "location.city": "a nested city",
            "location.address": "a nested address",
        }
        r = self.perform_patch(changes)
        values = self.compare_patch_with_get("location", r)
        self.assertEqual(values["city"], "a nested city")
        self.assertEqual(values["address"], "a nested address")

    def perform_patch(self, changes):
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assert200(status)
        self.assertPatchResponse(r, self.item_id)
        return r

    def perform_patch_with_post_override(self, field, value):
        headers = [
            ("X-HTTP-Method-Override", "PATCH"),
            ("If-Match", self.item_etag),
            ("Content-Type", "application/json"),
        ]
        return self.test_client.post(
            self.item_id_url, data=json.dumps({field: value}), headers=headers
        )

    def compare_patch_with_get(self, fields, patch_response):
        raw_r = self.test_client.get(self.item_id_url)
        r, status = self.parse_response(raw_r)
        self.assert200(status)
        self.assertEqual(
            raw_r.headers.get("ETag").replace('"', ""), patch_response[ETAG]
        )
        if isinstance(fields, str):
            return r[fields]
        else:
            return [r[field] for field in fields]

    def test_patch_allow_unknown(self):
        changes = {"unknown": "unknown"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {"unknown": "unknown field"})
        self.app.config["DOMAIN"][self.known_resource]["allow_unknown"] = True
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assert200(status)
        self.assertPatchResponse(r, self.item_id)

    def test_patch_x_www_form_urlencoded(self):
        field = "ref"
        test_value = "1234567890123456789012345"
        changes = {field: test_value}
        headers = [("If-Match", self.item_etag)]
        r, status = self.parse_response(
            self.test_client.patch(self.item_id_url, data=changes, headers=headers)
        )
        self.assert200(status)
        self.assertTrue("OK" in r[STATUS])

    def test_patch_x_www_form_urlencoded_number_serialization(self):
        del self.domain["contacts"]["schema"]["ref"]["required"]
        field = "anumber"
        test_value = 3.5
        changes = {field: test_value}
        headers = [("If-Match", self.item_etag)]
        r, status = self.parse_response(
            self.test_client.patch(self.item_id_url, data=changes, headers=headers)
        )
        self.assert200(status)
        self.assertTrue("OK" in r[STATUS])

    def test_patch_referential_integrity(self):
        data = {"person": self.unknown_item_id}
        headers = [("If-Match", self.invoice_etag)]
        r, status = self.patch(self.invoice_id_url, data=data, headers=headers)
        self.assertValidationErrorStatus(status)
        expected = "value '%s' must exist in resource '%s', field '%s'" % (
            self.unknown_item_id,
            "contacts",
            self.domain["contacts"]["id_field"],
        )
        self.assertValidationError(r, {"person": expected})

        data = {"person": self.item_id}
        r, status = self.patch(self.invoice_id_url, data=data, headers=headers)
        self.assert200(status)
        self.assertPatchResponse(r, self.invoice_id)

    def test_patch_write_concern_success(self):
        # 0 and 1 are the only valid values for 'w' on our mongod instance (1
        # is the default)
        self.domain["contacts"]["mongo_write_concern"] = {"w": 0}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {field: test_value}
        _, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assert200(status)

    def test_patch_write_concern_fail(self):
        # should get a 500 since there's no replicaset on the mongod instance
        self.domain["contacts"]["mongo_write_concern"] = {"w": 2}
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {field: test_value}
        _, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assert500(status)

    def test_patch_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        # directly insert a document, without DATE_CREATED e LAST_UPDATED
        # values.
        contacts = self.random_contacts(1, False)
        ref = "test_update_field"
        contacts[0]["ref"] = ref
        _db = self.connection[MONGO_DBNAME]
        _db.contacts.insert_one(contacts[0])

        # now retrieve same document via API and get its etag, which is
        # supposed to be computed on default DATE_CREATED and LAST_UPDATAED
        # values.
        response, status = self.get(self.known_resource, item=ref)
        etag = response[ETAG]
        _id = response["_id"]

        # attempt a PATCH with the new etag.
        field = "ref"
        test_value = "X234567890123456789012345"
        changes = {field: test_value}
        _, status = self.patch(
            "%s/%s" % (self.known_resource_url, _id),
            data=changes,
            headers=[("If-Match", etag)],
        )
        self.assert200(status)

    def test_patch_subresource(self):
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
        etag = response[ETAG]

        data = {"inv_number": "new_number"}
        headers = [("If-Match", etag)]
        response, status = self.patch(
            "users/%s/invoices/%s" % (fake_contact_id, self.invoice_id),
            data=data,
            headers=headers,
        )
        self.assert200(status)
        self.assertPatchResponse(response, self.invoice_id, "peopleinvoices")

    def test_patch_bandwidth_saver(self):
        changes = {"ref": "1234567890123456789012345"}

        # bandwidth_saver is on by default
        self.assertTrue(self.app.config["BANDWIDTH_SAVER"])
        r = self.perform_patch(changes)
        self.assertFalse("ref" in r)
        db_value = self.compare_patch_with_get(self.app.config["ETAG"], r)
        self.assertEqual(db_value, r[self.app.config["ETAG"]])
        self.item_etag = r[self.app.config["ETAG"]]

        # test return all fields (bandwidth_saver off)
        self.app.config["BANDWIDTH_SAVER"] = False
        r = self.perform_patch(changes)
        self.assertTrue("ref" in r)
        db_value = self.compare_patch_with_get(self.app.config["ETAG"], r)
        self.assertEqual(db_value, r[self.app.config["ETAG"]])

    def test_patch_bandwidth_saver_credit_rule_broken(self):
        _db = self.connection[MONGO_DBNAME]
        rule = {
            "amount": 300.0,
            "duration": "months",
            "name": "Testing BANDWIDTH_SAVER=False",
            "start": "2020-03-28T06:00:00 UTC",
        }
        rule_id = _db.credit_rules.insert_one(rule).inserted_id
        rule_url = "credit_rules/%s/" % (rule_id)
        changes = {
            "amount": 120.0,
            "duration": "months",
            "start": "2020-04-01T00:00:00 UTC",
        }
        response, _ = self.get("credit_rules/%s/" % (rule_id))
        etag = response[ETAG]
        # bandwidth_saver is on by default
        self.assertTrue(self.app.config["BANDWIDTH_SAVER"])
        self.assertTrue(self.app.config["PROJECTION"])
        r, status = self.patch(rule_url, data=changes, headers=[("If-Match", etag)])
        self.assert200(status)
        self.assertPatchResponse(r, "%s" % (rule_id))
        self.assertFalse("amount" in r)
        etag = r[self.app.config["ETAG"]]
        r, _ = self.get(rule_url, "")
        self.assertEqual(etag, r[self.app.config["ETAG"]])

        # test return all fields (bandwidth_saver off)
        self.app.config["BANDWIDTH_SAVER"] = False
        changes["name"] = "Give it all to me!"
        r, status = self.patch(rule_url, data=changes, headers=[("If-Match", etag)])
        self.assert200(status)
        self.assertPatchResponse(r, "%s" % (rule_id))
        self.assertTrue(
            all(["amount" in r, "duration" in r, "name" in r, "start" in r]),
            'One or more of "amount", "duration", "name", "start" is missing.',
        )
        self.assertTrue(r["name"] == "Give it all to me!")
        etag = r[self.app.config["ETAG"]]
        r, status = self.get(rule_url, "")
        self.assertEqual(etag, r[self.app.config["ETAG"]])

    def test_patch_readonly_field_with_previous_document(self):
        schema = self.domain["contacts"]["schema"]
        del schema["ref"]["required"]

        # disable read-only on the field so we can store a value which is
        # also different form its default value.
        schema["read_only_field"]["readonly"] = False
        changes = {"read_only_field": "value"}
        r = self.perform_patch(changes)

        # resume read-only status for the field
        self.domain["contacts"]["schema"]["read_only_field"]["readonly"] = True

        # test that if the read-only field is included with the payload and its
        # value is equal to the one stored with the document, validation
        # succeeds (#479).
        etag = r["_etag"]
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", etag)]
        )
        self.assert200(status)
        self.assertPatchResponse(r, self.item_id)

        # test that if the read-only field is included with the payload and its
        # value is different from the stored document, validation fails.
        etag = r["_etag"]
        changes = {"read_only_field": "another value"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", etag)]
        )
        self.assert422(status)
        self.assertTrue("is read-only" in r["_issues"]["read_only_field"])

    def test_patch_nested_document_not_overwritten(self):
        """Test that nested documents are not overwritten on PATCH and #519
        is fixed.
        """

        schema = {
            "sensor": {
                "type": "dict",
                "schema": {
                    "name": {"type": "string"},
                    "lon": {"type": "float"},
                    "lat": {"type": "float"},
                    "value": {"type": "float", "default": 10.3},
                    "dict": {
                        "type": "dict",
                        "schema": {
                            "string": {"type": "string"},
                            "int": {"type": "integer"},
                        },
                    },
                },
            },
            "test": {"type": "string", "readonly": True, "default": "default"},
        }

        self.app.config["BANDWIDTH_SAVER"] = False
        self.app.register_resource("sensors", {"schema": schema})

        changes = {
            "sensor": {
                "name": "device_name",
                "lon": 43.4,
                "lat": 1.31,
                "dict": {"int": 99},
            }
        }
        r, status = self.post("sensors", data=changes)
        self.assert201(status)

        id, etag, value, test, int = (
            r[self.domain["sensors"]["id_field"]],
            r[ETAG],
            r["sensor"]["value"],
            r["test"],
            r["sensor"]["dict"]["int"],
        )

        changes = {"sensor": {"lon": 10.0, "dict": {"string": "hi"}}}

        r, status = self.patch(
            "/%s/%s" % ("sensors", id), data=changes, headers=[("If-Match", etag)]
        )
        self.assert200(status)

        etag, value, int = (r[ETAG], r["sensor"]["value"], r["sensor"]["dict"]["int"])
        self.assertEqual(value, 10.3)
        self.assertEqual(test, "default")
        self.assertEqual(int, 99)

    def test_patch_nested_document_no_merge(self):
        """Test that nested documents are not merged, but overwritten,
        if configured."""
        domain = {
            "merge_nested_documents": False,
            "schema": {"nested": {"type": "dict"}},
        }
        self.app.config["BANDWIDTH_SAVER"] = False
        self.app.register_resource("nomerge", domain)

        original = {"nested": {"key1": "value1", "key2": "value2"}}
        changes = {"nested": {"key2": "value2", "key3": "value3"}}

        r, status = self.post("nomerge", data=original)
        self.assert201(status)

        id = r["_id"]
        etag = r["_etag"]

        r, status = self.patch(
            "/%s/%s" % ("nomerge", id), data=changes, headers=[("If-Match", etag)]
        )
        self.assert200(status)

        # Assert that nested document was completely overwritten
        self.assertEqual(r["nested"], changes["nested"])

    def test_patch_nested_document_nullable_missing(self):
        schema = {
            "sensor": {
                "type": "dict",
                "schema": {"name": {"type": "string"}},
                "default": None,
                "nullable": True,
            },
            "other": {"type": "dict", "schema": {"name": {"type": "string"}}},
        }
        self.app.config["BANDWIDTH_SAVER"] = False
        self.app.register_resource("sensors", {"schema": schema})

        changes = {}

        r, status = self.post("sensors", data=changes)
        self.assert201(status)
        id, etag = r[self.domain["sensors"]["id_field"]], r[ETAG]
        self.assertTrue("sensor" in r)
        self.assertEqual(r["sensor"], None)
        self.assertFalse("other" in r)

        changes = {"sensor": {"name": "device_name"}, "other": {"name": "other_name"}}

        r, status = self.patch(
            "/%s/%s" % ("sensors", id), data=changes, headers=[("If-Match", etag)]
        )
        self.assert200(status)
        self.assertEqual(r["sensor"], {"name": "device_name"})
        self.assertEqual(r["other"], {"name": "other_name"})

    def test_patch_dependent_field_on_origin_document(self):
        """Test that when patching a field which is dependent on another field's
        existance, and this other field is not provided in the patch, but does
        exist on the persisted document, the patch will be accepted.

        The value on the document can be there either because is was set
        explicitly or because it was set as a default value by Eve.

        See #363.
        """

        # this will succeed as even if the value is not present in the PATCH
        # payload, it is in the persisted document because the dependency_field1
        # had a default value defined
        changes = {"dependency_field2": "value"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assert200(status)

        # this will fail, as dependent field is missing in the PATCH payload
        # and is not present in the persisted document (it doesn't even have a
        # default value)
        etag = r["_etag"]
        changes = {"dependency_field5": "value"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", etag)]
        )
        self.assert422(status)

        # update the stored document by adding the dependency field with some
        # unknown value
        changes = {"dependency_field4": "unknown_value"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", etag)]
        )
        self.assert200(status)

        # This will succeed as now the field is present in the persisted document
        # even if it's not provided in the patch payload
        etag = r["_etag"]
        changes = {"dependency_field5": "value"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", etag)]
        )
        self.assert200(status)

    def test_patch_dependent_field_value_on_origin_document(self):
        """Test that when patching a field which is dependent on another field's
        value, and this other field is not provided in the patch, but is present
        on the persisted document, the patch will be accepted.

        See #363.
        """

        # this will fail as the dependent field has value that doesn't
        # document we are trying to update.
        changes = {"dependency_field3": "value"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assert422(status)

        # update the stored document by setting the dependency field to
        # the required value.
        changes = {"dependency_field1": "value"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assert200(status)

        # now the field3 update will be accepted as the dependency field is
        # present in the stored document already.
        etag = r["_etag"]
        changes = {"dependency_field3": "value"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", etag)]
        )
        self.assert200(status)

    def test_id_field_in_document_fails(self):
        # since v0.6 we also allow the id field to be included with the POSTed
        # document, but not with PATCH since it is immutable
        self.app.config["IF_MATCH"] = False
        id_field = self.domain[self.known_resource]["id_field"]
        data = {id_field: "55b2340538345bd048100ffe"}
        r, status = self.patch(self.item_id_url, data=data)
        self.assert400(status)
        self.assertTrue("immutable" in r["_error"]["message"])

    def test_patch_custom_idfield(self):
        response, status = self.get("products?max_results=1")
        product = response["_items"][0]
        headers = [("If-Match", product[ETAG])]
        data = {"title": "Awesome product"}
        r, status = self.patch(
            "products/%s" % product["sku"], data=data, headers=headers
        )
        self.assert200(status)

    def test_patch_type_coercion(self):
        schema = self.domain[self.known_resource]["schema"]
        schema["aninteger"]["coerce"] = lambda string: int(float(string))
        changes = {"ref": "1234567890123456789054321", "aninteger": "42.3"}
        r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assert200(status)
        r, status = self.get(r["_links"]["self"]["href"])
        self.assertEqual(r["aninteger"], 42)

    def assertPatchResponse(self, response, item_id, resource=None):
        id_field = self.domain[resource or self.known_resource]["id_field"]
        self.assertTrue(STATUS in response)
        self.assertTrue(STATUS_OK in response[STATUS])
        self.assertFalse(ISSUES in response)
        self.assertTrue(id_field in response)
        self.assertEqual(response[id_field], item_id)
        self.assertTrue(LAST_UPDATED in response)
        self.assertTrue(ETAG in response)
        self.assertTrue("_links" in response)
        self.assertItemLink(response["_links"], item_id)

    def patch(self, url, data, headers=[]):
        headers.append(("Content-Type", "application/json"))
        r = self.test_client.patch(url, data=json.dumps(data), headers=headers)
        return self.parse_response(r)


class TestEvents(TestBase):
    new_ref = "0123456789012345678901234"

    def test_on_pre_PATCH(self):
        devent = DummyEvent(self.before_update)
        self.app.on_pre_PATCH += devent
        self.patch()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(3, len(devent.called))

    def test_on_pre_PATCH_contacts(self):
        devent = DummyEvent(self.before_update)
        self.app.on_pre_PATCH_contacts += devent
        self.patch()
        self.assertEqual(2, len(devent.called))

    def test_on_PATCH_dynamic_filter(self):
        def filter_this(resource, request, lookup):
            lookup["_id"] = self.unknown_item_id

        self.app.on_pre_PATCH += filter_this
        # Would normally patch the known document; will return 404 instead.
        r, s = self.parse_response(self.patch())
        self.assert404(s)

    def test_on_post_PATCH(self):
        devent = DummyEvent(self.after_update)
        self.app.on_post_PATCH += devent
        self.patch()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(200, devent.called[2].status_code)
        self.assertEqual(3, len(devent.called))

    def test_on_post_PATCH_contacts(self):
        devent = DummyEvent(self.after_update)
        self.app.on_post_PATCH_contacts += devent
        self.patch()
        self.assertEqual(200, devent.called[1].status_code)
        self.assertEqual(2, len(devent.called))

    def test_on_update(self):
        devent = DummyEvent(self.before_update)
        self.app.on_update += devent
        self.patch()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(3, len(devent.called))

    def test_on_update_contacts(self):
        devent = DummyEvent(self.before_update)
        self.app.on_update_contacts += devent
        self.patch()
        self.assertEqual(2, len(devent.called))

    def test_on_updated(self):
        devent = DummyEvent(self.after_update)
        self.app.on_updated += devent
        self.patch()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(3, len(devent.called))

    def test_on_updated_contacts(self):
        devent = DummyEvent(self.after_update)
        self.app.on_updated_contacts += devent
        self.patch()
        self.assertEqual(2, len(devent.called))

    def before_update(self):
        db = self.connection[MONGO_DBNAME]
        contact = db.contacts.find_one(ObjectId(self.item_id))
        return contact["ref"] == self.item_name

    def after_update(self):
        return not self.before_update()

    def patch(self):
        headers = [("Content-Type", "application/json"), ("If-Match", self.item_etag)]
        data = json.dumps({"ref": self.new_ref})
        return self.test_client.patch(self.item_id_url, data=data, headers=headers)
