import simplejson as json

from eve.tests import TestBase
from eve.tests.utils import DummyEvent
from eve.tests.test_settings import MONGO_DBNAME

from eve import STATUS_OK, LAST_UPDATED, DATE_CREATED, ISSUES, STATUS, ETAG
from eve.methods.post import post
from eve.methods.post import post_internal


class TestPost(TestBase):
    def test_unknown_resource(self):
        _, status = self.post(self.unknown_resource_url, data={})
        self.assert404(status)

    def test_readonly_resource(self):
        _, status = self.post(self.readonly_resource_url, data={})
        self.assert405(status)

    def test_post_to_item_endpoint(self):
        _, status = self.post(self.item_id_url, data={})
        self.assert405(status)

    def test_validation_error(self):
        r, status = self.post(self.known_resource_url, data={"ref": "123"})
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {'ref': 'min length is 25'})

        r, status = self.post(self.known_resource_url, data={"prog": 123})
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {'ref': 'required'})

    def test_post_empty_bulk_insert(self):
        r, status = self.post(self.empty_resource_url, data=[])
        self.assert400(status)

    def test_post_empty_resource(self):
        data = []
        for _ in range(10):
            data.append({"inv_number": self.random_string(10)})
        r, status = self.post(self.empty_resource_url, data=data)
        self.assert201(status)
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

    def test_post_integer_zero(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "aninteger"
        test_value = 0
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_float_zero(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "afloat"
        test_value = 0.0
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

    def test_post_null_objectid(self):
        # verify that #341 is fixed.
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = 'tid'
        test_value = None
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

    def test_multi_post_valid(self):
        data = [
            {"ref": "9234567890123456789054321"},
            {"ref": "5432112345678901234567890", "role": ["agent"]},
        ]
        r, status = self.post(self.known_resource_url, data=data)
        self.assert201(status)
        results = r['_items']

        self.assertEqual(results[0]['_status'], 'OK')
        self.assertEqual(results[1]['_status'], 'OK')

        with self.app.test_request_context():
            contacts = self.app.data.driver.db['contacts']
            r = contacts.find({"ref": "9234567890123456789054321"}).count()
            self.assertTrue(r == 1)
            r = contacts.find({"ref": "5432112345678901234567890"}).count()
            self.assertTrue(r == 1)

    def test_multi_post_invalid(self):
        data = [
            {"ref": "9234567890123456789054321"},
            {"prog": 9999},
            {"ref": "5432112345678901234567890", "role": ["agent"]},
            {"ref": self.item_ref},
            {"ref": "9234567890123456789054321", "tid": "12345678"},
        ]
        r, status = self.post(self.known_resource_url, data=data)
        self.assertValidationErrorStatus(status)
        results = r['_items']

        self.assertEqual(results[0]['_status'], 'OK')
        self.assertEqual(results[2]['_status'], 'OK')

        self.assertValidationError(results[1], {'ref': 'required'})
        self.assertValidationError(results[3], {'ref': 'unique'})
        self.assertValidationError(results[4], {'tid': 'ObjectId'})

        id_field = self.domain[self.known_resource]['id_field']
        self.assertTrue(id_field not in results[0])
        self.assertTrue(id_field not in results[1])
        self.assertTrue(id_field not in results[2])
        self.assertTrue(id_field not in results[3])

        with self.app.test_request_context():
            contacts = self.app.data.driver.db['contacts']
            r = contacts.find({"prog": 9999}).count()
            self.assertTrue(r == 0)
            r = contacts.find({"ref": "9234567890123456789054321"}).count()
            self.assertTrue(r == 0)

    def test_post_x_www_form_urlencoded(self):
        test_field = "ref"
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        r, status = self.parse_response(self.test_client.post(
            self.known_resource_url, data=data))
        self.assert201(status)
        self.assertTrue('OK' in r[STATUS])
        self.assertPostResponse(r)

    def test_post_referential_integrity(self):
        data = {"person": self.unknown_item_id}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        expected = ("value '%s' must exist in resource '%s', field '%s'" %
                    (self.unknown_item_id, 'contacts',
                     self.domain['contacts']['id_field']))
        self.assertValidationError(r, {'person': expected})

        data = {"person": self.item_id}
        r, status = self.post('/invoices/', data=data)
        self.assert201(status)
        self.assertPostResponse(r)

    def test_post_referential_integrity_list(self):
        data = {"invoicing_contacts": [self.item_id, self.unknown_item_id]}
        r, status = self.post('/invoices/', data=data)
        self.assertValidationErrorStatus(status)
        expected = ("value '%s' must exist in resource '%s', field '%s'" %
                    (self.unknown_item_id, 'contacts',
                     self.domain['contacts']['id_field']))
        self.assertValidationError(r, {'invoicing_contacts': expected})

        data = {"invoicing_contacts": [self.item_id, self.item_id]}
        r, status = self.post('/invoices/', data=data)
        self.assert201(status)
        self.assertPostResponse(r)

    def test_post_allow_unknown(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        data = {"unknown": "unknown"}
        r, status = self.post(self.known_resource_url, data=data)
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {'unknown': 'unknown'})

        # since resource settings are only set at app startup we set
        # those that influence the 'allow_unknown' property by hand (so we
        # don't have to re-initialize the whole app.)
        settings = self.app.config['DOMAIN'][self.known_resource]
        settings['allow_unknown'] = True
        settings['datasource']['projection'] = None

        r, status = self.post(self.known_resource_url, data=data)
        self.assert201(status)
        self.assertPostResponse(r)

        # test that the unknown field is also returned with subsequent get
        # requests
        id = r[self.domain[self.known_resource]['id_field']]
        r = self.test_client.get('%s/%s' % (self.known_resource_url, id))
        r_data = json.loads(r.get_data())
        self.assertTrue('unknown' in r_data)
        self.assertEqual('unknown', r_data['unknown'])

    def test_post_with_content_type_charset(self):
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        r, status = self.post(self.known_resource_url, data=data,
                              content_type='application/json; charset=utf-8')
        self.assert201(status)
        self.assertPostResponse(r)

    def test_post_with_extra_response_fields(self):
        self.domain['contacts']['extra_response_fields'] = ['ref', 'notreally']
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert201(status)
        self.assertTrue('ref' in r and 'notreally' not in r)

    def test_post_with_excluded_response_fields(self):
        data = {
            'email': 'test@email.com',
            'password': 'password'
        }
        r, status = self.post('login', data=data)
        self.assert201(status)

        login_id = r[self.domain['login']['id_field']]
        r = self.test_client.get('%s/%s' % ('login', login_id))
        r_data = json.loads(r.get_data())
        self.assertTrue('password' not in r_data)
        self.assertTrue('email' in r_data)

    def test_post_write_concern(self):
        # should get a 500 since there's no replicaset on mongod test instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 2}
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        _, status = self.post(self.known_resource_url, data=data)
        self.assert500(status)
        # 0 and 1 are the only valid values for 'w' on our mongod instance
        self.domain['contacts']['mongo_write_concern'] = {'w': 0}
        test_value = "1234567890123456789054329"
        data = {test_field: test_value}
        _, status = self.post(self.known_resource_url, data=data)
        self.assert201(status)

    def test_post_with_get_override(self):
        # a GET request with POST override turns into a POST request.
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = json.dumps({test_field: test_value})
        headers = [('X-HTTP-Method-Override', 'POST'),
                   ('Content-Type', 'application/json')]
        r = self.test_client.get(self.known_resource_url, data=data,
                                 headers=headers)
        self.assert201(r.status_code)
        self.assertPostResponse(json.loads(r.get_data()))

    def test_post_list_of_objectid(self):
        objectid = '50656e4538345b39dd0414f0'
        del(self.domain['contacts']['schema']['ref']['required'])
        data = {'id_list': ['%s' % objectid]}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert201(status)
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
        self.assert201(status)
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
        self.assert201(status)
        r, status = self.get(self.known_resource,
                             '?where={"id_list_fixed_len": '
                             '{"$in": ["%s"]}}' % objectid)
        self.assert200(status)
        self.assertTrue(len(r), 1)
        self.assertTrue('%s' % objectid in r['_items'][0]['id_list_fixed_len'])

    def test_custom_issues(self):
        self.app.config['ISSUES'] = 'errors'
        r, status = self.post(self.known_resource_url, data={"ref": "123"})
        self.assertValidationErrorStatus(status)
        self.assertTrue('errors' in r and ISSUES not in r)

    def test_custom_status(self):
        self.app.config['STATUS'] = 'report'
        r, status = self.post(self.known_resource_url, data={"ref": "123"})
        self.assertValidationErrorStatus(status)
        self.assertTrue('report' in r and STATUS not in r)

    def test_custom_etag_update_date(self):
        self.app.config['ETAG'] = '_myetag'
        r, status = self.post(self.known_resource_url,
                              data={"ref": "1234567890123456789054321"})
        self.assert201(status)
        self.assertTrue('_myetag' in r and ETAG not in r)

    def test_custom_date_updated(self):
        self.app.config['LAST_UPDATED'] = '_update_date'
        r, status = self.post(self.known_resource_url,
                              data={"ref": "1234567890123456789054321"})
        self.assert201(status)
        self.assertTrue('_update_date' in r and LAST_UPDATED not in r)

    def test_subresource(self):
        response, status = self.post('users/%s/invoices' %
                                     self.item_id, data={})
        self.assert201(status)
        self.assertPostResponse(response)

        invoice_id = response.get(self.domain['peopleinvoices']['id_field'])
        response, status = self.get('users/%s/invoices/%s' %
                                    (self.item_id, invoice_id))
        self.assert200(status)
        self.assertEqual(response.get('person'), self.item_id)

    def test_subresource_required_ref(self):
        response, status = self.post('users/%s/required_invoices' %
                                     self.item_id, data={})
        self.assert201(status)
        self.assertPostResponse(response)

        invoice_id = response.get(self.domain['required_invoices']['id_field'])
        response, status = self.get('users/%s/required_invoices/%s' %
                                    (self.item_id, invoice_id))
        self.assert200(status)
        self.assertEqual(response.get('person'), self.item_id)

    def test_post_ifmatch_disabled(self):
        # if IF_MATCH is disabled, then we get no etag in the payload.
        self.app.config['IF_MATCH'] = False
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        data = {test_field: test_value}
        r, status = self.post(self.known_resource_url, data=data)
        self.assertTrue(ETAG not in r)

    def test_post_custom_idfield(self):
        # Test that we can post a document with a custom id_field.
        id_field = 'sku'
        product = {id_field: 'FOO', 'title': 'Foobar'}
        r, status = self.post('products', data=product)
        self.assert201(status)
        self.assertTrue(id_field in r)
        self.assertItemLink(r['_links'], r[id_field])

    def test_post_with_relation_to_custom_idfield(self):
        # Test that we can post a document that relates to a resource with a
        # custom id_field.
        id_field = 'sku'
        db = self.connection[MONGO_DBNAME]
        existing_product = db.products.find_one()
        product = {
            id_field: 'BAR',
            'title': 'Foobar',
            'parent_product': existing_product[id_field]
        }
        r, status = self.post('products', data=product)
        self.assert201(status)
        self.assertTrue(id_field in r)
        self.assertItemLink(r['_links'], r[id_field])
        r, status = self.get('products', item='BAR')
        self.assertEqual(r['parent_product'], existing_product[id_field])

    def test_post_bandwidth_saver(self):
        data = {'inv_number': self.random_string(10)}

        # bandwidth_saver is on by default
        self.assertTrue(self.app.config['BANDWIDTH_SAVER'])
        r, status = self.post(self.empty_resource_url, data=data)
        self.assert201(status)
        self.assertPostResponse(r)
        self.assertFalse('inv_number' in r)
        etag = r[self.app.config['ETAG']]
        r, status = self.get(
            self.empty_resource, '',
            r[self.domain[self.empty_resource]['id_field']])
        self.assertEqual(etag, r[self.app.config['ETAG']])

        # test return all fields (bandwidth_saver off)
        self.app.config['BANDWIDTH_SAVER'] = False
        r, status = self.post(self.empty_resource_url, data=data)
        self.assert201(status)
        self.assertPostResponse(r)
        self.assertTrue('inv_number' in r)
        etag = r[self.app.config['ETAG']]
        r, status = self.get(
            self.empty_resource, '',
            r[self.domain[self.empty_resource]['id_field']])
        self.assertEqual(etag, r[self.app.config['ETAG']])

    def test_post_alternative_payload(self):
        payl = {"ref": "5432112345678901234567890", "role": ["agent"]}
        with self.app.test_request_context(self.known_resource_url):
            r, _, _, status = post(self.known_resource, payl=payl)
        self.assert201(status)
        self.assertPostResponse(r)

    def test_post_dependency_fields_with_default(self):
        # test that default values are resolved before validation. See #353.
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = 'dependency_field2'
        test_value = 'a value'
        data = {test_field: test_value}
        self.assertPostItem(data, test_field, test_value)

    def test_post_dependency_required_fields(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        schema = self.domain['contacts']['schema']
        schema['dependency_field3']['required'] = True

        r, status = self.post(self.known_resource_url, data={})
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {'dependency_field3': 'required'})

        # required field dependnecy value matches the dependent field's default
        # value. validation still fails since required field is still missing.
        # See #665.
        schema['dependency_field3']['dependencies'] = {'dependency_field1':
                                                       'default'}
        r, status = self.post(self.known_resource_url, data={})
        self.assertValidationErrorStatus(status)
        self.assertValidationError(r, {'dependency_field3': 'required'})

        r, status = self.post(self.known_resource_url,
                              data={'dependency_field3': 'hello'})
        self.assert201(status)

    def test_post_dependency_fields_with_values(self):
        # test that dependencies values are validated correctly. See #547.
        del(self.domain['contacts']['schema']['ref']['required'])

        schema = {
            'field1': {
                'required': False,
                'default': 'one'
            },
            'field2': {
                'required': True,
                'dependencies': {'field1': ['one', 'two']}
            }
        }
        settings = {
            'RESOURCE_METHODS': ['GET', 'POST', 'DELETE'],
            'ITEM_METHODS': ['GET', 'PATCH', 'PUT', 'DELETE'],
            'schema': schema
        }
        self.app.register_resource('posts', settings)

        data = {"field1": "three", "field2": 7}
        r, s = self.post('posts', data=data)
        self.assert422(s)

        data = {"field2": 7}
        r, s = self.post('posts', data=data)
        self.assert201(s)

        data = {"field1": "one", "field2": 7}
        r, s = self.post('posts', data=data)
        self.assert201(s)

        data = {"field1": "two", "field2": 7}
        r, s = self.post('posts', data=data)
        self.assert201(s)

    def test_post_readonly_field_with_default(self):
        # test that a read only field with a 'default' setting is correctly
        # validated now that we resolve field values before validation.
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = 'read_only_field'
        # thou shalt not pass.
        test_value = 'a random value'
        data = {test_field: test_value}
        r, status = self.post(self.known_resource_url, data=data)
        self.assertValidationErrorStatus(status)
        # this will not pass even if value matches 'default' setting.
        # (hey it's still a read-onlu field so you can't reset it)
        test_value = 'default'
        data = {test_field: test_value}
        r, status = self.post(self.known_resource_url, data=data)
        self.assertValidationErrorStatus(status)

    def test_post_readonly_in_dict(self):
        # Test that a post with a readonly field inside a dict is properly
        # validated (even if it has a defult value)
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = 'dict_with_read_only'
        test_value = {'read_only_in_dict': 'default'}
        data = {test_field: test_value}
        r, status = self.post(self.known_resource_url, data=data)
        self.assertValidationErrorStatus(status)

    def test_post_valueschema_dict(self):
        """ make sure Cerberus#48 is fixed """
        del(self.domain['contacts']['schema']['ref']['required'])
        r, status = self.post(self.known_resource_url,
                              data={"valueschema_dict": {"k1": "1"}})
        self.assertValidationErrorStatus(status)
        issues = r[ISSUES]
        self.assertTrue('valueschema_dict' in issues)
        self.assertEqual(issues['valueschema_dict'],
                         {'k1': 'must be of integer type'})

        r, status = self.post(self.known_resource_url,
                              data={"valueschema_dict": {"k1": 1}})
        self.assert201(status)

    def test_post_propertyschema_dict(self):
        del(self.domain['contacts']['schema']['ref']['required'])

        r, status = self.post(self.known_resource_url,
                              data={"propertyschema_dict": {"aaa": 1}})
        self.assert201(status)

        r, status = self.post(self.known_resource_url,
                              data={"propertyschema_dict": {"AAA": "1"}})
        self.assertValidationErrorStatus(status)

        issues = r[ISSUES]
        self.assertTrue('propertyschema_dict' in issues)
        self.assertEqual(issues['propertyschema_dict'],
                         'propertyschema_dict')

    def test_post_internal(self):
        # test that post_internal is available and working properly.
        test_field = 'ref'
        test_value = "1234567890123456789054321"
        payload = {test_field: test_value}
        with self.app.test_request_context(self.known_resource_url):
            r, _, _, status = post_internal(self.known_resource, payl=payload)
        self.assert201(status)

    def test_post_nested(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        data = {'location.city': 'a nested city',
                'location.address': 'a nested address'}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert201(status)
        values = self.compare_post_with_get(
            r[self.domain[self.known_resource]['id_field']],
            ['location']).pop()
        self.assertEqual(values['city'], 'a nested city')
        self.assertEqual(values['address'], 'a nested address')

    def test_post_error_as_list(self):
        del(self.domain['contacts']['schema']['ref']['required'])
        self.app.config['VALIDATION_ERROR_AS_LIST'] = True
        data = {'unknown_field': 'a value'}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert422(status)
        error = r[ISSUES]['unknown_field']
        self.assertTrue(isinstance(error, list))

    def test_id_field_included_with_document(self):
        # since v0.6 we also allow the id field to be included with the POSTed
        # document
        id_field = self.domain[self.known_resource]['id_field']
        id = '55b2340538345bd048100ffe'
        data = {"ref": "1234567890123456789054321", id_field: id}
        r, status = self.post(self.known_resource_url, data=data)
        self.assert201(status)
        self.assertPostResponse(r)
        self.assertEqual(r['_id'], id)

    def test_post_type_coercion(self):
        schema = self.domain[self.known_resource]['schema']
        schema['aninteger']['coerce'] = lambda string: int(float(string))
        data = {'ref': '1234567890123456789054321', 'aninteger': '42.3'}
        self.assertPostItem(data, 'aninteger', 42)

    def perform_post(self, data, valid_items=[0]):
        r, status = self.post(self.known_resource_url, data=data)
        self.assert201(status)
        self.assertPostResponse(r, valid_items)
        return r

    def assertPostItem(self, data, test_field, test_value):
        r = self.perform_post(data)
        item_id = r[self.domain[self.known_resource]['id_field']]
        item_etag = r[ETAG]
        db_value = self.compare_post_with_get(item_id, [test_field, ETAG])
        self.assertTrue(db_value[0] == test_value)
        self.assertTrue(db_value[1] == item_etag)

    def assertPostResponse(self, response, valid_items=[0], resource=None):
        if '_items' in response:
            results = response['_items']
        else:
            results = [response]

        id_field = self.domain[resource or self.known_resource]['id_field']

        for i in valid_items:
            item = results[i]
            self.assertTrue(STATUS in item)
            self.assertTrue(STATUS_OK in item[STATUS])
            self.assertFalse(ISSUES in item)
            self.assertTrue(id_field in item)
            self.assertTrue(LAST_UPDATED in item)
            self.assertTrue('_links' in item)
            self.assertItemLink(item['_links'], item[id_field])
            self.assertTrue(ETAG in item)

    def compare_post_with_get(self, item_id, fields):
        raw_r = self.test_client.get("%s/%s" % (self.known_resource_url,
                                                item_id))
        item, status = self.parse_response(raw_r)
        id_field = self.domain[self.known_resource]['id_field']
        self.assert200(status)
        self.assertTrue(id_field in item)
        self.assertTrue(item[id_field] == item_id)
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


class TestEvents(TestBase):
    new_contact_id = "0123456789012345678901234"

    def test_on_pre_POST(self):
        devent = DummyEvent(self.before_insert)
        self.app.on_pre_POST += devent
        self.post()
        self.assertFalse(devent.called is None)

    def test_on_pre_POST_contacts(self):
        devent = DummyEvent(self.before_insert)
        self.app.on_pre_POST_contacts += devent
        self.post()
        self.assertFalse(devent.called is None)

    def test_on_post_POST(self):
        devent = DummyEvent(self.after_insert)
        self.app.on_post_POST += devent
        self.post()
        self.assertEqual(devent.called[0], self.known_resource)

    def test_on_POST_post_resource(self):
        devent = DummyEvent(self.after_insert)
        self.app.on_post_POST_contacts += devent
        self.post()
        self.assertFalse(devent.called is None)

    def test_on_insert(self):
        devent = DummyEvent(self.before_insert, True)
        self.app.on_insert += devent
        self.post()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(self.new_contact_id, devent.called[1][0]['ref'])

    def test_on_insert_contacts(self):
        devent = DummyEvent(self.before_insert, True)
        self.app.on_insert_contacts += devent
        self.post()
        self.assertEqual(self.new_contact_id, devent.called[0][0]['ref'])

    def test_on_inserted(self):
        devent = DummyEvent(self.after_insert, True)
        self.app.on_inserted += devent
        self.post()
        self.assertEqual(self.known_resource, devent.called[0])
        self.assertEqual(self.new_contact_id, devent.called[1][0]['ref'])

    def test_on_inserted_contacts(self):
        devent = DummyEvent(self.after_insert, True)
        self.app.on_inserted_contacts += devent
        self.post()
        self.assertEqual(self.new_contact_id, devent.called[0][0]['ref'])

    def post(self):
        headers = [('Content-Type', 'application/json')]
        data = json.dumps({"ref": self.new_contact_id})
        self.test_client.post(
            self.known_resource_url, data=data, headers=headers)

    def before_insert(self):
        db = self.connection[MONGO_DBNAME]
        return db.contacts.find_one({"ref": self.new_contact_id}) is None

    def after_insert(self):
        return not self.before_insert()
