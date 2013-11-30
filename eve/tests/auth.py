# -*- coding: utf-8 -*-
from bson import ObjectId

import eve
import json
from eve import Eve
from eve.auth import BasicAuth, TokenAuth, HMACAuth
from eve.tests import TestBase


class ValidBasicAuth(BasicAuth):
    def __init__(self):
        self.skip_setting_auth_value = False
        super(ValidBasicAuth, self).__init__()

    def check_auth(self, username, password, allowed_roles, resource, method):
        # ignoble hack to only set request_auth_value when the test needs it to
        # be really set
        if not self.skip_setting_auth_value:
            self.request_auth_value = 'admin'
        return username == 'admin' and password == 'secret' and  \
            (allowed_roles == ['admin'] if allowed_roles else True)


class BadBasicAuth(BasicAuth):
    pass


class ValidTokenAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        return token == 'test_token' and (allowed_roles == ['admin'] if
                                          allowed_roles else True)


class ValidHMACAuth(HMACAuth):
    def check_auth(self, userid, hmac_hash, headers, data, allowed_roles,
                   resource, method):
        return userid == 'admin' and hmac_hash == 'secret' and  \
            (allowed_roles == ['admin'] if allowed_roles else True)


class BadHMACAuth(HMACAuth):
    pass


class TestBasicAuth(TestBase):

    def setUp(self):
        super(TestBasicAuth, self).setUp()
        self.app = Eve(settings=self.settings_file, auth=ValidBasicAuth)
        self.test_client = self.app.test_client()
        self.content_type = ('Content-Type', 'application/json')
        self.valid_auth = [('Authorization', 'Basic YWRtaW46c2VjcmV0'),
                           self.content_type]
        self.invalid_auth = [('Authorization', 'Basic IDontThinkSo'),
                             self.content_type]
        for _, schema in self.app.config['DOMAIN'].items():
            schema['allowed_roles'] = ['admin']
            schema['allowed_item_roles'] = ['admin']
        self.app.set_defaults()

    def test_custom_auth(self):
        self.assertTrue(isinstance(self.app.auth, ValidBasicAuth))

    def test_restricted_home_access(self):
        r = self.test_client.get('/')
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
        r = self.test_client.get('/',  headers=self.valid_auth)
        self.assert200(r.status_code)

    def test_authorized_resource_access(self):
        r = self.test_client.get(self.known_resource_url,
                                 headers=self.valid_auth)
        self.assert200(r.status_code)
        r = self.test_client.post(self.known_resource_url,
                                  data=json.dumps({"k": "value"}),
                                  headers=self.valid_auth)
        self.assert200(r.status_code)
        r = self.test_client.delete(self.known_resource_url,
                                    headers=self.valid_auth)
        self.assert200(r.status_code)

    def test_authorized_item_access(self):
        r = self.test_client.get(self.item_id_url, headers=self.valid_auth)
        self.assert200(r.status_code)
        r = self.test_client.patch(self.item_id_url,
                                   data=json.dumps({"k": "value"}),
                                   headers=self.valid_auth)
        self.assert403(r.status_code)
        r = self.test_client.delete(self.item_id_url, headers=self.valid_auth)
        self.assert403(r.status_code)

    def test_unauthorized_home_access(self):
        r = self.test_client.get('/',  headers=self.invalid_auth)
        self.assert401(r.status_code)

    def test_unauthorized_resource_access(self):
        r = self.test_client.get(self.known_resource_url,
                                 headers=self.invalid_auth)
        self.assert401(r.status_code)
        r = self.test_client.post(self.known_resource_url,
                                  headers=self.invalid_auth)
        self.assert401(r.status_code)
        r = self.test_client.delete(self.known_resource_url,
                                    headers=self.invalid_auth)
        self.assert401(r.status_code)

    def test_unauthorized_item_access(self):
        r = self.test_client.get(self.item_id_url, headers=self.invalid_auth)
        self.assert401(r.status_code)
        r = self.test_client.patch(self.item_id_url, headers=self.invalid_auth)
        self.assert401(r.status_code)
        r = self.test_client.delete(self.item_id_url,
                                    headers=self.invalid_auth)
        self.assert401(r.status_code)

    def test_home_public_methods(self):
        self.app.config['PUBLIC_METHODS'] = ['GET']
        r = self.test_client.get('/')
        self.assert200(r.status_code)
        self.test_restricted_resource_access()
        self.test_restricted_item_access()

    def test_public_methods_resource(self):
        self.app.config['PUBLIC_METHODS'] = ['GET']
        domain = self.app.config['DOMAIN']
        for resource, settings in domain.items():
            del(settings['public_methods'])
        self.app.set_defaults()
        del(domain['peopleinvoices'])
        for resource in domain:
            url = self.app.config['URLS'][resource]
            r = self.test_client.get(url)
            self.assert200(r.status_code)
            r = self.test_client.post(url, data={'key1': 'value1'})
            self.assert401or405(r.status_code)
            r = self.test_client.delete(url)
            self.assert401or405(r.status_code)
        self.test_restricted_item_access()

    def test_public_methods_but_locked_resource(self):
        self.app.config['PUBLIC_METHODS'] = ['GET']
        domain = self.app.config['DOMAIN']
        for _, settings in domain.items():
            del(settings['public_methods'])
        self.app.set_defaults()
        domain[self.known_resource]['public_methods'] = []
        r = self.test_client.get(self.known_resource_url)
        self.assert401(r.status_code)

    def test_public_methods_but_locked_item(self):
        self.app.config['PUBLIC_ITEM_METHODS'] = ['GET']
        domain = self.app.config['DOMAIN']
        for _, settings in domain.items():
            del(settings['public_item_methods'])
        self.app.set_defaults()
        domain[self.known_resource]['public_item_methods'] = []
        r = self.test_client.get(self.item_id_url)
        self.assert401(r.status_code)

    def test_public_methods_item(self):
        self.app.config['PUBLIC_ITEM_METHODS'] = ['GET']
        for _, settings in self.app.config['DOMAIN'].items():
            del(settings['public_item_methods'])
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
        r = self.test_client.get('/', headers=self.valid_auth)
        # will fail because check_auth() is not implemented in the custom class
        self.assert500(r.status_code)

    def test_rfc2617_response(self):
        r = self.test_client.get('/')
        self.assert401(r.status_code)
        self.assertTrue(('WWW-Authenticate', 'Basic realm:"%s"' %
                         eve.__package__) in r.headers.to_wsgi_list())


