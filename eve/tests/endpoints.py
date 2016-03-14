# -*- coding: utf-8 -*-

import simplejson as json
from werkzeug.routing import BaseConverter
from eve.tests import TestBase, TestMinimal
from eve import Eve
from datetime import datetime
from eve.utils import config
from eve.io.base import BaseJSONEncoder
from eve.tests.test_settings import MONGO_DBNAME
from uuid import UUID
from eve.io.mongo import Validator
import os


class UUIDEncoder(BaseJSONEncoder):
    """ Propretary JSONEconder subclass used by the json render function.
    This is different from BaseJSONEoncoder since it also addresses encoding of
    UUID
    """
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        else:
            # delegate rendering to base class method
            return super(UUIDEncoder, self).default(obj)


class UUIDConverter(BaseConverter):
    """
    UUID converter for the Werkzeug routing system.
    """

    def __init__(self, url_map, strict=True):
        super(UUIDConverter, self).__init__(url_map)

    def to_python(self, value):
        return UUID(value)

    def to_url(self, value):
        return str(value)


class UUIDValidator(Validator):
    """
    Extends the base mongo validator adding support for the uuid data-type
    """
    def _validate_type_uuid(self, field, value):
        try:
            UUID(value)
        except ValueError:
            self._error("value '%s' for field '%s' cannot be converted to a "
                        "UUID" % (value, field))


class TestCustomConverters(TestMinimal):
    """
    Test that we can use custom types as id field ('_id' by default).
    """

    def setUp(self):
        uuids = {
            'resource_methods': ['GET', 'POST'],
            'item_methods': ['GET', 'PATCH', 'PUT', 'DELETE'],
            'item_url': 'uuid',
            'schema': {
                '_id': {'type': 'uuid'},
                'name': {'type': 'string'}
            }
        }
        settings = {
            'MONGO_USERNAME': 'test_user',
            'MONGO_PASSWORD': 'test_pw',
            'MONGO_DBNAME': 'eve_test',
            'DOMAIN': {
                'uuids': uuids
            }
        }
        url_converters = {'uuid': UUIDConverter}
        self.uuid_valid = '48c00ee9-4dbe-413f-9fc3-d5f12a91de1c'
        self.url = '/uuids/%s' % self.uuid_valid
        self.headers = [('Content-Type', 'application/json')]

        super(TestCustomConverters, self).setUp(settings_file=settings,
                                                url_converters=url_converters)

        self.app.validator = UUIDValidator
        self.app.data.json_encoder_class = UUIDEncoder

    def bulk_insert(self):
        # create a document which has a id field of UUID type and store it
        # into the database
        _db = self.connection[MONGO_DBNAME]
        fake = {'_id': UUID(self.uuid_valid), }
        _db.uuids.insert(fake)

    def _get_etag(self):
        r = self.test_client.get(self.url)
        self.assert200(r.status_code)
        return json.loads(r.get_data())[config.ETAG]

    def test_get_uuid(self):
        r = self.test_client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_patch_uuid(self):
        etag = self._get_etag()
        self.headers.append(('If-Match', etag))
        r = self.test_client.patch(self.url,
                                   data=json.dumps({"name": " a_name"}),
                                   headers=self.headers)
        self.assert200(r.status_code)

    def test_put_uuid(self):
        etag = self._get_etag()
        self.headers.append(('If-Match', etag))
        r = self.test_client.put(self.url,
                                 data=json.dumps({"name": " a_name"}),
                                 headers=self.headers)
        self.assert200(r.status_code)

    def test_delete_uuid(self):
        etag = self._get_etag()
        self.headers.append(('If-Match', etag))
        r = self.test_client.delete(self.url, headers=self.headers)
        self.assert204(r.status_code)

    def test_post_uuid(self):
        new_id = '48c00ee9-4dbe-413f-9fc3-d5f12a91de13'
        data = json.dumps({'_id': new_id})
        r = self.test_client.post('uuids', data=data, headers=self.headers)
        self.assert201(r.status_code)
        match_id = json.loads(r.get_data())['_id']
        self.assertEqual(new_id, match_id)


