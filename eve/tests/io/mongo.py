# -*- coding: utf-8 -*-

from unittest import TestCase
from bson import ObjectId
from datetime import datetime
from eve.io.mongo.parser import parse, ParseError
from eve.io.mongo import Validator, Mongo, MongoJSONEncoder
from eve.tests import TestBase
from eve.tests.test_settings import MONGO_DBNAME
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
        self.assertFalse(v.transparent_schema_rules)

    def test_geojson_not_compilant(self):
        schema = {'location': {'type': 'point'}}
        doc = {'location': [10.0, 123.0]}
        v = Validator(schema)
        self.assertFalse(v.validate(doc))
        self.assertTrue('location' in v.errors)
        self.assertTrue('Point' in v.errors['location'])

    def test_geometry_not_compilant(self):
        schema = {'location': {'type': 'point'}}
        doc = {'location': {"type": "Point", "geometries": [10.0, 123.0]}}
        v = Validator(schema)
        self.assertFalse(v.validate(doc))
        self.assertTrue('location' in v.errors)
        self.assertTrue('Point' in v.errors['location'])

    def test_geometrycollection_not_compilant(self):
        schema = {'location': {'type': 'geometrycollection'}}
        doc = {'location': {"type": "GeometryCollection",
                            "coordinates": [10.0, 123.0]}}
        v = Validator(schema)
        self.assertFalse(v.validate(doc))
        self.assertTrue('location' in v.errors)
        self.assertTrue('GeometryCollection' in v.errors['location'])

    def test_point_success(self):
        schema = {'location': {'type': 'point'}}
        doc = {'location': {"type": "Point", "coordinates": [100.0, 0.0]}}
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

    def test_point_fail(self):
        schema = {'location': {'type': 'point'}}
        doc = {'location': {'type': "Point", 'coordinates': ["asdasd", 123.0]}}
        v = Validator(schema)
        self.assertFalse(v.validate(doc))
        self.assertTrue('location' in v.errors)
        self.assertTrue('Point' in v.errors['location'])

    def test_point_integer_success(self):
        schema = {'location': {'type': 'point'}}
        doc = {'location': {'type': "Point", 'coordinates': [10, 123.0]}}
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

    def test_linestring_success(self):
        schema = {'location': {'type': 'linestring'}}
        doc = {'location': {"type": "LineString",
                            "coordinates": [[100.0, 0.0], [101.0, 1.0]]
                            }}
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

    def test_linestring_fail(self):
        schema = {'location': {'type': 'linestring'}}
        doc = {'location': {'type': "LineString",
                            'coordinates': [[12.0, 123.0], [12, 'eve']]}}
        v = Validator(schema)
        self.assertFalse(v.validate(doc))
        self.assertTrue('location' in v.errors)
        self.assertTrue('LineString' in v.errors['location'])

    def test_polygon_success(self):
        schema = {'location': {'type': 'polygon'}}
        doc = {'location': {"type": "Polygon",
                            "coordinates": [[[100.0, 0.0], [101.0, 0.0],
                                             [101.0, 1.0], [100.0, 1.0],
                                             [100.0, 0.0]]
                                            ]
                            }
               }
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

    def test_polygon_fail(self):
        schema = {'location': {'type': 'polygon'}}
        doc = {'location': {'type': "Polygon",
                            'coordinates': [[[12.0, 23.0], [12.3, 12.5]],
                                            ["eve"]]}}
        v = Validator(schema)
        self.assertFalse(v.validate(doc))
        self.assertTrue('location' in v.errors)
        self.assertTrue('Polygon' in v.errors['location'])

    def test_multipoint_success(self):
        schema = {'location': {'type': 'multipoint'}}
        doc = {'location': {"type": "MultiPoint",
                            "coordinates": [[100.0, 0.0], [101.0, 1.0]]
                            }
               }
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

    def test_multilinestring_success(self):
        schema = {'location': {'type': 'multilinestring'}}
        doc = {'location': {"type": "MultiLineString",
                            "coordinates": [[[100.0, 0.0], [101.0, 1.0]],
                                            [[102.0, 2.0], [103.0, 3.0]]
                                            ]
                            }
               }
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

    def test_multipolygon_success(self):
        schema = {'location': {'type': 'multipolygon'}}
        doc = {'location': {"type": "MultiPolygon",
                            "coordinates": [[[[102.0, 2.0], [103.0, 2.0],
                                              [103.0, 3.0], [102.0, 3.0],
                                              [102.0, 2.0]]],
                                            [[[100.0, 0.0], [101.0, 0.0],
                                              [101.0, 1.0], [100.0, 1.0],
                                              [100.0, 0.0]],
                                             [[100.2, 0.2], [100.8, 0.2],
                                              [100.8, 0.8], [100.2, 0.8],
                                              [100.2, 0.2]]]
                                            ]
                            }
               }
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

    def test_geometrycollection_success(self):
        schema = {'locations': {'type': 'geometrycollection'}}
        doc = {'locations': {'type': "GeometryCollection",
                             "geometries": [{"type": "Point",
                                             "coordinates": [100.0, 0.0]},
                                            {"type": "LineString",
                                             "coordinates": [[101.0, 0.0],
                                                             [102.0, 1.0]]
                                             }
                                            ]
                             }
               }
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

    def test_geometrycollection_fail(self):
        schema = {'locations': {'type': 'geometrycollection'}}
        doc = {'locations': {'type': "GeometryCollection",
                             "geometries": [{"type": "GeoJSON",
                                             "badinput": "lolololololol"}]
                             }
               }
        v = Validator(schema)
        self.assertFalse(v.validate(doc))
        self.assertTrue('locations' in v.errors)
        self.assertTrue('GeometryCollection' in v.errors['locations'])

    def test_dependencies_with_defaults(self):
        schema = {
            'test_field': {'dependencies': 'foo'},
            'foo': {'type': 'string', 'default': 'foo'},
            'bar': {'type': 'string', 'default': 'bar'}
        }
        doc = {'test_field': 'foobar'}

        # With `dependencies` as a str
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

        # With `dependencies` as a dict
        schema['test_field'] = {'dependencies': {'foo': 'foo', 'bar': 'bar'}}
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

        # With `dependencies` as a list
        schema['test_field'] = {'dependencies': ['foo', 'bar']}
        v = Validator(schema)
        self.assertTrue(v.validate(doc))

    def test_removal_of_unnecessary_unique_constraints(self):
        schema = {
            '_id': {
                'type': 'objectid',
                'unique': True
            },
            'foo': {
                'type': 'string',
                'minlength': 2
            }
        }
        expected_schema = {
            '_id': {
                'type': 'objectid'
            },
            'foo': {
                'type': 'string',
                'minlength': 2
            }
        }
        v = Validator(schema)
        schema = v._remove_unique_rules_on_fields_with_unique_index(schema)
        self.assertEqual(expected_schema, schema)


