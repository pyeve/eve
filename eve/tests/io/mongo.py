# -*- coding: utf-8 -*-

from unittest import TestCase
from bson import ObjectId
from datetime import datetime
from eve.io.mongo.parser import parse, ParseError
from eve.io.mongo import Validator, Mongo, MongoJSONEncoder
from eve.utils import config
import simplejson as json


class TestPythonParser(TestCase):

    def test_Eq(self):
        r = parse('a == "whatever"')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'a': 'whatever'})

    def test_Gt(self):
        r = parse('a > 1')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'a': {'$gt': 1}})

    def test_GtE(self):
        r = parse('a >= 1')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'a': {'$gte': 1}})

    def test_Lt(self):
        r = parse('a < 1')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'a': {'$lt': 1}})

    def test_LtE(self):
        r = parse('a <= 1')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'a': {'$lte': 1}})

    def test_NotEq(self):
        r = parse('a != 1')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'a': {'$ne': 1}})

    def test_And_BoolOp(self):
        r = parse('a == 1 and b == 2')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'$and': [{'a': 1}, {'b': 2}]})

    def test_Or_BoolOp(self):
        r = parse('a == 1 or b == 2')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'$or': [{'a': 1}, {'b': 2}]})

    def test_nested_BoolOp(self):
        r = parse('a == 1 or (b == 2 and c == 3)')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'$or': [{'a': 1},
                                     {'$and': [{'b': 2}, {'c': 3}]}]})

    def test_ObjectId_Call(self):
        r = parse('_id == ObjectId("4f4644fbc88e20212c000000")')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'_id': ObjectId("4f4644fbc88e20212c000000")})

    def test_datetime_Call(self):
        r = parse('born == datetime(2012, 11, 9)')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'born': datetime(2012, 11, 9)})

    def test_Attribute(self):
        r = parse('Invoice.number == 1')
        self.assertEqual(type(r), dict)
        self.assertEqual(r, {'Invoice.number': 1})

    def test_unparsed_statement(self):
        self.assertRaises(ParseError, parse, 'print ("hello")')

    def test_bad_Expr(self):
        self.assertRaises(ParseError, parse, 'a | 2')


class TestMongoValidator(TestCase):
    def test_unique_fail(self):
        """ relying on POST and PATCH tests since we don't have an active
        app_context running here """
        pass

    def test_unique_success(self):
        """ relying on POST and PATCH tests since we don't have an active
        app_context running here """
        pass

    def test_objectid_fail(self):
        schema = {'id': {'type': 'objectid'}}
        doc = {'id': 'not_an_object_id'}
        v = Validator(schema, None)
        self.assertFalse(v.validate(doc))
        self.assertTrue('id' in v.errors)
        self.assertTrue('ObjectId' in v.errors['id'])

    def test_objectid_success(self):
        schema = {'id': {'type': 'objectid'}}
        doc = {'id': ObjectId('50656e4538345b39dd0414f0')}
        v = Validator(schema, None)
        self.assertTrue(v.validate(doc))

    def test_transparent_rules(self):
        schema = {'a_field': {'type': 'string'}}
        v = Validator(schema)
        self.assertTrue(v.transparent_schema_rules, True)


class TestMongoDriver(TestCase):
    def test_combine_queries(self):
        mongo = Mongo(None)
        query_a = {'username': {'$exists': True}}
        query_b = {'username': 'mike'}
        combined = mongo.combine_queries(query_a, query_b)
        self.assertEqual(
            combined,
            {'$and': [{'username': {'$exists': True}}, {'username': 'mike'}]}
        )

    def test_json_encoder_class(self):
        mongo = Mongo(None)
        self.assertTrue((mongo.json_encoder_class(), MongoJSONEncoder))
        self.assertTrue((mongo.json_encoder_class(), json.JSONEncoder))

    def test_get_value_from_query(self):
        mongo = Mongo(None)
        simple_query = {config.ID_FIELD: 'abcdef012345678901234567'}
        compound_query = {'$and': [
            {'username': {'$exists': False}},
            {config.ID_FIELD: 'abcdef012345678901234567'}
        ]}
        self.assertEqual(mongo.get_value_from_query(simple_query,
                                                    config.ID_FIELD),
                         'abcdef012345678901234567')
        self.assertEqual(mongo.get_value_from_query(compound_query,
                                                    config.ID_FIELD),
                         'abcdef012345678901234567')

    def test_query_contains_field(self):
        mongo = Mongo(None)
        simple_query = {config.ID_FIELD: 'abcdef012345678901234567'}
        compound_query = {'$and': [
            {'username': {'$exists': False}},
            {config.ID_FIELD: 'abcdef012345678901234567'}
        ]}
        self.assertTrue(mongo.query_contains_field(simple_query,
                                                   config.ID_FIELD))
        self.assertFalse(mongo.query_contains_field(simple_query,
                                                    'fake-field'))
        self.assertTrue(mongo.query_contains_field(compound_query,
                                                   config.ID_FIELD))
        self.assertFalse(mongo.query_contains_field(compound_query,
                                                    'fake-field'))
