# Alive Maps: build notes

Live site: https://alive-maps-chi.vercel.app/ (Vercel deploys every commit to `main`).

## What is in this repository

- `index.html`: the whole app (HTML, CSS and JavaScript in one file). Edit this file for any change to the page, the search, the routing or the directions.
- `meta.json`: map shapes (land, parks, water), place names, street names, sights, tile index.
- `nodes.b64.txt`, `topo.b64.txt`, `attr.b64.txt`, `geom.b64.txt`: the street graph, as base64 text of binary arrays.
- `build/build_nyc.py`: the script that makes the five data files from raw data.
- City picker: the "Select where you are" menu beside the logo lists New York and Sevastopol. Each option's value is the address of that city's page. To add a city, add an `<option>` in `index.html` and a matching swap in `build/make_sevastopol_page.py`.
- `og.png`: the picture shown when a link to the site is pasted into X, iMessage or Slack (1200 x 630). It is a screenshot of the app. Retake it after a visual change.
- `build/NOTES.md`: this file.

## How the app works

- The graph has 550,132 nodes and 807,893 edges for the five boroughs. Coordinates are metres from the top-left of the box lat 40.47 to 40.93, lon -74.27 to -73.68.
- Each edge has six scores from 0 to 9: green, water, tree, lively, historic, traffic. They are packed as nibbles in `attr.b64.txt`.
- Routing is A* in the browser. Edge cost = length x m^lambda, where m = (1 + 1.3 x traffic) / (1 + 1.8 x good).
- Three routes: Fastest (lambda 0), Alive (best alive score within +15% length, or +3 minutes on a short walk), Most alive (best within +67%, so 30 minutes can become 50, or +6 minutes on a short walk). Very short walks are held to 1.75 and 2.5 times the fastest. The limits are in `slack()`. The search tries lambda values up to 8 and homes in on each limit. A longer route is only chosen when its alive score is higher, so the extra time is not always used.
- Place search uses three sources: the built-in `places` list, Photon (photon.komoot.io) for venues, and NYC Planning GeoSearch for addresses. Results outside the borough polygons are dropped.
- Share links: the address bar always holds a link to the walk on screen, and the "Share this walk" button copies it (on a phone it opens the share sheet). Format: `?a=lat,lon&an=name&b=lat,lon&bn=name`, plus `r=most` or `r=fast` when the chosen route is not Alive, and `p=` six 0/1 digits when a preference chip is off. `v=2024`, `v=1951` or `v=1924` is added when an aerial photo view is on. A link wins over the walk saved in the browser. Links use latitude and longitude, so they still work after a data rebuild.
- Map look: warm cream land, white streets, a blue Alive route, a dashed grey Fastest route. Little trees are scattered through parks and along the leafy stretches of the chosen route (tree or green score 5 or more). Stops on the route show as round icon badges; tapping one opens a card with its name. Up to four cards (a park, a historic stretch, a landmark, a café) show by default.
- Layout: on a wide screen the map fills the window and the controls float over its left side. Below 860 px wide they stack above and below the map.
- Aerial photo views: the Map / Satellite / 1951 / 1924 switch on the map. Satellite is the City of New York's 2024 aerial photos; 1951 and 1924 are its historic sets. The tiles come from the city's public ArcGIS service (`tiles.arcgis.com/tiles/yG5s3afENB5iO9fj`, layers `NYC_Orthos_2024`, `NYC_Orthos_1951`, `Ortho_1924_Mosaic`). No key is needed. If the city moves the service, change `PHOTO` and `LAYERS` in `index.html`. Newer years appear there as `NYC_Orthos_<year>`.
- Beauty points: every route shows what it earns. Points are 1 for every 10 metres, scaled by the route's alive score, so a nicer route earns more than a faster one. "I walked it" adds the walk to a list kept in the browser (`localStorage` key `alive-walks`, shared by all cities). The "Your beauty points" card shows the total, a day streak, and minutes in nature this week against 120 (the weekly figure from White and others, 2019, Scientific Reports). Nature minutes count stretches where the green, water or tree score is 5 or more. There is no login and no check that the walk happened. Share copies a sentence with the points and the link.

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

## Sevastopol

Page: `/sevastopol/` on the live site. Everything for it is in the `sevastopol/` folder: `index.html`, the five data files and its own `og.png`.

### What is different from New York

- `sevastopol/index.html` is made from the New York `index.html` by `build/make_sevastopol_page.py`. Do not edit it by hand. Change `index.html`, or change the swaps in that script, then run `python3 build/make_sevastopol_page.py` from the repository root. If a swap no longer matches, the script stops and names it.
- Street and place names are the local OpenStreetMap names, so they are in Russian, as on the street signs. Places that have an English name in OpenStreetMap can also be found by that name. The page text is in English.
- There is no tree census, so the tree score is the share of ground under tree canopy (3 m or taller) within about 17 m of the street, from the Meta and WRI Global Canopy Height map.
- There is no city register of landmarks. Landmarks are OpenStreetMap `historic` features (monuments, memorials, forts, ruins, the Chersonesus site). The 26 named historic sites with a mapped outline take the place of historic districts.
- The passenger boats across the bay (Артбухта to Северная, Артбухта to Радиогорка, Графская пристань to Северная) are in the graph as edge kind 7. A crossing counts as its length plus 400 m for waiting. The map draws them as dashed blue lines, the directions say "Take the ferry", and a note asks the walker to check that the boats are running. The Inkerman boat and the seasonal Balaklava beach boats are left out.
- Paths and small roads inside mapped military land are left out (985 segments, 132 km), and places inside it are not listed.
- Courtyard service roads are kept as walkable, because few pavements are mapped. Motorway-class (trunk) roads are not walkable.
- Address search uses Photon only. The saved walk uses its own browser key, so it does not mix with New York.
- Beaches are a kind of stop.
- There are no aerial photo views. The New York photos stop at the city line and Sevastopol has no free source like them yet, so the Map / Satellite switch is hidden there.

### Numbers

39,510 nodes and 54,147 edges, 5,524 km of streets and paths. 2,948 cafés, shops and venues. 449 monuments and memorials. About 21% of street length is under tree canopy. The five data files are 2.8 MB together.

### How to rebuild the data

Unlike New York, every input is public, so the build can be run anywhere. It needs Python with `osmium`, `shapely` 2, `numpy` and `rasterio`.

1. Download `https://download.openstreetmap.fr/extracts/europe/ukraine/sevastopol-latest.osm.pbf` (7 MB, updated daily). The Geofabrik Crimea file has the same data.
2. `python3 build/extract_sevastopol.py sevastopol-latest.osm.pbf sev_raw.json`
3. Download the four canopy tiles (870 MB) named at the top of `build/canopy_sevastopol.py`, then `python3 build/canopy_sevastopol.py <tile folder> canopy.npz`. The canopy map does not change, so this step is only needed once.
4. `python3 build/build_sevastopol.py sev_raw.json canopy.npz sevastopol/`
5. Open the page and try the six sample walks. Retake `sevastopol/og.png` (1200 x 630) after a visual change.

### Using this for another city

The three Sevastopol scripts are the template for a city that has only OpenStreetMap. Change the bounding box and the boundary relation id in the extract script, the canopy tile names, and the city text and sample walks in `make_sevastopol_page.py`. The coastline step in `build_sevastopol.py` (carrying the open ends of the coast to the map edge) is specific to this coast and needs a look for each new city.
