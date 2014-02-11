# -*- coding: utf-8 -*-

import simplejson as json
from werkzeug.routing import BaseConverter
from eve.tests import TestBase, TestMinimal
from eve import Eve
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
    Test that we can use custom types as ID_FIELD ('_id' by default).

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
        # create a document which has a ID_FIELD of UUID type and store it
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
        self.assert200(r.status_code)

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
        for settings in self.domain.values():
            r = self.test_client.get('/%s/' % settings['url'])
            self.assert200(r.status_code)

            r = self.test_client.get('/%s' % settings['url'])
            self.assert200(r.status_code)

    def test_item_endpoint(self):
        pass

    def test_unknown_endpoints(self):
        r = self.test_client.get('/%s/' % self.unknown_resource)
        self.assert404(r.status_code)

        r = self.test_client.get(self.unknown_item_id_url)
        self.assert404(r.status_code)

        r = self.test_client.get(self.unknown_item_name_url)
        self.assert404(r.status_code)

    def test_api_version(self):
        settings_file = os.path.join(self.this_directory, 'test_version.py')
        self.prefixapp = Eve(settings=settings_file)
        self.test_prefix = self.prefixapp.test_client()
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
        self.prefixapp = Eve(settings=settings_file)
        self.test_prefix = self.prefixapp.test_client()
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
        self.prefixapp = Eve(settings=settings_file)
        self.test_prefix = self.prefixapp.test_client()
        r = self.test_prefix.get('/')
        self.assert404(r.status_code)
        r = self.test_prefix.get('/prefix/v1/')
        self.assert200(r.status_code)
        r = self.test_prefix.get('/prefix/v1/contacts')
        self.assert200(r.status_code)
        r = self.test_prefix.get('/prefix/v1/contacts/')
        self.assert200(r.status_code)

    def test_nested_endpoint(self):
        r = self.test_client.get('/users/overseas')
        self.assert200(r.status_code)
