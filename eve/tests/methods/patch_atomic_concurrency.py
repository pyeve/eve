import simplejson as json
import sys
import eve.methods.common
from eve.tests import TestBase
from eve.utils import config

"""
Atomic Concurrency Checks

Prior to commit 54fd697 from 2016-November, ETags would be verified
twice during a patch. One ETag check would be non-atomic by Eve,
then again atomically by MongoDB during app.data.update(filter).
The atomic ETag check was removed during issue #920 in 54fd697

When running Eve in a scale-out environment (multiple processes),
concurrent simultaneous updates are sometimes allowed, because
the Python-only ETag check is not atomic.

There is a critical section in patch_internal() between get_document()
and app.data.update() where a competing Eve process can change the
document and ETag.

This test simulates another process changing data & ETag during
the critical section. The test patches get_document() to return an
intentionally wrong ETag.
"""


def get_document_simulate_concurrent_update(*args, **kwargs):
    """
    Hostile version of get_document

    This simluates another process updating MongoDB (and ETag) in
    eve.methods.patch.patch_internal() during the critical area
    between get_document() and app.data.update()
    """
    document = eve.methods.common.get_document(*args, **kwargs)
    document[config.ETAG] = "unexpected change!"
    return document


class TestPatchAtomicConcurrent(TestBase):
    def setUp(self):
        """
        Patch eve.methods.patch.get_document with a hostile version
        that simulates simultaneous updates
        """
        self.original_get_document = sys.modules["eve.methods.patch"].get_document
        sys.modules[
            "eve.methods.patch"
        ].get_document = get_document_simulate_concurrent_update
        return super(TestPatchAtomicConcurrent, self).setUp()

    def test_etag_changed_after_get_document(self):
        """
        Try to update a document after the ETag was adjusted
        outside this process
        """
        changes = {"ref": "1234567890123456789054321"}
        _r, status = self.patch(
            self.item_id_url, data=changes, headers=[("If-Match", self.item_etag)]
        )
        self.assertEqual(status, 412)

    def tearDown(self):
        """ Remove patch of eve.methods.patch.get_document """
        sys.modules["eve.methods.patch"].get_document = self.original_get_document
        return super(TestPatchAtomicConcurrent, self).tearDown()

    def patch(self, url, data, headers=[]):
        headers.append(("Content-Type", "application/json"))
        r = self.test_client.patch(url, data=json.dumps(data), headers=headers)
        return self.parse_response(r)
