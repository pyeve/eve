# -*- coding: utf-8 -*-

"""
    eve.io.mongo.geo
    ~~~~~~~~~~~~~~~~~~~

    Geospatial functions and classes for mongo IO layer

    :copyright: (c) 2017 by Nicola Iarocci.
    :license: BSD, see LICENSE for more details.
"""
from eve.utils import config


class GeoJSON(dict):
    def __init__(self, json):
        try:
            self["type"] = json["type"]
        except KeyError:
            raise TypeError("Not compliant to GeoJSON")
        self.update(json)
        if not config.ALLOW_CUSTOM_FIELDS_IN_GEOJSON and len(self.keys()) != 2:
            raise TypeError("Not compliant to GeoJSON")

    def _correct_position(self, position):
        return (
            isinstance(position, list)
            and len(position) > 1
            and all(isinstance(pos, int) or isinstance(pos, float) for pos in position)
        )


class Geometry(GeoJSON):
    def __init__(self, json):
        super(Geometry, self).__init__(json)
        try:
            if (
                not isinstance(self["coordinates"], list)
                or self["type"] != self.__class__.__name__
            ):
                raise TypeError
        except (KeyError, TypeError):
            raise TypeError("Geometry not compliant to GeoJSON")


class GeometryCollection(GeoJSON):
    def __init__(self, json):
        super(GeometryCollection, self).__init__(json)
        try:
            if not isinstance(self["geometries"], list):
                raise TypeError
            for geometry in self["geometries"]:
                factory = factories[geometry["type"]]
                factory(geometry)
        except (KeyError, TypeError, AttributeError):
            raise TypeError("Geometry not compliant to GeoJSON")


class Point(Geometry):
    def __init__(self, json):
        super(Point, self).__init__(json)
        if not self._correct_position(self["coordinates"]):
            raise TypeError


class MultiPoint(GeoJSON):
    def __init__(self, json):
        super(MultiPoint, self).__init__(json)
        for position in self["coordinates"]:
            if not self._correct_position(position):
                raise TypeError


class LineString(GeoJSON):
    def __init__(self, json):
        super(LineString, self).__init__(json)
        for position in self["coordinates"]:
            if not self._correct_position(position):
                raise TypeError


class MultiLineString(GeoJSON):
    def __init__(self, json):
        super(MultiLineString, self).__init__(json)
        for linestring in self["coordinates"]:
            for position in linestring:
                if not self._correct_position(position):
                    raise TypeError


class Polygon(GeoJSON):
    def __init__(self, json):
        super(Polygon, self).__init__(json)
        for linestring in self["coordinates"]:
            for position in linestring:
                if not self._correct_position(position):
                    raise TypeError


class MultiPolygon(GeoJSON):
    def __init__(self, json):
        super(MultiPolygon, self).__init__(json)
        for polygon in self["coordinates"]:
            for linestring in polygon:
                for position in linestring:
                    if not self._correct_position(position):
                        raise TypeError


class Feature(GeoJSON):
    def __init__(self, json):
        super(Feature, self).__init__(json)
        try:
            geometry = self["geometry"]
            factory = factories[geometry["type"]]
            factory(geometry)

        except (KeyError, TypeError, AttributeError):
            raise TypeError("Feature not compliant to GeoJSON")


class FeatureCollection(GeoJSON):
    def __init__(self, json):
        super(FeatureCollection, self).__init__(json)
        try:
            if not isinstance(self["features"], list):
                raise TypeError
            for feature in self["features"]:
                Feature(feature)
        except (KeyError, TypeError, AttributeError):
            raise TypeError("FeatureCollection not compliant to GeoJSON")


factories = dict(
    [
        (_type.__name__, _type)
        for _type in [
            GeometryCollection,
            Point,
            MultiPoint,
            LineString,
            MultiLineString,
            Polygon,
            MultiPolygon,
        ]
    ]
)
