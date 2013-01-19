from eve.tests import TestMethodsBase
from eve import STATUS_OK, LAST_UPDATED, ID_FIELD, DATE_CREATED
import simplejson as json
from ast import literal_eval


class TestPost(TestMethodsBase):
    def test_unknown_resource(self):
        r, status = self.post(self.unknown_resource_url, data={})
        self.assert404(status)

    def test_readonly_resource(self):
        r, status = self.post(self.readonly_resource_url, data={})
        self.assert405(status)

    def test_post_to_item_endpoint(self):
        r, status = self.post(self.item_id_url, data={})
        self.assert405(status)

    def test_bad_form_length(self):
        r, status = self.post(self.known_resource_url, data={})
        self.assert400(status)

    def test_validation_error(self):
        data = {'item1': json.dumps({"ref": "123"})}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        self.assertValidationError(r, 'item1',
                                   ("min length for field 'ref' is 25",))

        data = {'item1': json.dumps({"prog": 123})}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        self.assertValidationError(r, 'item1', ("required", "ref"))

    def test_post_empty_resource(self):
        data = {}
        for i in range(10):
            data['item%s' % i] = json.dumps({"inv_number":
                                             self.random_string(10)})
        r, status = self.post(self.empty_resource_url, data=data)
        self.assert200(status)
        self.assertPostResponse(r, ['item%s' % i for i in range(10)])

    def test_post_string(self):
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = {'item1': json.dumps({test_field: test_value})}
        self.assertPostItem(data, test_field, test_value)

    def test_post_integer(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = 'prog'
        test_value = 1
        data = {'item1': json.dumps({test_field: test_value})}
        self.assertPostItem(data, test_field, test_value)

    def test_post_list_as_array(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "role"
        test_value = ["vendor", "client"]
        data = {'item1': json.dumps({test_field: test_value})}
        self.assertPostItem(data, test_field, test_value)

    def test_post_rows(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "rows"
        test_value = [
            {'sku': 'AT1234', 'price': 99},
            {'sku': 'XF9876', 'price': 9999}
        ]
        data = {'item1': json.dumps({test_field: test_value})}
        self.assertPostItem(data, test_field, test_value)

    def test_post_list(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "alist"
        test_value = ["a_string", 99]
        data = {'item1': json.dumps({test_field: test_value})}
        self.assertPostItem(data, test_field, test_value)

    def test_post_dict(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "location"
        test_value = {'address': 'an address', 'city': 'a city'}
        data = {'item1': json.dumps({test_field: test_value})}
        self.assertPostItem(data, test_field, test_value)

    def test_post_datetime(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "born"
        test_value = "Tue, 06 Nov 2012 10:33:31 UTC"
        data = {'item1': '{"%s": "%s"}' % (test_field, test_value)}
        self.assertPostItem(data, test_field, test_value)

    def test_post_objectid(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = 'tid'
        test_value = "50656e4538345b39dd0414f0"
        data = {'item1': '{"%s": "%s"}' % (test_field, test_value)}
        self.assertPostItem(data, test_field, test_value)

    def assertPostItem(self, data, test_field, test_value):
        r = self.perform_post(data)
        item_id = r['item1'][ID_FIELD]
        db_value = self.compare_post_with_get(item_id, test_field)
        self.assertTrue(db_value == test_value)

    def test_multi_post(self):
        items = [
            ('ref', "9234567890123456789054321"),
            ('prog', 7),
            ('ref', "5432112345678901234567890", ["agent"]),
            ('ref', "9234567890123456789054321"),
            ('ref', "9234567890123456789054321", "12345678"),
        ]
        data = {
            'item1': json.dumps(literal_eval('{"%s": "%s"}' % items[0])),
            'item2': json.dumps(literal_eval('{"%s": %s}' % items[1])),
            'item3': json.dumps(literal_eval('{"%s": "%s", "role": %s}' %
                                             items[2])),
            'item4': json.dumps(literal_eval('{"%s": "%s"}' % items[3])),
            'item5': json.dumps(literal_eval('{"%s": "%s", "tid": "%s"}' %
                                             items[4])),
        }
        r = self.perform_post(data, ['item1', 'item3'])

        self.assertValidationError(r, 'item2', ("required", "ref"))
        self.assertValidationError(r, 'item4', ("unique", "ref"))
        self.assertValidationError(r, 'item5', ("ObjectId", "tid"))

        item_id = r['item1'][ID_FIELD]
        db_value = self.compare_post_with_get(item_id, "ref")
        self.assertTrue(db_value == items[0][1])

        item_id = r['item3'][ID_FIELD]
        db_value = self.compare_post_with_get(item_id, ["ref", "role"])
        self.assertTrue(db_value[0] == items[2][1])
        self.assertTrue(db_value[1] == items[2][2])

    def perform_post(self, data, valid_items=['item1']):
        r, status = self.post(self.known_resource_url, data=data)
        self.assert200(status)
        self.assertPostResponse(r, valid_items)
        return r

    def assertPostResponse(self, response, keys):
        for key in keys:
            self.assertTrue(key in response)
            k = response[key]
            self.assertTrue('status' in k)
            self.assertTrue(STATUS_OK in k['status'])
            self.assertFalse('issues' in k)
            self.assertTrue(ID_FIELD in k)
            self.assertTrue(LAST_UPDATED in k)
            self.assertTrue('_links') in k
            self.assertItemLink(k['_links'], k[ID_FIELD])

    def compare_post_with_get(self, item_id, fields):
        raw_r = self.test_client.get("%s%s/" % (self.known_resource_url,
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

    def post(self, url, data, headers=[]):
        headers.append(('Content-Type', 'application/x-www-form-urlencoded'))
        r = self.test_client.post(url,
                                  data=data,
                                  headers=headers)
        return self.parse_response(r)
