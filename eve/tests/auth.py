# -*- coding: utf-8 -*-

import eve
from eve import Eve
from eve.auth import BasicAuth
from eve.tests import TestMethodsBase


class ValidBasicAuth(BasicAuth):
    def check_auth(self, username, password, allowed_roles):
        return username == 'admin' and password == 'secret' and  \
            (allowed_roles == ['admin'] if allowed_roles else True)


class BadBasicAuth(BasicAuth):
    pass


class TestBasicAuth(TestMethodsBase):

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
                                  data={'key1': 'value1'},
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
