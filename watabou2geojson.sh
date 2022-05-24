#!/bin/bash

# convert saved json from https://watabou.github.io/city-generator to geoJSON format

if [[ -z $1 ]]; then
    echo "expects filename as first parameter"
    exit 1
fi

jq -r ' {type: "FeatureCollection", features: [ .features[] | select(.id == "buildings") | .coordinates | to_entries | .[].key as $i | {type: "Feature", id: ($i+1) , geometry: {type: "Polygon", coordinates: [ .[$i].value[] + [.[$i].value[0][0]]] }} ]  }' "$@" > buildings.geojson
jq -r ' {type: "FeatureCollection", features: [ .features[] | select(.id == "roads") | .geometries | to_entries | .[].key as $i | {type: "Feature", id: ($i+1) , geometry: {type: "LineString", coordinates: [ .[$i].value.coordinates[] ] }} ]  }' "$@" > roads.geojson

