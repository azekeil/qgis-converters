#!/bin/bash

# convert layout.json from fantasytowngenerator.com to geoJSON format

if [[ -z $1 ]]; then
    echo "expects filename as first parameter"
    exit 1
fi

jq -r '{type: "FeatureCollection", features: [ .buildings[] | {type: "Feature", geometry: {type: "Polygon", coordinates: [[ .buildingLayout[] | [.x, .y] ]]}} + del(.buildingLayout) ] }' "$@"
