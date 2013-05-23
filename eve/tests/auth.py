# -*- coding: utf-8 -*-

import eve
import json
from eve import Eve
from eve.auth import BasicAuth, TokenAuth, HMACAuth
from eve.tests import TestBase


class ValidBasicAuth(BasicAuth):
    def check_auth(self, username, password, allowed_roles, resource):
        return username == 'admin' and password == 'secret' and  \
            (allowed_roles == ['admin'] if allowed_roles else True)


class BadBasicAuth(BasicAuth):
    pass


class ValidTokenAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource):
        return token == 'test_token' and (allowed_roles == ['admin'] if
                                          allowed_roles else True)


class ValidHMACAuth(HMACAuth):
    def check_auth(self, userid, hmac_hash, headers, data, allowed_roles,
                   resource):
        return userid == 'admin' and hmac_hash == 'secret' and  \
            (allowed_roles == ['admin'] if allowed_roles else True)


class BadHMACAuth(HMACAuth):
    pass


class TestBasicAuth(TestBase):

    def setUp(self):
        super(TestBasicAuth, self).setUp()
        self.app = Eve(settings=self.settings_file, auth=ValidBasicAuth)
        self.test_client = self.app.test_client()
        self.valid_auth = [('Authorization', 'Basic YWRtaW46c2VjcmV0')]
        self.invalid_auth = [('Authorization', 'Basic IDontThinkSo')]
        for resource, schema in self.app.config['DOMAIN'].items():
            schema['allowed_roles'] = ['admin']
            schema['allowed_item_roles'] = ['admin']
        self.app.set_defaults()

    def test_custom_auth(self):
        self.assertEqual(type(self.app.auth), ValidBasicAuth)

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
                                  data={"item1": json.dumps({"k": "value"})},
                                  headers=self.valid_auth)
        self.assert200(r.status_code)
        r = self.test_client.delete(self.known_resource_url,
                                    headers=self.valid_auth)
        self.assert200(r.status_code)

    def test_authorized_item_access(self):
        r = self.test_client.get(self.item_id_url, headers=self.valid_auth)
        self.assert200(r.status_code)
        r = self.test_client.patch(self.item_id_url, data={'key1': 'value'},
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
        for resource in domain:
            url = '/%s/' % self.app.config['URLS'][resource]
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
        for resource, settings in domain.items():
            del(settings['public_methods'])
        self.app.set_defaults()
        domain[self.known_resource]['public_methods'] = []
        r = self.test_client.get(self.known_resource_url)
        self.assert401(r.status_code)

    def test_public_methods_but_locked_item(self):
        self.app.config['PUBLIC_ITEM_METHODS'] = ['GET']
        domain = self.app.config['DOMAIN']
        for resource, settings in domain.items():
            del(settings['public_item_methods'])
        self.app.set_defaults()
        domain[self.known_resource]['public_item_methods'] = []
        r = self.test_client.get(self.item_id_url)
        self.assert401(r.status_code)

    def test_public_methods_item(self):
        self.app.config['PUBLIC_ITEM_METHODS'] = ['GET']
        for resource, settings in self.app.config['DOMAIN'].items():
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
                         eve.__package__) in r.headers.to_list())

    def assert401(self, status):
        self.assertEqual(status, 401)

    def assert401or405(self, status):
        self.assertTrue(status == 401 or 405)

    def assert500(self, status):
        self.assertEqual(status, 500)


class TestTokenAuth(TestBasicAuth):
    def setUp(self):
        super(TestTokenAuth, self).setUp()
        self.app = Eve(settings=self.settings_file, auth=ValidTokenAuth)
        self.test_client = self.app.test_client()
        self.valid_auth = [('Authorization', 'Basic dGVzdF90b2tlbjo=')]

    def test_custom_auth(self):
        self.assertEqual(type(self.app.auth), ValidTokenAuth)


class TestHMACAuth(TestBasicAuth):
    def setUp(self):
        super(TestHMACAuth, self).setUp()
        self.app = Eve(settings=self.settings_file, auth=ValidHMACAuth)
        self.test_client = self.app.test_client()
        self.valid_auth = [('Authorization', 'admin:secret')]

    def test_custom_auth(self):
        self.assertEqual(type(self.app.auth), ValidHMACAuth)

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
        # remove the datasource filter to make the whole collection available
        # to a GET request.
        del(self.app.config['DOMAIN'][self.known_resource]['datasource']['filter'])
        self.app.set_defaults()
        self.app._add_url_rules()
        self.test_client = self.app.test_client()
        self.valid_auth = [('Authorization', 'Basic YWRtaW46c2VjcmV0')]
        self.invalid_auth = [('Authorization', 'Basic IDontThinkSo')]
        self.field_name = 'auth_username_field'
        self.data = {'item1': json.dumps({"ref": "0123456789123456789012345"})}
        for resource, settings in self.app.config['DOMAIN'].items():
            settings[self.field_name] = 'username'

    def test_get(self):
        data, status = self.parse_response(
            self.test_client.get(self.known_resource_url,
                                 headers=self.valid_auth))
        self.assert200(status)
        # no data has been saved by user 'admin' yet, so we get an empyy
        # resulset back.
        self.assertEqual(len(data['_items']), 0)

    def test_post(self):
        response, status = self.post()
        self.assert200(status)
        data, status = self.parse_response(
            self.test_client.get(self.known_resource_url,
                                 headers=self.valid_auth))
        self.assert200(status)
        # len of 1 as there are is only 1 doc saved by user
        self.assertEqual(len(data['_items']), 1)

    def test_patch(self):
        changes = {"ref": "9999999999999999999999999"}
        data, status = self.post()
        url = '%s%s/' % (self.known_resource_url, data['item1']['_id'])
        response = self.test_client.get(url, headers=self.valid_auth)
        etag = response.headers['ETag']
        headers = [('If-Match', etag),
                   ('Content-Type', 'application/x-www-form-urlencoded'),
                   ('Authorization', 'Basic YWRtaW46c2VjcmV0')]
        response, status = self.parse_response(
            self.test_client.patch(url, data={'item1': json.dumps(changes)},
                                   headers=headers))
        self.assert200(status)

        data, status = self.parse_response(
            self.test_client.get(url, headers=self.valid_auth))
        self.assert200(status)

    def test_delete(self):
        data, status = self.post()
        url = '%s%s/' % (self.known_resource_url, data['item1']['_id'])
        response = self.test_client.get(url, headers=self.valid_auth)
        etag = response.headers['ETag']
        headers = [('If-Match', etag),
                   ('Authorization', 'Basic YWRtaW46c2VjcmV0')]
        response, status = self.parse_response(
            self.test_client.delete(url, headers=headers))
        self.assert200(status)

    def post(self):
        headers = [('Content-Type', 'application/x-www-form-urlencoded'),
                   ('Authorization', 'Basic YWRtaW46c2VjcmV0')]
        r = self.test_client.post(self.known_resource_url,
                                  data=self.data,
                                  headers=headers)
        return self.parse_response(r)
