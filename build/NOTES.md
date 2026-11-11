# Alive Maps: build notes

Live site: https://alive-maps-chi.vercel.app/ (Vercel deploys every commit to `main`).

## What is in this repository

- `index.html`: the whole app (HTML, CSS and JavaScript in one file). Edit this file for any change to the page, the search, the routing or the directions.
- `meta.json`: map shapes (land, parks, water), place names, street names, sights, tile index.
- `nodes.b64.txt`, `topo.b64.txt`, `attr.b64.txt`, `geom.b64.txt`: the street graph, as base64 text of binary arrays.
- `build/build_nyc.py`: the script that makes the five data files from raw data.
- `build/NOTES.md`: this file.

## How the app works

- The graph has 550,132 nodes and 807,893 edges for the five boroughs. Coordinates are metres from the top-left of the box lat 40.47 to 40.93, lon -74.27 to -73.68.
- Each edge has six scores from 0 to 9: green, water, tree, lively, historic, traffic. They are packed as nibbles in `attr.b64.txt`.
- Routing is A* in the browser. Edge cost = length x m^lambda, where m = (1 + 1.3 x traffic) / (1 + 1.8 x good).
- Three routes: Fastest (lambda 0), Alive (best alive score within +12% length), Most alive (best within +45%). The search tries several lambda values up to 3.
- Place search uses three sources: the built-in `places` list, Photon (photon.komoot.io) for venues, and NYC Planning GeoSearch for addresses. Results outside the borough polygons are dropped.
- Share links: the address bar always holds a link to the walk on screen, and the "Share this walk" button copies it (on a phone it opens the share sheet). Format: `?a=lat,lon&an=name&b=lat,lon&bn=name`, plus `r=most` or `r=fast` when the chosen route is not Alive, and `p=` six 0/1 digits when a preference chip is off. A link wins over the walk saved in the browser. Links use latitude and longitude, so they still work after a data rebuild.

## Binary layout (little-endian)

- nodes: uint16 x[N], uint16 y[N]
- topo: uint32 a[E], uint32 b[E], uint16 length in 0.5 m units [E]
- attr: uint8 kind[E], uint8 scores[3E], uint16 park id[E], uint8 district id[E], 1 pad byte if E is odd, uint16 street-name id[E]
- geom: uint8 count[E] of middle points, then uint16 x,y pairs
- Edge kinds: 0 footpath, 1 sidewalk, 2 crossing, 3 minor street, 4 tertiary, 5 secondary, 6 primary.
- Edges are sorted by 1 km tile. `meta.toff` gives the first edge of each tile.

## How to rebuild the data

The raw inputs are not in this repository. They are on Ray's computer in `Downloads\alive-maps-data`:

- `nyc_part_00` to `nyc_part_04`: join them and decompress with xz to get `nyc_raw.json` (OpenStreetMap extract made by `extract_nyc.py` from the BBBike NewYork.osm.pbf).
- `nyc_trees.u16.xz`: NYC street tree census points.
- `alive_historic_districts.geojson` and `alive_landmark_sites.geojson` in `Downloads`: NYC landmarks data (coordinates in EPSG:2263).

Then run `build_nyc.py` (needs numpy, shapely 2, pyproj). Fix the input and output paths at the top first.

## Data credits

Map data © OpenStreetMap contributors (ODbL). Trees, landmarks and historic districts from NYC Open Data.