class TestTokenAuth(TestBasicAuth):
    def setUp(self):
        super(TestTokenAuth, self).setUp()
        self.app = Eve(settings=self.settings_file, auth=ValidTokenAuth)
        self.test_client = self.app.test_client()
        self.valid_auth = [('Authorization', 'Basic dGVzdF90b2tlbjo='),
                           self.content_type]

    def test_custom_auth(self):
        self.assertTrue(isinstance(self.app.auth, ValidTokenAuth))


class TestHMACAuth(TestBasicAuth):
    def setUp(self):
        super(TestHMACAuth, self).setUp()
        self.app = Eve(settings=self.settings_file, auth=ValidHMACAuth)
        self.test_client = self.app.test_client()
        self.valid_auth = [('Authorization', 'admin:secret'),
                           self.content_type]

    def test_custom_auth(self):
        self.assertTrue(isinstance(self.app.auth, ValidHMACAuth))

    def test_bad_auth_class(self):
        self.app = Eve(settings=self.settings_file, auth=BadHMACAuth)
        self.test_client = self.app.test_client()
        r = self.test_client.get('/', headers=self.valid_auth)
        # will fail because check_auth() is not implemented in the custom class
        self.assert500(r.status_code)

    def test_rfc2617_response(self):
        r = self.test_client.get('/')
        self.assert401(r.status_code)