class TestEndPoints(TestBase):

    def test_homepage(self):
        r = self.test_client.get('/')
        self.assertEqual(r.status_code, 200)

    def test_resource_endpoint(self):
        del(self.domain['peopleinvoices'])
        del(self.domain['peoplerequiredinvoices'])
        del(self.domain['peoplesearches'])
        del(self.domain['internal_transactions'])
        del(self.domain['child_products'])
        for settings in self.domain.values():
            r = self.test_client.get('/%s/' % settings['url'])
            self.assert200(r.status_code)

            r = self.test_client.get('/%s' % settings['url'])
            self.assert200(r.status_code)

    def assert_item_fields(self, data, resource=None):
        id_field = self.domain[resource or self.known_resource]['id_field']
        self.assertTrue(id_field in list(data))
        self.assertTrue('_created' in list(data))
        self.assertTrue('_updated' in list(data))
        self.assertTrue('_etag' in list(data))
        self.assertTrue('_links' in list(data))

    def test_item_endpoint_id(self):
        data, status_code = self.get(self.known_resource, item=self.item_id)
        self.assertEqual(status_code, 200)
        self.assert_item_fields(data)

    def test_item_endpoint_additional_lookup(self):
        data, status_code = self.get(self.known_resource, item=self.item_name)
        self.assertEqual(status_code, 200)
        self.assert_item_fields(data)

    def test_item_self_link(self):
        data, status_code = self.get(self.known_resource, item=self.item_id)
        lookup_field = self.domain[self.known_resource]['item_lookup_field']
        link = '%s/%s' % (self.known_resource_url.lstrip('/'),
                          self.item[lookup_field])
        self.assertEqual(data.get('_links').get('self').get('href'), link)

    def test_unknown_endpoints(self):
        r = self.test_client.get('/%s/' % self.unknown_resource)
        self.assert404(r.status_code)

        r = self.test_client.get(self.unknown_item_id_url)
        self.assert404(r.status_code)

        r = self.test_client.get(self.unknown_item_name_url)
        self.assert404(r.status_code)

    def test_api_version(self):
        settings_file = os.path.join(self.this_directory, 'test_version.py')
        self.app = Eve(settings=settings_file)
        self.test_prefix = self.app.test_client()
        r = self.test_prefix.get('/')
        self.assert404(r.status_code)
        r = self.test_prefix.get('/v1/')
        self.assert200(r.status_code)

        r = self.test_prefix.get('/contacts/')
        self.assert404(r.status_code)
        r = self.test_prefix.get('/v1/contacts')
        self.assert200(r.status_code)
        r = self.test_prefix.get('/v1/contacts/')
        self.assert200(r.status_code)

    def test_api_prefix(self):
        settings_file = os.path.join(self.this_directory, 'test_prefix.py')
        self.app = Eve(settings=settings_file)
        self.test_prefix = self.app.test_client()
        r = self.test_prefix.get('/')
        self.assert404(r.status_code)
        r = self.test_prefix.get('/prefix/')
        self.assert200(r.status_code)

        r = self.test_prefix.get('/prefix/contacts')
        self.assert200(r.status_code)
        r = self.test_prefix.get('/prefix/contacts/')
        self.assert200(r.status_code)

    def test_api_prefix_version(self):
        settings_file = os.path.join(self.this_directory,
                                     'test_prefix_version.py')
        self.app = Eve(settings=settings_file)
        self.test_prefix = self.app.test_client()
        r = self.test_prefix.get('/')
        self.assert404(r.status_code)
        r = self.test_prefix.get('/prefix/v1/')
        self.assert200(r.status_code)
        r = self.test_prefix.get('/prefix/v1/contacts')
        self.assert200(r.status_code)
        r = self.test_prefix.get('/prefix/v1/contacts/')
        self.assert200(r.status_code)

    def test_api_prefix_version_hateoas_links(self):
        """ Test that #419 is closed and URL_PREFIX and API_VERSION are stipped
        out of hateoas links since they are now relative to the API entry point
        (root).
        """
        settings_file = os.path.join(self.this_directory,
                                     'test_prefix_version.py')
        self.app = Eve(settings=settings_file)
        self.test_prefix = self.app.test_client()

        r = self.test_prefix.get('/prefix/v1/')
        href = json.loads(r.get_data())['_links']['child'][0]['href']
        self.assertEqual(href, 'contacts')

        r = self.test_prefix.get('/prefix/v1/contacts')
        href = json.loads(r.get_data())['_links']['self']['href']
        self.assertEqual(href, 'contacts')

    def test_nested_endpoint(self):
        r = self.test_client.get('/users/overseas')
        self.assert200(r.status_code)

    def test_homepage_does_not_have_internal_resources(self):
        r = self.test_client.get('/')
        links = json.loads(r.get_data())
        for resource in self.domain.keys():
            internal = self.domain[resource].get('internal_resource', False)
            if internal:
                self.assertFalse(internal in links.keys())

    def on_generic_inserted(self, resource, docs):
        if resource != 'internal_transactions':
            dt = datetime.now()
            transaction = {
                'entities': [doc['_id'] for doc in docs],
                'original_resource': resource,
                config.LAST_UPDATED: dt,
                config.DATE_CREATED: dt,
            }
            self.app.data.insert('internal_transactions', [transaction])

    def test_internal_endpoint(self):
        self.app.on_inserted -= self.on_generic_inserted
        self.app.on_inserted += self.on_generic_inserted
        del(self.domain['contacts']['schema']['ref']['required'])
        test_field = "rows"
        test_value = [
            {'sku': 'AT1234', 'price': 99},
            {'sku': 'XF9876', 'price': 9999}
        ]
        data = {test_field: test_value}
        resp_data, code = self.post(self.known_resource_url, data)
        self.assert201(code)

    def test_oplog_endpoint(self):
        r = self.test_client.get('/oplog')
        self.assert404(r.status_code)

        self.app.config['OPLOG_ENDPOINT'] = 'oplog'
        self.app._init_oplog()
        settings = self.app.config['DOMAIN']['oplog']
        self.app.register_resource('oplog', settings)
        r = self.test_client.get('/oplog')
        self.assert200(r.status_code)

        # OPLOG endpoint is read-only
        data = {'field': 'value'}
        _, status_code = self.post('/oplog', data)
        self.assert405(status_code)
        _, status_code = self.delete('/oplog')
        self.assert405(status_code)

    def test_schema_endpoint(self):
        known_schema_path = '/schema/%s' % self.known_resource

        r = self.test_client.get(known_schema_path)
        self.assert404(r.status_code)

        self.app.config['SCHEMA_ENDPOINT'] = 'schema'
        self.app._init_schema_endpoint()
        r = self.test_client.get(known_schema_path)
        self.assert200(r.status_code)
        self.assertEqual(r.mimetype, 'application/json')
        self.assertEqual(
            json.loads(r.data),
            self.app.config['DOMAIN'][self.known_resource]['schema'])

        r = self.test_client.get('/schema/%s' % self.unknown_resource)
        self.assert404(r.status_code)

        # schema endpoint doesn't reveal internal resources
        r = self.test_client.get('/schema/internal_transactions')
        self.assert404(r.status_code)

        # schema endpoint is read-only
        data = {'field': 'value'}
        _, status_code = self.patch(known_schema_path, data)
        self.assert405(status_code)
        _, status_code = self.put(known_schema_path, data)
        self.assert405(status_code)
        _, status_code = self.post(known_schema_path, data)
        self.assert405(status_code)
        _, status_code = self.delete(known_schema_path)
        self.assert405(status_code)

    def test_schema_endpoint_does_not_attempt_callable_serialization(self):
        self.domain[self.known_resource]['schema']['lambda'] = {
            'type': 'boolean',
            'coerce': lambda v: v if type(v) is bool else v.lower() in ['true',
                                                                        '1']
        }
        known_schema_path = '/schema/%s' % self.known_resource
        self.app.config['SCHEMA_ENDPOINT'] = 'schema'
        self.app._init_schema_endpoint()

        r = self.test_client.get(known_schema_path)
        self.assert200(r.status_code)
        self.assertEqual(json.loads(r.data)['lambda']['coerce'], '<callable>')
