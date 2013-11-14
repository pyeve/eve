# -*- coding: utf-8 -*-

from werkzeug.routing import BaseConverter
from eve.tests import TestBase, TestMinimal
from eve import Eve
from eve.io.base import BaseJSONEncoder
from eve.tests.test_settings import MONGO_DBNAME
from uuid import UUID


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


class TestCustomConverters(TestMinimal):
    """
    Test that we can use custom types as ID_FIELD ('_id' by default).

    """

    def setUp(self):
        uuids = {
            'resource_methods': ['GET'],
            'item_methods': ['GET'],
            'item_url': 'uuid',
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

        super(TestCustomConverters, self).setUp(settings_file=settings,
                                                url_converters=url_converters)

        self.app.data.json_encoder_class = UUIDEncoder

    def bulk_insert(self):
        # create a document which has a ID_FIELD of UUID type and store it
        # into the database
        _db = self.connection[MONGO_DBNAME]
        fake = {'_id': UUID(self.uuid_valid), }
        _db.uuids.insert(fake)

    def test_uuid(self):
        # get the document via the Eve API (it will use the UUIDConverter
        # class).
        r = self.test_client.get('/uuids/%s' % self.uuid_valid)
        self.assertEqual(r.status_code, 200)


class TestEndPoints(TestBase):

    def test_homepage(self):
        r = self.test_client.get('/')
        self.assertEqual(r.status_code, 200)

    def test_resource_endpoint(self):
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
        settings_file = 'eve/tests/test_version.py'
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
        settings_file = 'eve/tests/test_prefix.py'
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
        settings_file = 'eve/tests/test_prefix_version.py'
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
