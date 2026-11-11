"""Step 1 of the Sevastopol build: pull what the app needs out of an OpenStreetMap extract.

Usage: python3 extract_sevastopol.py sevastopol.osm.pbf sev_raw.json
Input: https://download.openstreetmap.fr/extracts/europe/ukraine/sevastopol-latest.osm.pbf
       (the Geofabrik Crimea file works too, it is just bigger). Needs osmium and shapely.
"""
import osmium, json, sys, time, base64
import shapely.wkb
BB = (44.37, 33.36, 44.86, 33.95)          # south, west, north, east
CITY_REL = 1574364                         # OSM relation of the city boundary
def inbb(lat, lon): return BB[0] <= lat <= BB[2] and BB[1] <= lon <= BB[3]
fab = osmium.geom.WKBFactory()
AM = {'cafe', 'restaurant', 'bar', 'pub', 'ice_cream', 'fast_food', 'theatre', 'cinema', 'marketplace', 'biergarten',
      'food_court', 'fountain', 'library', 'university', 'place_of_worship', 'ferry_terminal', 'bus_station'}
TO = {'gallery', 'museum', 'artwork', 'attraction', 'viewpoint'}
HI = {'memorial', 'monument', 'ruins', 'archaeological_site', 'castle', 'fort', 'citywalls', 'city_gate', 'tomb',
      'monastery', 'cannon', 'ship', 'aircraft', 'tank', 'building', 'church', 'battlefield'}
PL = {'city', 'town', 'village', 'suburb', 'neighbourhood', 'quarter', 'square'}
WAY_KEYS = ('highway', 'footway', 'foot', 'access', 'name', 'tunnel', 'indoor', 'level', 'layer', 'service', 'area', 'route', 'bridge')
def names(t, d):
    if 'name' in t: d['name'] = t['name']
    if 'name:en' in t: d['en'] = t['name:en']
class H(osmium.SimpleHandler):
    def __init__(s):
        super().__init__(); s.pois = []; s.ways = []; s.areas = []; s.coast = []; s.trees = []; s.rows = []
    def poi(s, t, lat, lon):
        d = {}
        a = t.get('amenity'); sh = t.get('shop'); to = t.get('tourism'); hi = t.get('historic'); pl = t.get('place')
        if a in AM: d['amenity'] = a
        if sh and sh not in ('vacant', 'no'): d['shop'] = sh
        if to in TO: d['tourism'] = to
        if hi in HI: d['historic'] = hi
        if pl in PL: d['place'] = pl
        if t.get('railway') in ('station', 'halt'): d['railway'] = 'station'
        if t.get('leisure') == 'outdoor_seating': d['leisure'] = 'outdoor_seating'
        if t.get('natural') == 'beach' and 'name' in t: d['beach'] = 1
        if not d: return
        if 'wikidata' in t or 'wikipedia' in t or 'heritage' in t: d['wiki'] = 1
        names(t, d); s.pois.append([round(lat, 6), round(lon, 6), d])
    def node(s, n):
        if not n.location.valid() or len(n.tags) == 0: return
        lat, lon = n.location.lat, n.location.lon
        if not inbb(lat, lon): return
        if n.tags.get('natural') == 'tree': s.trees.append([round(lat, 5), round(lon, 5)]); return
        s.poi(n.tags, lat, lon)
    def way(s, w):
        t = w.tags
        hw = t.get('highway'); co = t.get('natural') == 'coastline'; fe = t.get('route') == 'ferry'; row = t.get('natural') == 'tree_row'
        if not (hw or co or fe or row): return
        if hw in ('construction', 'proposed', 'elevator', 'corridor', 'platform', 'emergency_bay', 'rest_area', 'busway', 'raceway', 'via_ferrata', 'escape'): return
        try: pts = [(n.ref, n.lat, n.lon) for n in w.nodes]
        except Exception: return
        if not any(inbb(p[1], p[2]) for p in pts): return
        ll = [[round(p[1], 6), round(p[2], 6)] for p in pts]
        if co: s.coast.append(ll); return
        if row: s.rows.append(ll); return
        if fe and not hw:
            if t.get('foot') == 'no': return
            d = {'highway': 'ferry'}; names(t, d)
        else: d = {k: t[k] for k in WAY_KEYS if k in t}
        s.ways.append([d, [p[0] for p in pts], [int(round((p[1] - BB[0]) * 1e6)) for p in pts], [int(round((p[2] - BB[1]) * 1e6)) for p in pts]])
    def area(s, a):
        t = a.tags
        kind = None
        le = t.get('leisure'); lu = t.get('landuse'); na = t.get('natural'); hi = t.get('historic')
        if not a.from_way() and a.orig_id() == CITY_REL: kind = 'boro'
        elif le in ('park', 'garden', 'nature_reserve', 'playground'): kind = le
        elif lu in ('recreation_ground', 'village_green', 'cemetery', 'forest'): kind = lu
        elif na in ('wood', 'water'): kind = na
        elif t.get('waterway') == 'riverbank': kind = 'water'
        elif lu == 'military' or t.get('military') in ('base', 'barracks', 'naval_base', 'airfield', 'danger_area', 'training_area', 'range'): kind = 'military'
        elif na == 'beach': kind = 'beach'
        elif hi in HI: kind = 'historic'
        elif t.get('tourism') in TO or t.get('amenity') in AM or t.get('place') == 'square': kind = 'poi'
        if not kind: return
        if t.get('access') in ('private', 'no') and kind not in ('water', 'military', 'boro'): return
        try: g = shapely.wkb.loads(fab.create_multipolygon(a), hex=True)
        except Exception: return
        w, so, e, n = g.bounds
        if e < BB[1] or w > BB[3] or n < BB[0] or so > BB[2]: return
        if kind in ('historic', 'poi', 'beach'):          # these also count as points of interest
            p = g.representative_point(); s.poi(t, p.y, p.x)
            if kind == 'poi': return
            if kind == 'beach' or (kind == 'historic' and (g.area < 2e-7 or 'name' not in t)): return
        if kind != 'boro':
            if g.area < 4e-8: return
            g = g.simplify(0.00002)
        else: g = g.simplify(0.00001)
        d = {'k': kind, 'name': t.get('name', ''), 'wkb': base64.b64encode(g.wkb).decode()}
        if 'name:en' in t: d['en'] = t['name:en']
        s.areas.append(d)
t0 = time.time()
h = H(); h.apply_file(sys.argv[1], locations=True)
print('parsed %.0fs' % (time.time() - t0), 'pois', len(h.pois), 'ways', len(h.ways), 'areas', len(h.areas), 'coast', len(h.coast), 'trees', len(h.trees), 'rows', len(h.rows), flush=True)
import collections
print(collections.Counter(a['k'] for a in h.areas))
with open(sys.argv[2], 'w') as f: json.dump({'bb': BB, 'pois': h.pois, 'ways': h.ways, 'areas': h.areas, 'coast': h.coast, 'trees': h.trees, 'rows': h.rows}, f, separators=(',', ':'), ensure_ascii=False)
print('done %.0fs' % (time.time() - t0), flush=True)
