from eve.tests import TestBase
import time


class TestRateLimit(TestBase):
    def setUp(self):
        super(TestRateLimit, self).setUp()
        try:
            from redis import Redis, ConnectionError
            self.app.redis = Redis()
            try:
                self.app.redis.flushdb()
            except ConnectionError:
                self.app.redis = None
        except ImportError:
            self.app.redis = None

        if self.app.redis:
            self.app.config['RATE_LIMIT_GET'] = (1, 1)

    def test_ratelimit_home(self):
            self.get_ratelimit("/")

    def test_ratelimit_resource(self):
        self.get_ratelimit(self.known_resource_url)

    def test_ratelimit_item(self):
        self.get_ratelimit(self.item_id_url)

    def test_noratelimits(self):
        self.app.config['RATE_LIMIT_GET'] = None
        if self.app.redis:
            self.app.redis.flushdb()
        r = self.test_client.get("/")
        self.assert200(r.status_code)
        self.assertTrue('X-RateLimit-Remaining' not in r.headers)
        self.assertTrue('X-RateLimit-Limit' not in r.headers)
        self.assertTrue('X-RateLimit-Reset' not in r.headers)

    def get_ratelimit(self, url):
        if self.app.redis:
            # we want the following two GET to be executed within the same
            # tick (1 second)
            t1, t2 = 1, 2
            while (t1 != t2):
                t1 = int(time.time())
                r1 = self.test_client.get(url)
                t2 = int(time.time())
                r2 = self.test_client.get(url)
                if t1 != t2:
                    time.sleep(1)
            self.assertRateLimit(r1)
            self.assertEqual(r2.status_code, 429)
            self.assertTrue(b'Rate limit exceeded' in r2.get_data())

            time.sleep(1)
            self.assertRateLimit(self.test_client.get(url))
        else:
            print("Skipped. Needs a running redis-server and 'pip install "
                  "redis'")

    def assertRateLimit(self, r):
        self.assertTrue('X-RateLimit-Remaining' in r.headers)
        self.assertEqual(r.headers['X-RateLimit-Remaining'], '0')
        self.assertTrue('X-RateLimit-Limit' in r.headers)
        self.assertEqual(r.headers['X-RateLimit-Limit'], '1')
        # renouncing on testing the actual Reset value:
        self.assertTrue('X-RateLimit-Reset' in r.headers)
