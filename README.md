# Hertenstein Land Record

A shared record of the Stella Matutina land at Hertenstein, Weggis: the parcels, the landscape architect's proposals pinned to the map, federal and cantonal environmental data, species and habitat records, the ecological plan, and visitor readings.

Live page: https://sylvancr.github.io/hertenstein-land-record-/ . You can also open `index.html` locally.

## What is here

- `index.html`: the whole page, in four tabs (Map, Sun and terrain, The land, Plan); the detail sits in sections that open on a click. No build step.
- `terrain.html`: a 3D model of the land with its buildings and trees: sun and shade by day and hour, hours of sun, yearly sun, steepness, facing, wetness and frost hollows. It is the Sun and terrain tab of `index.html` and also works on its own. It reads `data/terrain.json`, which `tools/build_terrain.py` builds from public elevation tiles, and `data/site_objects.json`, one row per building, tree or grove, traced from the plans by `tools/trace_sheets.py`. Correct a height or a tree there, then run `tools/build_terrain.py` again so the shade follows.
- `data/`: one JSON file per table (parcels, proposals, public data layers, species, measures, stations, gaps, log and so on). The page reads these files on load.
- `docs/`: the ecological master plan and the visitor readings protocol (first drafts, 13 October 2026).
- `readings-form/`: the Google Apps Script form visitors will use to log readings. Not deployed yet; see `readings-form/SETUP.md`.
- `vendor/`: d3 7.9.0, used for the map, and three.js 0.169.0, used for the 3D terrain.

## Updating it

Edit the JSON file for the table you want to change and commit. Each file is a list of rows; keep the existing field names. The page picks up changes on the next load.

Land changes shown here are proposals. Site and hotel operations belong to Hertenstein.

## Sources

Map coordinates are Swiss LV95. Public data comes from map.geo.admin.ch and the Canton of Lucerne geoportal, read on 14 October 2026. The architect's sheets are dated 29 July 2026.
