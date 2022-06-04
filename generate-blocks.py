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


def Dict2Line(d: dict) -> Line:
    return Line((Point((d['lat1'], d['lon1'])), Point((d['lat2'], d['lon2']))))


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

    def segments(self, dist: float, variation: float) -> Iterator[Point]:
        s = 0
        l = geod.InverseLine(*self.start, *self.end)
        yield Point(self.start)
        while s < l.s13:
            s = min(vary(dist, variation), l.s13)
            p = l.Position(s)
            start = Point((p['lat1'], p['lon1']))
            end = Point((p['lat2'], p['lon2']))
            yield end
            start = end
            l = geod.InverseLine(*start, *self.end)


def ConstructBuilding(edge: Line, size: Decimal) -> Iterator[Point]:
    start, end = edge
    e = geod.Inverse(*start, *end)
    yield Dict2Line(e)
    for i in range(1, 3):
        e = geod.Direct(*start, e['azi1'] + 90, size)
        d = Dict2Line(e)
        yield d
        _, start = d


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
            yield list(ConstructBuilding(building_edge, 1))
            # print(list(ConstructBuilding(building_edge, 1)))
            # print(building_edge)
            break
        start = end


def convert2geojson(buildings) -> Iterator[geojson.Feature]:
    for b in buildings:
        print("Building: ", b)
        c = [(s, e) for (s, e) in b]
        print("Building coordinates: ", c)
        yield geojson.Feature(geometry=geojson.Polygon(coordinates=c))


def main():
    i: geojson.GeoJSON
    with open('../../alextown.geo2.json') as fh:
        i = geojson.load(fh)
    buildings: list[Iterator[Line]] = []
    f: geojson.Feature
    for f in i.get('features'):
        print("GeoJson input:", list(geojson.coords(f)))
        buildings += GenerateBlock(Polygon(list(geojson.coords(f))))
        # c = geojson.coords(f)
        # print(list(c))
        break

    o = geojson.GeoJSON(convert2geojson(buildings))
    with open('../../alextown-blocks.geojson', 'w') as fh:
        geojson.dump(o, fh)


if __name__ == '__main__':
    main()
