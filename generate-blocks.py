import random
from dataclasses import dataclass
from decimal import Decimal
import time
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

    def segments(self, dist: float, variation: float) -> Iterator[Line]:
        s = 0
        l = geod.InverseLine(*self.start, *self.end)
        while s < l.s13:
            s = min(vary(dist, variation), l.s13)
            d = Dict2Line(l.Position(s))
            yield d
            start = d[1]
            l = geod.InverseLine(*start, *self.end)


def AngleDiff(a1, a2):
    a = a1 - a2
    return (a+180) % 360 - 180


def ConstructBuilding(edge: Line, size: Decimal, turn: Decimal) -> Iterator[Line]:
    start, end = edge
    e = geod.Inverse(*start, *end)
    yield Dict2Line(e)
    _, start = edge
    for _ in range(0, 3):
        e = geod.Direct(*start, e['azi1'] + turn, size)
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
        # Make sure we draw inside the block and point towards the centre
        e = geod.Inverse(*start, *end)
        c = geod.Inverse(*start, *centre)
        # pick whichever is closer to going towards the centre
        turn = -90
        if AngleDiff(c['azi1'], e['azi1'] + 90) > AngleDiff(c['azi1'], e['azi1'] - 90):
            turn = 90
        for building_edge in l.segments(size, variation):
            yield list(ConstructBuilding(building_edge, 1, turn))
            # print(list(ConstructBuilding(building_edge, 1)))
            # print(building_edge)
        start = end


def convert2geojson(buildings) -> Iterator[geojson.Feature]:
    i = 0
    for b in buildings:
        i += 1
        print("Building: ", b)
        c = [[*s] for (s, _) in b]
        c += [c[0]]
        p = geojson.Polygon(coordinates=[c], validate=True, precision=8)
        print("Polygon:", p)
        g = geojson.Feature(id=i, geometry=p, properties={
                            "name": f"bld {i}", "generation_time": time.ctime()})
        yield g


def main():
    i: geojson.GeoJSON
    with open('../../alextown.geo2.json') as fh:
        i = geojson.load(fh)
    buildings: list[Iterator[Line]] = []
    f: geojson.Feature
    for f in i.get('features'):
        #print("GeoJson input:", list(geojson.coords(f)))
        #print(geojson.Polygon(coordinates=[[[a,b] for (a, b) in geojson.coords(f)]], validate=True))
        buildings += GenerateBlock(Polygon(list(geojson.coords(f))),
                                   variation=0)
        # c = geojson.coords(f)
        # print(list(c))
        break

    o = geojson.FeatureCollection(list(convert2geojson(buildings)))
    with open('../../public_html/alextown-blocks.geojson', 'w') as fh:
        geojson.dump(o, fh)


if __name__ == '__main__':
    main()
