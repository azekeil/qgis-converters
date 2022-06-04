import random
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterator

import geojson
import geopy.distance
from geographiclib.geodesic import Geodesic
from geographiclib.geodesicline import GeodesicLine

geod: Geodesic = Geodesic.WGS84  # define the WGS84 ellipsoid


def vary(value: float, variation: float) -> float:
    """ value is in meters
        variation is a fraction of value
        returns the value +/- variation * random.random()
    """
    v = variation * value
    return value - v + random.random() * v * 2


Point = list[Decimal]

Line = Point, Point

@dataclass
class Polygon:
    _v: list[Point]

    def coords(self) -> Iterator[Point]:
        return iter(self._v)

    def centre(self) -> Point:
        i = 0
        totalx = 0
        totaly = 0

        for c in self.coords():
            totalx += c[0]
            totaly += c[1]
            i += 1
        return Point([totalx/i, totaly/i])


@dataclass
class MyGeodesicLine:
    a: Point
    b: Point

    def length(self) -> float:
        """returns length in meters"""
        return geopy.distance.geodesic(self.a,  self.b).meters
    
    def inverse(self):
        return geod.Inverse(*self.a, *self.b)

    def coords(self, dist: float) -> Point:
        d = geod.Direct(*self.a, self.inverse()['azi1'], dist)
        return Point([d['lat2'], d['lon2']])

    def waypoints(self, dist: float, variation: float) -> Iterator[GeodesicLine]:
        l = geod.InverseLine(*self.a, *self.b)
        s = 0.0
        while s < l.s13:
            g = l.Position(s)
            yield g
            s = min(s + vary(dist, variation), l.s13)

    def segments(self, dist: float, variation: float) -> Iterator[GeodesicLine]:
        start = self.a
        end = self.b
        l = geod.InverseLine(*start, *end)
        s = dist
        p = l.Position(s)
        g = geod.InverseLine(*self.a, p['lat2'], p['lon2'])
        yield g
        while s < l.s13:
            s = min(s + vary(dist, variation), l.s13)
            p = g.Position(s)
            g = geod.InverseLine(g.lat1, g.lon1, p['lat2'], p['lon2'])
            yield g


def ConstructBuilding(edge: GeodesicLine) -> Iterator[GeodesicLine]:
    e = edge
    for i in range(0,3):
        print(i, e)
        yield geod.DirectLine(e.lat1, e.lon1, e.azi1, e.s13)
        e = geod.DirectLine(e.lat2, e.lon2, e.azi1 + 90, e.s13)


def GenerateBlock(polygon: Polygon, size: Decimal = 1, variation: Decimal = 0.1):
    """ size is in meters
        variation is the limit of the fraction of size to + or -
    """
    centre = polygon.centre()
    print(centre)
    coords_iter = polygon.coords()
    start: Point = next(coords_iter)
    end: Point
    for end in coords_iter:
        l = MyGeodesicLine(start, end)
        print(l, l.length())
        for building_edge in l.segments(size, variation):
            #print(list(ConstructBuilding(building_edge)))
            print(building_edge)
        start = end


def main():
    o: geojson.GeoJSON
    with open('../../alextown.geo2.json') as fh:
        o = geojson.load(fh)
    f: geojson.Feature
    for f in o.get('features'):
        GenerateBlock(Polygon(list(geojson.coords(f))))
        # c = geojson.coords(f)
        # print(list(c))
        break


if __name__ == '__main__':
    main()