class TestMongoDriver(TestBase):

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
        simple_query = {'_id': 'abcdef012345678901234567'}
        compound_query = {'$and': [
            {'username': {'$exists': False}},
            {'_id': 'abcdef012345678901234567'}
        ]}
        self.assertEqual(mongo.get_value_from_query(simple_query, '_id'),
                         'abcdef012345678901234567')
        self.assertEqual(mongo.get_value_from_query(compound_query, '_id'),
                         'abcdef012345678901234567')

    def test_query_contains_field(self):
        mongo = Mongo(None)
        simple_query = {'_id': 'abcdef012345678901234567'}
        compound_query = {'$and': [
            {'username': {'$exists': False}},
            {'_id': 'abcdef012345678901234567'}
        ]}
        self.assertTrue(mongo.query_contains_field(simple_query, '_id'))
        self.assertFalse(mongo.query_contains_field(simple_query,
                                                    'fake-field'))
        self.assertTrue(mongo.query_contains_field(compound_query, '_id'))
        self.assertFalse(mongo.query_contains_field(compound_query,
                                                    'fake-field'))

    def test_delete_returns_status(self):
        db = self.connection[MONGO_DBNAME]
        count = db.contacts.count()
        result = db.contacts.remove()
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result.get('n'), count)
        self.assertEqual(result.get('ok'), 1)
        self.connection.close()
