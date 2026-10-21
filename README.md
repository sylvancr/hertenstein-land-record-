# Hertenstein Land Record

A shared record of the Stella Matutina land at Hertenstein, Weggis: the parcels, the landscape architect's proposals pinned to the map, federal and cantonal environmental data, species and habitat records, the ecological plan, and visitor readings.

Live page: https://sylvancr.github.io/hertenstein-land-record-/ . You can also open `index.html` locally.

## What is here

- `index.html`: the whole page. No build step.
- `terrain.html`: a 3D model of the land with sun and shade by day and hour, hours of sun, yearly sun, steepness, facing, wetness and frost hollows. Reads `data/terrain.json`, which `tools/build_terrain.py` builds from public elevation tiles (run it again to rebuild, or point it at swissALTI3D for sharper detail).
- `data/`: one JSON file per table (parcels, proposals, public data layers, species, measures, stations, gaps, log and so on). The page reads these files on load.
- `docs/`: the ecological master plan and the visitor readings protocol (first drafts, 13 October 2026).
- `readings-form/`: the Google Apps Script form visitors will use to log readings. Not deployed yet; see `readings-form/SETUP.md`.
- `vendor/`: d3 7.9.0, used for the map, and three.js 0.169.0, used for the 3D terrain.

## Updating it

Edit the JSON file for the table you want to change and commit. Each file is a list of rows; keep the existing field names. The page picks up changes on the next load.

Land changes shown here are proposals. Site and hotel operations belong to Hertenstein.

## Sources

Map coordinates are Swiss LV95. Public data comes from map.geo.admin.ch and the Canton of Lucerne geoportal, read on 14 October 2026. The architect's sheets are dated 29 July 2026.
