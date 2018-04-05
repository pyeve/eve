from io import BytesIO
from unittest import TestCase
from eve.io.media import MediaStorage
from eve.io.mongo import GridFSMediaStorage
from eve.tests import TestBase, MONGO_DBNAME
from eve import STATUS_OK, STATUS, STATUS_ERR, ISSUES, ETAG
import base64
from bson import ObjectId


class TestMediaStorage(TestCase):
    def test_base_media_storage(self):
        a = MediaStorage()
        self.assertEqual(a.app, None)

        a = MediaStorage("hello")
        self.assertEqual(a.app, "hello")

        self.assertRaises(NotImplementedError, a.get, 1)
        self.assertRaises(NotImplementedError, a.put, "clean", "filename")
        self.assertRaises(NotImplementedError, a.delete, 1)
        self.assertRaises(NotImplementedError, a.exists, 1)


class TestGridFSMediaStorage(TestBase):
    def setUp(self):
        super(TestGridFSMediaStorage, self).setUp()
        self.url = self.known_resource_url
        self.resource = self.known_resource
        self.headers = [('Content-Type', 'multipart/form-data')]
        self.id_field = self.domain[self.resource]['id_field']
        self.test_field, self.test_value = 'ref', "1234567890123456789054321"
        # we want an explicit binary as Py3 encodestring() expects binaries.
        self.clean = b'my file contents'
        # encodedstring will raise a DeprecationWarning under Python3.3, but
        # the alternative encodebytes is not available in Python 2.
        self.encoded = base64.encodestring(self.clean).decode('utf-8')

    def test_gridfs_media_storage_errors(self):
        self.assertRaises(TypeError, GridFSMediaStorage)
        self.assertRaises(TypeError, GridFSMediaStorage, "hello")

    def test_gridfs_media_storage_post(self):
        # send something different than a file and get an error back
        data = {'media': 'not a file'}
        r, s = self.parse_response(
            self.test_client.post(self.url, data=data, headers=self.headers))
        self.assertEqual(STATUS_ERR, r[STATUS])

        # validates media fields
        self.assertTrue('must be of media type' in r[ISSUES]['media'])
        # also validates ordinary fields
        self.assertTrue('required' in r[ISSUES][self.test_field])

        r, s = self._post()
        self.assertEqual(STATUS_OK, r[STATUS])

        # compare original and returned data
        _id = r[self.id_field]
        self.assertMediaField(_id, self.encoded, self.clean)

        # GET the file at the resource endpoint
        where = 'where={"%s": "%s"}' % (self.id_field, _id)
        r, s = self.parse_response(
            self.test_client.get('%s?%s' % (self.url, where)))
        self.assertEqual(len(r['_items']), 1)
        returned = r['_items'][0]['media']

        # returned value is a base64 encoded string
        self.assertEqual(returned, self.encoded)

        # which decodes to the original clean
        self.assertEqual(base64.decodestring(returned.encode()), self.clean)

    def test_gridfs_media_storage_post_excluded_file_in_result(self):
        # send something different than a file and get an error back
        data = {'media': 'not a file'}
        r, s = self.parse_response(
            self.test_client.post(self.url, data=data, headers=self.headers))
        self.assertEqual(STATUS_ERR, r[STATUS])

        # validates media fields
        self.assertTrue('must be of media type' in r[ISSUES]['media'])
        # also validates ordinary fields
        self.assertTrue('required' in r[ISSUES][self.test_field])

        r, s = self._post()
        self.assertEqual(STATUS_OK, r[STATUS])

        self.app.config['RETURN_MEDIA_AS_BASE64_STRING'] = False
        # compare original and returned data
        _id = r[self.id_field]

        # GET the file at the resource endpoint
        where = 'where={"%s": "%s"}' % (self.id_field, _id)
        r, s = self.parse_response(
            self.test_client.get('%s?%s' % (self.url, where)))
        self.assertEqual(len(r['_items']), 1)
        returned = r['_items'][0]['media']

        # returned value is a base64 encoded string
        self.assertEqual(returned, None)

    def test_gridfs_media_storage_post_extended(self):
        r, s = self._post()
        self.assertEqual(STATUS_OK, r[STATUS])

        # request extended format file response
        self.app.config['EXTENDED_MEDIA_INFO'] = ['content_type', 'length']

        # compare original and returned data
        _id = r[self.id_field]
        self.assertMediaFieldExtended(_id, self.encoded, self.clean)

        # GET the file at the resource endpoint
        where = 'where={"%s": "%s"}' % (self.id_field, _id)
        r, s = self.parse_response(
            self.test_client.get('%s?%s' % (self.url, where)))
        self.assertEqual(len(r['_items']), 1)
        returned = r['_items'][0]['media']

        # returned value is a base64 encoded string
        self.assertEqual(returned['file'], self.encoded)

        # which decodes to the original clean
        self.assertEqual(base64.decodestring(returned['file'].encode()),
                         self.clean)

        # also verify our extended fields
        self.assertEqual(returned['content_type'], 'text/plain')
        self.assertEqual(returned['length'], 16)

    def test_gridfs_media_storage_post_extended_excluded_file_in_result(self):
        r, s = self._post()
        self.assertEqual(STATUS_OK, r[STATUS])

        # request extended format file response
        self.app.config['EXTENDED_MEDIA_INFO'] = ['content_type', 'length']
        self.app.config['RETURN_MEDIA_AS_BASE64_STRING'] = False
        # compare original and returned data
        _id = r[self.id_field]

        # GET the file at the resource endpoint
        where = 'where={"%s": "%s"}' % (self.id_field, _id)
        r, s = self.parse_response(
            self.test_client.get('%s?%s' % (self.url, where)))
        self.assertEqual(len(r['_items']), 1)
        returned = r['_items'][0]['media']

        # returned value is None
        self.assertEqual(returned['file'], None)

        # also verify our extended fields
        self.assertEqual(returned['content_type'], 'text/plain')
        self.assertEqual(returned['length'], 16)

    def test_gridfs_media_storage_put(self):
        r, s = self._post()
        _id = r[self.id_field]
        etag = r[ETAG]

        # compare original and returned data
        self.assertMediaField(_id, self.encoded, self.clean)

        with self.app.test_request_context():
            # retrieve media_id
            media_id = self.assertMediaStored(_id)

        # PUT replaces the file with new one
        clean = b'my new file contents'
        encoded = base64.encodestring(clean).decode()
        test_field, test_value = 'ref', "9234567890123456789054321"
        data = {'media': (BytesIO(clean), 'test.txt'), test_field: test_value}
        headers = [('Content-Type', 'multipart/form-data'), ('If-Match', etag)]

        r, s = self.parse_response(
            self.test_client.put(('%s/%s' % (self.url, _id)), data=data,
                                 headers=headers))
        self.assertEqual(STATUS_OK, r[STATUS])

        with self.app.test_request_context():
            # media has been properly stored
            self.assertMediaStored(_id)

        # compare original and returned data
        r, s = self.assertMediaField(_id, encoded, clean)

        # and of course, the ordinary field has been updated too
        self.assertEqual(r[test_field], test_value)

        with self.app.test_request_context():
            # previous media doesn't exist anymore (it's been deleted)
            self.assertFalse(self.app.media.exists(media_id, self.resource))

    def test_gridfs_media_storage_patch(self):
        r, s = self._post()
        _id = r[self.id_field]
        etag = r[ETAG]

        # compare original and returned data
        self.assertMediaField(_id, self.encoded, self.clean)

        with self.app.test_request_context():
            # retrieve media_id
            media_id = self.assertMediaStored(_id)

        # PATCH replaces the file with new one
        clean = b'my new file contents'
        encoded = base64.encodestring(clean).decode()
        test_field, test_value = 'ref', "9234567890123456789054321"
        data = {'media': (BytesIO(clean), 'test.txt'), test_field: test_value}
        headers = [('Content-Type', 'multipart/form-data'), ('If-Match', etag)]

        r, s = self.parse_response(
            self.test_client.patch(('%s/%s' % (self.url, _id)), data=data,
                                   headers=headers))
        self.assertEqual(STATUS_OK, r[STATUS])

        # compare original and returned data
        r, s = self.assertMediaField(_id, encoded, clean)

        # and of course, the ordinary field has been updated too
        self.assertEqual(r[test_field], test_value)

        with self.app.test_request_context():
            # previous media doesn't exist anymore (it's been deleted)
            self.assertFalse(self.app.media.exists(media_id, self.resource))

    def test_gridfs_media_storage_patch_null(self):
        # set 'media' field to 'nullable'
        self.domain[self.known_resource]['schema']['media']['nullable'] = True

        response, status = self._post()
        self.assert201(status)

        _id = response[self.id_field]
        etag = response[ETAG]

        # test that nullable media field can be set to None
        data = {'media': None}
        headers = [('If-Match', etag)]
        response, status = self.patch(('%s/%s' % (self.url, _id)), data=data,
                                      headers=headers)
        self.assert200(status)

        response, status = self.get(self.known_resource, item=_id)
        self.assert200(status)
        self.assertEqual(response['media'], None)

    def test_gridfs_media_storage_delete(self):
        r, s = self._post()
        _id = r[self.id_field]
        etag = r[ETAG]

        with self.app.test_request_context():
            # retrieve media_id and compare original and returned data
            self.assertMediaField(_id, self.encoded, self.clean)

            media_id = self.assertMediaStored(_id)

        # DELETE deletes both the document and the media file
        headers = [('If-Match', etag)]

        r, s = self.parse_response(
            self.test_client.delete(('%s/%s' % (self.url, _id)),
                                    headers=headers))
        self.assert204(s)

        with self.app.test_request_context():
            # media doesn't exist anymore (it's been deleted)
            self.assertFalse(self.app.media.exists(media_id, self.resource))

        # GET returns 404
        r, s = self.parse_response(self.test_client.get('%s/%s' % (self.url,
                                                                   _id)))
        self.assert404(s)

    def test_get_media_can_leverage_projection(self):
        """ Test that static projection expose fields other than media
        and client projection on media will work.
        """
        # post a document with *hiding media*
        r, s = self._post_hide_media()

        _id = r[self.id_field]

        projection = '{"media": 1}'
        response, status = self.parse_response(self.test_client.get(
            '%s/%s?projection=%s' %
            (self.resource_exclude_media_url, _id, projection))
        )
        self.assert200(status)

        self.assertFalse('title' in response)
        self.assertFalse('ref' in response)
        # client-side projection should work
        self.assertTrue('media' in response)
        self.assertTrue(self.domain[self.known_resource]['id_field']
                        in response)
        self.assertTrue(self.app.config['ETAG'] in response)
        self.assertTrue(self.app.config['LAST_UPDATED'] in response)
        self.assertTrue(self.app.config['DATE_CREATED'] in response)
        self.assertTrue(r[self.app.config['LAST_UPDATED']] != self.epoch)
        self.assertTrue(r[self.app.config['DATE_CREATED']] != self.epoch)

        response, status = self.parse_response(self.test_client.get(
            '%s/%s' % (self.resource_exclude_media_url, _id)))
        self.assert200(status)

        self.assertTrue('title' in response)
        self.assertTrue('ref' in response)
        # not shown without projection
        self.assertFalse('media' in response)
        self.assertTrue(self.domain[self.known_resource]['id_field']
                        in response)
        self.assertTrue(self.app.config['ETAG'] in response)
        self.assertTrue(self.app.config['LAST_UPDATED'] in response)
        self.assertTrue(self.app.config['DATE_CREATED'] in response)
        self.assertTrue(r[self.app.config['LAST_UPDATED']] != self.epoch)
        self.assertTrue(r[self.app.config['DATE_CREATED']] != self.epoch)

    def test_gridfs_media_storage_delete_projection(self):
        """ test that #284 is fixed: If you have a media field, and set
        datasource projection to 0 for that field, the media will not be
        deleted
        """
        r, s = self._post()
        _id = r[self.id_field]

        with self.app.test_request_context():
            # retrieve media_id and compare original and returned data
            media_id = self.assertMediaStored(_id)

        self.app.config['DOMAIN']['contacts']['datasource']['projection'] = \
            {"media": 0}

        r, s = self.parse_response(self.test_client.get('%s/%s' % (self.url,
                                                                   _id)))
        etag = r[ETAG]

        # DELETE deletes both the document and the media file
        headers = [('If-Match', etag)]

        r, s = self.parse_response(
            self.test_client.delete(('%s/%s' % (self.url, _id)),
                                    headers=headers))
        self.assert204(s)

        with self.app.test_request_context():
            # media doesn't exist anymore (it's been deleted)
            self.assertFalse(self.app.media.exists(media_id, self.resource))

        # GET returns 404
        r, s = self.parse_response(self.test_client.get('%s/%s' % (self.url,
                                                                   _id)))
        self.assert404(s)

    def test_gridfs_media_storage_return_url(self):
        self.app._init_media_endpoint()
        self.app.config['RETURN_MEDIA_AS_BASE64_STRING'] = False
        self.app.config['RETURN_MEDIA_AS_URL'] = True

        r, s = self._post()
        self.assertEqual(STATUS_OK, r[STATUS])
        _id = r[self.id_field]

        # GET the file at the resource endpoint
        where = 'where={"%s": "%s"}' % (self.id_field, _id)
        r, s = self.parse_response(
            self.test_client.get('%s?%s' % (self.url, where)))
        self.assertEqual(len(r['_items']), 1)
        url = r['_items'][0]['media']

        with self.app.test_request_context():
            media_id = self.assertMediaStored(_id)

        self.assertEqual('/media/%s' % media_id, url)
        response = self.test_client.get(url)
        self.assertEqual(self.clean, response.get_data())

    def test_gridfs_partial_media(self):
        self.app._init_media_endpoint()
        self.app.config['RETURN_MEDIA_AS_BASE64_STRING'] = False
        self.app.config['RETURN_MEDIA_AS_URL'] = True

        r, s = self._post()
        _id = r[self.id_field]
        where = 'where={"%s": "%s"}' % (self.id_field, _id)
        r, s = self.parse_response(
            self.test_client.get('%s?%s' % (self.url, where)))
        url = r['_items'][0]['media']

        headers = {'Range': 'bytes=0-5'}
        response = self.test_client.get(url, headers=headers)
        self.assertEqual(self.clean[:6], response.get_data())
        headers = {'Range': 'bytes=5-10'}
        response = self.test_client.get(url, headers=headers)
        self.assertEqual(self.clean[5:11], response.get_data())
        headers = {'Range': 'bytes=0-999'}
        response = self.test_client.get(url, headers=headers)
        self.assertEqual(self.clean, response.get_data())

    def test_gridfs_media_storage_base_url(self):
        self.app._init_media_endpoint()
        self.app.config['RETURN_MEDIA_AS_BASE64_STRING'] = False
        self.app.config['RETURN_MEDIA_AS_URL'] = True
        self.app.config['MEDIA_BASE_URL'] = 'http://s3-us-west-2.amazonaws.com'
        self.app.config['MEDIA_ENDPOINT'] = 'foo'

        r, s = self._post()
        self.assertEqual(STATUS_OK, r[STATUS])
        _id = r[self.id_field]

        # GET the file at the resource endpoint
        where = 'where={"%s": "%s"}' % (self.id_field, _id)
        r, s = self.parse_response(
            self.test_client.get('%s?%s' % (self.url, where)))
        self.assertEqual(len(r['_items']), 1)
        url = r['_items'][0]['media']

        with self.app.test_request_context():
            media_id = self.assertMediaStored(_id)
        self.assertEqual('%s/%s/%s' % (self.app.config['MEDIA_BASE_URL'],
                         self.app.config['MEDIA_ENDPOINT'], media_id), url)

    def assertMediaField(self, _id, encoded, clean):
        # GET the file at the item endpoint
        r, s = self.parse_response(self.test_client.get('%s/%s' % (self.url,
                                                                   _id)))
        returned = r['media']
        # returned value is a base64 encoded string
        self.assertEqual(returned, encoded)
        # which decodes to the original file clean
        self.assertEqual(base64.decodestring(returned.encode()), clean)
        return r, s

    def assertMediaFieldExtended(self, _id, encoded, clean):
        # GET the file at the item endpoint
        r, s = self.parse_response(self.test_client.get('%s/%s' % (self.url,
                                                                   _id)))
        returned = r['media']['file']
        # returned value is a base64 encoded string
        self.assertEqual(returned, encoded)
        # which decodes to the original file clean
        self.assertEqual(base64.decodestring(returned.encode()), clean)
        return r, s

    def assertMediaStored(self, _id):
        _db = self.connection[MONGO_DBNAME]

        # retrieve media id
        media_id = _db.contacts.find_one(
            {self.id_field: ObjectId(_id)})['media']

        # verify it's actually stored in the media storage system
        self.assertTrue(self.app.media.exists(media_id, self.resource))
        return media_id

    def _post(self):
        # send a file and a required, ordinary field with no issues
        data = {'media': (BytesIO(self.clean), 'test.txt'), self.test_field:
                self.test_value}
        return self.parse_response(self.test_client.post(
            self.url, data=data, headers=self.headers))

    def _post_hide_media(self):
        # send a file and a required, ordinary field with no issues
        data = {'media': (BytesIO(self.clean), 'test.txt'), self.test_field:
                self.test_value}
        return self.parse_response(self.test_client.post(
            self.resource_exclude_media_url, data=data, headers=self.headers))
