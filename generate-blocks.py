import random
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterator
from typing_extensions import Self

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


Point = tuple[Decimal, Decimal]

Line = tuple[Point, Point]


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
    start: Point
    end: Point

    def length(self) -> float:
        """returns length in meters"""
        return geopy.distance.geodesic(self.start,  self.end).meters

    def position(self, dist: float) -> Self:
        l = geod.InverseLine(*self.start, *self.end)
        p = l.Position(dist)
        return Self(Point((p['lat1'], p['lon1'])), Point((p['lat2'], p['lon2'])))

    def waypoints(self, dist: float):
        s = dist
        start = self.start
        end = self.end
        l = geod.InverseLine(*start, *end)
        while s < l.s13:
            yield self.position(s)
            s = min(s + dist, l.s13)

    def segments(self, dist: float, variation: float) -> Iterator[Line]:
        start = self.start
        end = self.end
        l = geod.InverseLine(*start, *end)
        s = dist
        while s < l.s13:
            p = l.Position(s)
            start = Point((p['lat1'], p['lon1']))
            end = Point((p['lat2'], p['lon2']))
            yield Line((start, end))
            start = end
            s = min(s + vary(dist, variation), l.s13)
            l = geod.InverseLine(*start, *end)


def ConstructBuilding(edge: Line) -> Iterator[Line]:
    e = edge
    for i in range(0, 3):
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
            # print(list(ConstructBuilding(building_edge)))
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
