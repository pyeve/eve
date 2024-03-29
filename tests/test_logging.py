from testfixtures import log_capture

from . import TestBase


class TestUtils(TestBase):
    """collection, document and home_link methods (and resource_uri, which is
    used by all of them) are tested in 'tests.methods' since we need an active
    flaskapp context
    """

    @log_capture()
    def test_logging_info(self, log):
        self.app.logger.propagate = True
        self.app.logger.info("test info")
        log.check(("eve", "INFO", "test info"))

        log_record = log.records[0]
        self.assertEqual(log_record.clientip, None)
        self.assertEqual(log_record.method, None)
        self.assertEqual(log_record.url, None)
