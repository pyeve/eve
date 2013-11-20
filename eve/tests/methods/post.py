from eve.tests import TestBase
from eve import STATUS_OK, LAST_UPDATED, ID_FIELD, DATE_CREATED
import simplejson as json
from ast import literal_eval
import io


class TestPost(TestBase):
    def test_unknown_resource(self):
        r, status = self.post(self.unknown_resource_url, data={})
        self.assert404(status)

    def test_readonly_resource(self):
        r, status = self.post(self.readonly_resource_url, data={})
        self.assert405(status)

    def test_post_to_item_endpoint(self):
        r, status = self.post(self.item_id_url, data={})
        self.assert405(status)

    def test_validation_error(self):
        r, status = self.post(self.known_resource_url, data={"ref": "123"})
        self.assert200(status)
        self.assertValidationError(r, ("min length for field 'ref' is 25",))

        r, status = self.post(self.known_resource_url, data={"prog": 123})
        self.assert200(status)
        self.assertValidationError(r, ("required", "ref"))

    def test_post_empty_resource(self):
        data = []
        for i in range(10):
            data.append({"inv_number": self.random_string(10)})
        r, status = self.post(self.empty_resource_url, data=data)
        self.assert200(status)
        self.assertPostResponse(r)

    def test_post_string(self):
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_integer(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = 'prog'
        test_value = 1
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_list_as_array(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "role"
        test_value = ["vendor", "client"]
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_rows(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "rows"
        test_value = [
            {'sku': 'AT1234', 'price': 99},
            {'sku': 'XF9876', 'price': 9999}
        ]
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_list(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "alist"
        test_value = ["a_string", 99]
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_dict(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "location"
        test_value = {'address': 'an address', 'city': 'a city'}
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_datetime(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "born"
        test_value = "Tue, 06 Nov 2012 10:33:31 GMT"
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_objectid(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = 'tid'
        test_value = "50656e4538345b39dd0414f0"
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_default_value(self):
        test_field = 'title'
        test_value = "Mr."
        data = {'ref': '9234567890123456789054321'}
        self.assertPostItem(data, test_field, test_value)

    def test_post_default_value_none(self):
        # default values that assimilate to None (0, '', False) were ignored
        # prior to 0.1.1
        title = self.domain['contacts']['schema']['title']
        title['default'] = ''
        self.app.set_defaults()
        data = {"ref": "UUUUUUUUUUUUUUUUUUUUUUUUU"}
        self.assertPostItem(data, 'title', '')

        title['type'] = 'integer'
        title['default'] = 0
        self.app.set_defaults()
        data = {"ref": "TTTTTTTTTTTTTTTTTTTTTTTTT"}
        self.assertPostItem(data, 'title', 0)

        title['type'] = 'boolean'
        title['default'] = False
        self.app.set_defaults()
        data = {"ref": "QQQQQQQQQQQQQQQQQQQQQQQQQ"}
        self.assertPostItem(data, 'title', False)

    def test_multi_post(self):
        items = [
            ('ref', "9234567890123456789054321"),
            ('prog', 7),
            ('ref', "5432112345678901234567890", ["agent"]),
            ('ref', self.item_ref),
            ('ref', "9234567890123456789054321", "12345678"),
        ]
        data = [
            literal_eval('{"%s": "%s"}' % items[0]),
            literal_eval('{"%s": %s}' % items[1]),
            literal_eval('{"%s": "%s", "role": %s}' % items[2]),
            literal_eval('{"%s": "%s"}' % items[3]),
            literal_eval('{"%s": "%s", "tid": "%s"}' % items[4]),
        ]
        r = self.perform_post(data, [0, 2])

        self.assertValidationError(r[1], ("required", "ref"))
        self.assertValidationError(r[3], ("unique", "ref"))
        self.assertValidationError(r[4], ("ObjectId", "tid"))

        item_id = r[0][ID_FIELD]
        db_value = self.compare_post_with_get(item_id, "ref")
        self.assertTrue(db_value == items[0][1])

        item_id = r[2][ID_FIELD]
        db_value = self.compare_post_with_get(item_id, ["ref", "role"])
        self.assertTrue(db_value[0] == items[2][1])
        self.assertTrue(db_value[1] == items[2][2])

        # items on which validation failed should not be inserted into the db
        response, status = self.get(self.known_resource_url, "where=prog==7")
        self.assert404(status)

    def test_post_x_www_form_urlencoded(self):
        test_field = "ref"
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        r, status = self.parse_response(self.test_client.post(
            self.known_resource_url, data=data))
        self.assert200(status)
        self.assertTrue('OK' in r['status'])
        self.assert200(status)
        self.assertPostResponse(r)

    def test_post_referential_integrity(self):
        data = {"person": self.unknown_item_id}
        r, status = self.post('/invoices/', data=data)
        self.assert200(status)
        expected = ("value '%s' for field '%s' must exist in "
                    "resource '%s', field '%s'" %
                    (self.unknown_item_id, 'person', 'contacts',
                     self.app.config['ID_FIELD']))
        self.assertValidationError(r, expected)

        data = {"person": self.item_id}
        r, status = self.post('/invoices/', data=data)
        self.assert200(status)
        self.assertPostResponse(r)

    def test_post_allow_unknown(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        data = {"unknown": "unknown"}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        self.assertValidationError(r, "unknown")
        self.app.config['DOMAIN'][self.known_resource]['allow_unknown'] = True
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        self.assertPostResponse(r)

    def test_post_with_content_type_charset(self):
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        r, status = self.post(self.known_resource_url, data=data,
                              content_type='application/json; charset=utf-8')
        self.assert200(status)
        self.assertPostResponse(r)

    def test_post_with_extra_response_fields(self):
        self.domain['contacts']['extra_response_fields'] = ['ref', 'notreally']
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        self.assertTrue('ref' in r and 'notreally' not in r)

    def test_post_write_concern(self):
        # should get a 500 since there's no replicaset on mongod test instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 2}
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert500(status)
        # 0 and 1 are the only valid values for 'w' on our mongod instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 0}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)

    def test_post_with_get_override(self):
        # a GET request with POST override turns into a POST request.
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = json.dumps({test_field: test_value})
        headers = [('X-HTTP-Method-Override', 'POST'),
                   ('Content-Type', 'application/json')]
        r = self.test_client.get(self.known_resource_url, data=data,
                                 headers=headers)
        self.assert200(r.status_code)
        self.assertPostResponse(json.loads(r.get_data()))

    def test_post_list_of_objectid(self):
        objectid = '50656e4538345b39dd0414f0'
        del(self.domain['contacts']['schema']['ref']['required'])
        data = {'id_list': ['%s' % objectid]}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        r, status = self.get(self.known_resource, '?where={"id_list": '
                             '{"$in": ["%s"]}}' % objectid)
        self.assert200(status)
        self.assertTrue(len(r), 1)
        self.assertTrue('%s' % objectid in r['_items'][0]['id_list'])

    def test_post_nested_dict_objectid(self):
        objectid = '50656e4538345b39dd0414f0'
        del(self.domain['contacts']['schema']['ref']['required'])
        data = {'id_list_of_dict': [{'id': '%s' % objectid}]}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        r, status = self.get(self.known_resource,
                             '?where={"id_list_of_dict.id": ' '"%s"}'
                             % objectid)
        self.assertTrue(len(r), 1)
        self.assertTrue('%s' % objectid in
                        r['_items'][0]['id_list_of_dict'][0]['id'])

    def test_post_list_fixed_len(self):
        objectid = '50656e4538345b39dd0414f0'
        del(self.domain['contacts']['schema']['ref']['required'])
        data = {'id_list_fixed_len': ['%s' % objectid]}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        r, status = self.get(self.known_resource,
                             '?where={"id_list_fixed_len": '
                             '{"$in": ["%s"]}}' % objectid)
        self.assert200(status)
        self.assertTrue(len(r), 1)
        self.assertTrue('%s' % objectid in r['_items'][0]['id_list_fixed_len'])

    def tests_post_multipart(self):
        data = {'picture': io.BytesIO(b'test data')}
        headers = [('Content-Type', 'multipart/form-data')]
        url = self.known_resource_url
        r = self.test_client.post(url, data=data, headers=headers)
        self.assert200(r.status_code)

    def perform_post(self, data, valid_items=[0]):
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        self.assertPostResponse(r, valid_items)
        return r

    def assertPostItem(self, data, test_field, test_value):
        r = self.perform_post(data)
        item_id = r[ID_FIELD]
        item_etag = r['etag']
        db_value = self.compare_post_with_get(item_id, [test_field, 'etag'])
        self.assertTrue(db_value[0] == test_value)
        self.assertTrue(db_value[1] == item_etag)

    def assertPostResponse(self, response, valid_items=[0]):
        if isinstance(response, dict):
            response = [response]
        for i in valid_items:
            item = response[i]
            self.assertTrue('status' in item)
            self.assertTrue(STATUS_OK in item['status'])
            self.assertFalse('issues' in item)
            self.assertTrue(ID_FIELD in item)
            self.assertTrue(LAST_UPDATED in item)
            self.assertTrue('_links' in item)
            self.assertItemLink(item['_links'], item[ID_FIELD])
            self.assertTrue('etag' in item)

    def compare_post_with_get(self, item_id, fields):
        raw_r = self.test_client.get("%s/%s" % (self.known_resource_url,
                                                item_id))
        item, status = self.parse_response(raw_r)
        self.assert200(status)
        self.assertTrue(ID_FIELD in item)
        self.assertTrue(item[ID_FIELD] == item_id)
        self.assertTrue(DATE_CREATED in item)
        self.assertTrue(LAST_UPDATED in item)
        self.assertEqual(item[DATE_CREATED], item[LAST_UPDATED])
        if isinstance(fields, list):
            return [item[field] for field in fields]
        else:
            return item[fields]

    def post(self, url, data, headers=[], content_type='application/json'):
        headers.append(('Content-Type', content_type))
        r = self.test_client.post(url, data=json.dumps(data), headers=headers)
        return self.parse_response(r)