class TestUserRestrictedAccess(TestBase):
    def setUp(self):
        super(TestUserRestrictedAccess, self).setUp()

        self.app = Eve(settings=self.settings_file, auth=ValidBasicAuth)

        # using this endpoint since it is a copy of 'contacts' with
        # no filter on the datasource
        self.url = 'restricted'
        self.resource = self.app.config['DOMAIN'][self.url]
        self.test_client = self.app.test_client()

        self.valid_auth = [('Authorization', 'Basic YWRtaW46c2VjcmV0')]
        self.invalid_auth = [('Authorization', 'Basic IDontThinkSo')]
        self.field_name = 'auth_field'
        self.data = json.dumps({"ref": "0123456789123456789012345"})

        for _, settings in self.app.config['DOMAIN'].items():
            settings[self.field_name] = 'username'

        self.resource['public_methods'] = []

    def test_get(self):
        data, status = self.parse_response(
            self.test_client.get(self.url, headers=self.valid_auth))
        self.assert200(status)
        # no data has been saved by user 'admin' yet,
        # so assert we get an empty result set back.
        self.assertEqual(len(data['_items']), 0)

        # Add a user belonging to `admin`
        new_user = self.random_contacts(1)[0]
        new_user['username'] = 'admin'
        _db = self.connection[self.app.config['MONGO_DBNAME']]
        _db.contacts.insert(new_user)

        # Verify that we can retrieve it
        data2, status2 = self.parse_response(
            self.test_client.get(self.url,
                                 headers=self.valid_auth))
        self.assert200(status2)
        self.assertEqual(len(data2['_items']), 1)

    def test_get_by_auth_field_criteria(self):
        """ If we attempt to retrieve an object by the same field
        that is in `auth_field`, then the request is /unauthorized/,
        and should fail and return 401.

        This test verifies that the `auth_field` does not overwrite
        a `client_filter` or url param.
        """
        _, status = self.parse_response(
            self.test_client.get(self.user_username_url,
                                 headers=self.valid_auth))
        self.assert401(status)

    def test_get_by_auth_field_id(self):
        """ To test handling of ObjectIds
        """
        # set auth_field to `_id`
        self.app.config['DOMAIN']['users'][self.field_name] = \
            self.app.config['ID_FIELD']

        _, status = self.parse_response(
            self.test_client.get(self.user_id_url,
                                 headers=self.valid_auth))
        self.assert401(status)

    def test_filter_by_auth_field_id(self):
        """ To test handling of ObjectIds when using a `where` clause
        We need to make sure we *match* an object ID when it is the
        same
        """
        _id = ObjectId('deadbeefdeadbeefdeadbeef')
        resource_def = self.app.config['DOMAIN']['users']
        resource_def['authentication'].skip_setting_auth_value = True
        resource_def['authentication'].request_auth_value = _id

        # set auth_field to `_id`
        resource_def[self.field_name] = '_id'

        # Retrieving a /different user/ by id returns 401
        user_url = '/users/'
        filter_by_id = 'where=_id==ObjectId("%s")'
        filter_query = filter_by_id % self.user_id

        _, status = self.parse_response(
            self.test_client.get('%s?%s' % (user_url, filter_query),
                                 headers=self.valid_auth))
        self.assert401(status)

        # Create a user account belonging to admin
        new_user = self.random_contacts(1)[0]
        new_user['_id'] = _id
        new_user['username'] = 'admin'
        _db = self.connection[self.app.config['MONGO_DBNAME']]
        _db.contacts.insert(new_user)

        # Retrieving /the same/ user by id returns OK
        filter_query_2 = filter_by_id % 'deadbeefdeadbeefdeadbeef'
        data2, status2 = self.parse_response(
            self.test_client.get('%s?%s' % (user_url, filter_query_2),
                                 headers=self.valid_auth))
        self.assert200(status2)
        self.assertEqual(len(data2['_items']), 1)

    def test_collection_get_public(self):
        """ Test that if GET is in `public_methods` the `auth_field`
        criteria is overruled
        """
        self.resource['public_methods'].append('GET')
        data, status = self.parse_response(
            self.test_client.get(self.url))      # no auth
        self.assert200(status)
        # no data has been saved by user 'admin' yet,
        # but we should get all the other results back
        self.assertEqual(len(data['_items']), 25)

    def test_item_get_public(self):
        """ Test that if GET is in `public_item_methods` the `auth_field`
        criteria is overruled
        """
        self.resource['public_item_methods'].append('GET')
        data, status = self.parse_response(
            self.test_client.get(self.item_id_url,
                                 headers=self.valid_auth))
        self.assert200(status)
        self.assertEqual(data['_id'], self.item_id)

    def test_post(self):
        _, status = self.post()
        self.assert200(status)
        data, status = self.parse_response(
            self.test_client.get(self.url,
                                 headers=self.valid_auth))
        self.assert200(status)
        # len of 1 as there are is only 1 doc saved by user
        self.assertEqual(len(data['_items']), 1)

    def test_patch(self):
        new_ref = "9999999999999999999999999"
        changes = json.dumps({"ref": new_ref})
        data, status = self.post()
        url = '%s/%s' % (self.url, data['_id'])
        response = self.test_client.get(url, headers=self.valid_auth)
        etag = response.headers['ETag']
        headers = [('If-Match', etag),
                   self.valid_auth[0]]
        response, status = self.parse_response(
            self.test_client.patch(url, data=json.dumps(changes),
                                   headers=headers,
                                   content_type='application/json'))
        self.assert200(status)

        data, status = self.parse_response(
            self.test_client.get(url, headers=self.valid_auth))
        self.assert200(status)
        self.assertEqual(data['ref'], new_ref)

    def test_delete(self):
        data, status = self.post()
        url = '%s/%s' % (self.url, data['_id'])
        response = self.test_client.get(url, headers=self.valid_auth)
        etag = response.headers['ETag']
        headers = [('If-Match', etag),
                   ('Authorization', 'Basic YWRtaW46c2VjcmV0')]
        response, status = self.parse_response(
            self.test_client.delete(url, headers=headers))
        self.assert200(status)

    def post(self):
        r = self.test_client.post(self.url,
                                  data=self.data,
                                  headers=self.valid_auth,
                                  content_type='application/json')
        return self.parse_response(r)


class TestResourceAuth(TestBase):
    def test_resource_only_auth(self):
        # no auth at the API level
        self.app = Eve(settings=self.settings_file)
        self.test_client = self.app.test_client()
        # explicit auth for just one resource
        self.app.config['DOMAIN']['contacts']['authentication'] = \
            ValidBasicAuth()
        self.app.config['DOMAIN']['empty']['authentication'] = ValidTokenAuth()
        self.app.set_defaults()
        basic_auth = [('Authorization', 'Basic YWRtaW46c2VjcmV0')]
        token_auth = [('Authorization', 'Basic dGVzdF90b2tlbjo=')]

        # 'contacts' endpoints are protected
        r = self.test_client.get(self.known_resource_url)
        self.assert401(r.status_code)
        r = self.test_client.get(self.item_id_url)
        self.assert401(r.status_code)
        # both with BasicAuth.
        _, status = self.parse_response(
            self.test_client.get(self.known_resource_url, headers=basic_auth))
        self.assert200(status)
        _, status = self.parse_response(
            self.test_client.get(self.item_id_url, headers=basic_auth))
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
