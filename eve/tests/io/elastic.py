# -*- coding: utf-8 -*-

from unittest import TestCase
from datetime import datetime
from eve.io.elastic import Validator, Elastic
from eve.io.elastic.elastic import convert_dates
from eve.utils import config


class TestElasticValidator(TestCase):
    pass

class TestElasticDriver(TestCase):
    def test_convert_dates(self):
        doc = {}
        doc[config.LAST_UPDATED] = '2013-11-06T07:56:01.414944+00:00'
        doc[config.DATE_CREATED] = '2013-11-06T07:56:01.414944+00:00'

        convert_dates(doc)

        self.assertIsInstance(doc[config.LAST_UPDATED], datetime)
        self.assertIsInstance(doc[config.DATE_CREATED], datetime)
