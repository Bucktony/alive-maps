import json, math, collections, base64, lzma, gzip, time
import numpy as np
import shapely
from shapely import wkb as swkb
from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer

T0 = time.time()
def log(*a): print('[%5.0fs]' % (time.time() - T0), *a, flush=True)
UP = '/mnt/user-data/uploads/Downloads/'
OUT = '/home/claude/alive/site2/'
d = json.load(open('/home/claude/alive/nyc_raw.json'))
BB = d['bb']
LAT0, LON0 = BB[2], BB[1]
KX = 111320 * math.cos(math.radians(40.7)); KY = 111050.0
def px(lon): return (np.asarray(lon, dtype=float) - LON0) * KX
def py(lat): return (LAT0 - np.asarray(lat, dtype=float)) * KY
def proj_geom(g): return shapely.transform(g, lambda c: np.column_stack([px(c[:, 0]), py(c[:, 1])]))
W, H = float(px(BB[3])), float(py(BB[0]))
log('extent m', W, H)

boros = {a['name']: proj_geom(swkb.loads(base64.b64decode(a['wkb']))) for a in d['areas'] if a['k'] == 'boro'}
city = unary_union(list(boros.values())).buffer(0)
shapely.prepare(city)

# ---------- ways ----------
FOOT_OK = ('yes', 'designated', 'permissive')
STREET = {'residential': 3, 'living_street': 3, 'unclassified': 3, 'service': 3, 'tertiary': 4, 'tertiary_link': 4,
          'secondary': 5, 'secondary_link': 5, 'primary': 6, 'primary_link': 6}
PATHS = {'footway', 'path', 'pedestrian', 'steps', 'bridleway', 'track', 'cycleway'}
TRAFFIC_W = {'motorway': 1.0, 'motorway_link': 0.9, 'trunk': 1.0, 'trunk_link': 0.9, 'primary': 0.75,
             'primary_link': 0.6, 'secondary': 0.5, 'secondary_link': 0.4, 'tertiary': 0.25, 'tertiary_link': 0.2}
def neg(v):
    try: return float(str(v).split(';')[0]) < 0
    except Exception: return False

kept = []
traffic = collections.defaultdict(list)
dens_pts = []
for t, refs, la, lo in d['ways']:
    hw = t['highway']
    xs = (np.asarray(lo) * 1e-6) * KX
    ys = (BB[2] - BB[0] - np.asarray(la) * 1e-6) * KY
    dens_pts.append((xs[0], ys[0]))
    if hw in TRAFFIC_W and t.get('tunnel') not in ('yes', 'building_passage') and len(xs) > 1:
        traffic[TRAFFIC_W[hw]].append(np.column_stack([xs, ys]))
    foot = t.get('foot'); acc = t.get('access')
    if foot == 'no' or len(refs) < 2: continue
    if acc in ('private', 'no', 'customers', 'delivery') and foot not in FOOT_OK: continue
    if t.get('indoor') == 'yes': continue
    if hw in STREET:
        if hw == 'service' and not (t.get('name') or t.get('service') == 'alley'): continue
        kind = STREET[hw]
    elif hw in PATHS:
        if hw == 'cycleway' and foot not in FOOT_OK: continue
        if hw in ('footway', 'steps') and (t.get('tunnel') == 'yes' or neg(t.get('level')) or neg(t.get('layer'))): continue
        fw = t.get('footway')
        if fw == 'access_aisle': continue
        kind = 1 if fw == 'sidewalk' else 2 if fw in ('crossing', 'traffic_island') else 0
    else: continue
    kept.append((kind, refs, xs, ys, t.get('name', '')))
log('kept ways', len(kept))
allx = np.concatenate([k[2] for k in kept]); ally = np.concatenate([k[3] for k in kept])
ins_all = shapely.contains_xy(city, allx, ally)
log('inside share', ins_all.mean())

use = collections.Counter(); runs = []; o = 0
for kind, refs, xs, ys, wname in kept:
    n = len(refs); ins = ins_all[o:o + n]; o += n
    i = 0
    while i < n:
        if not ins[i]: i += 1; continue
        j = i
        while j + 1 < n and ins[j + 1]: j += 1
        if j > i:
            r = refs[i:j + 1]; runs.append((kind, r, xs[i:j + 1], ys[i:j + 1], wname))
            for k, rr in enumerate(r): use[rr] += 2 if k in (0, len(r) - 1) else 1
        i = j + 1
del kept
ea_r, eb_r, ekind, ecoords, ename = [], [], [], [], []
for kind, refs, xs, ys, wname in runs:
    s = 0
    for k in range(1, len(refs)):
        if use[refs[k]] > 1 or k == len(refs) - 1:
            if refs[s] != refs[k]:
                ea_r.append(refs[s]); eb_r.append(refs[k]); ekind.append(kind); ename.append(wname)
                ecoords.append(np.column_stack([xs[s:k + 1], ys[s:k + 1]]))
            s = k
del runs
log('edges raw', len(ea_r))

par = {}
def find(a):
    r = a
    while par.setdefault(r, r) != r: r = par[r]
    while par[a] != r: par[a], a = r, par[a]
    return r
for a, b in zip(ea_r, eb_r):
    ra, rb = find(a), find(b)
    if ra != rb: par[ra] = rb
roots = [find(a) for a in ea_r]
comp = collections.Counter(roots)
keep_roots = {r for r, c in comp.items() if c >= 300}
log('components', len(comp), 'kept', len(keep_roots), [c for r, c in comp.most_common(6)])
sel = [i for i, r in enumerate(roots) if r in keep_roots]
ea_r = [ea_r[i] for i in sel]; eb_r = [eb_r[i] for i in sel]; ekind = np.array([ekind[i] for i in sel], dtype=np.uint8)
ecoords = [ecoords[i] for i in sel]; ename = [ename[i] for i in sel]
E = len(sel)

flat = np.vstack(ecoords); idx = np.repeat(np.arange(E), [len(c) for c in ecoords])
lines = shapely.simplify(shapely.linestrings(flat, indices=idx), 1.2)
del ecoords, flat, idx
npts = shapely.get_num_coordinates(lines)
for tol in (3, 6, 12, 25):
    big = npts > 250
    if not big.any(): break
    lines[big] = shapely.simplify(lines[big], tol); npts = shapely.get_num_coordinates(lines)
L = shapely.length(lines)
log('edges', E, 'km', L.sum() / 1000, 'kinds', collections.Counter(ekind.tolist()))

# sort edges by 1 km tile
b = shapely.bounds(lines); mx = (b[:, 0] + b[:, 2]) / 2; my = (b[:, 1] + b[:, 3]) / 2
TS = 1000; TW = int(W // TS) + 1; TH = int(H // TS) + 1
tid = (my // TS).astype(int) * TW + (mx // TS).astype(int)
order = np.argsort(tid, kind='stable')
lines = lines[order]; L = L[order]; ekind = ekind[order]; tid = tid[order]; npts = npts[order]
ea_r = [ea_r[i] for i in order]; eb_r = [eb_r[i] for i in order]; ename = [ename[i] for i in order]
tile_off = np.searchsorted(tid, np.arange(TW * TH + 1)).astype(int)

nid = {}
for r in ea_r:
    if r not in nid: nid[r] = len(nid)
for r in eb_r:
    if r not in nid: nid[r] = len(nid)
N = len(nid)
EA = np.array([nid[r] for r in ea_r], dtype=np.uint32); EB = np.array([nid[r] for r in eb_r], dtype=np.uint32)
coords, cidx = shapely.get_coordinates(lines, return_index=True)
starts = np.concatenate([[0], np.cumsum(npts)[:-1]]); ends = starts + npts - 1
NX = np.zeros(N); NY = np.zeros(N)
NX[EA] = coords[starts, 0]; NY[EA] = coords[starts, 1]; NX[EB] = coords[ends, 0]; NY[EB] = coords[ends, 1]
log('graph nodes', N)

# ---------- samples ----------
k = np.maximum(1, np.rint(L / 18)).astype(int)
se = np.repeat(np.arange(E), k)
first = np.concatenate([[0], np.cumsum(k)[:-1]])
q = np.arange(len(se)) - np.repeat(first, k)
frac = (q + 0.5) / np.repeat(k, k)
spts = shapely.line_interpolate_point(lines[se], frac, normalized=True)
S = len(spts); cnt = k.astype(float)
log('samples', S)
def edge_mean(v): return np.bincount(se, weights=v, minlength=E) / cnt
def within_any(geoms, dist=None):
    out = np.zeros(S)
    if not len(geoms): return out
    tr = STRtree(geoms)
    ii = tr.query(spts, predicate='within') if dist is None else tr.query(spts, predicate='dwithin', distance=dist)
    out[np.unique(ii[0])] = 1
    return out
def count_within(geoms, dist, weights=None):
    tr = STRtree(geoms); ii = tr.query(spts, predicate='dwithin', distance=dist)
    w = None if weights is None else np.asarray(weights)[ii[1]]
    return np.bincount(ii[0], weights=w, minlength=S)
def majority(geoms, names, minshare=0.5):
    """per-edge index (1-based) of the named polygon most samples fall in"""
    tr = STRtree(geoms); ii = tr.query(spts, predicate='within')
    key = se[ii[0]].astype(np.int64) * 100000 + ii[1]
    u, c = np.unique(key, return_counts=True)
    e_i = u // 100000; g_i = u % 100000
    out = np.zeros(E, dtype=int); best = np.zeros(E)
    for e, g, n in zip(e_i, g_i, c):
        if n > best[e]: best[e] = n; out[e] = g + 1
    out[best < minshare * cnt] = 0
    return out

# ---------- areas ----------
GREEN = {'park', 'garden', 'nature_reserve', 'wood', 'forest', 'recreation_ground', 'village_green', 'cemetery', 'playground'}
frame = box(0, 0, W, H)
greens, waters = [], []
for a in d['areas']:
    if a['k'] == 'boro': continue
    g = proj_geom(swkb.loads(base64.b64decode(a['wkb'])))
    if not g.is_valid: g = g.buffer(0)
    if g.is_empty: continue
    if a['k'] in GREEN:
        if g.area >= 400: greens.append((g, a['name'], a['k']))
    elif a['k'] == 'water' and g.area >= 500: waters.append(g)
log('greens', len(greens), 'waters', len(waters))
ggeoms = [g for g, _, _ in greens]
in_green = within_any(ggeoms)
near_green = within_any([g for g in ggeoms if g.area >= 3000], 30)
f_green = edge_mean(np.maximum(in_green, 0.45 * near_green))

coast = [proj_geom(LineString([(c[1], c[0]) for c in cl])) for cl in d['coast'] if len(cl) > 1]
wlines = coast + [g.boundary for g in waters if g.area >= 3000]
f_water = edge_mean(np.maximum(within_any(wlines, 35), 0.55 * within_any(wlines, 75)))
log('green/water done')

tq = np.frombuffer(lzma.decompress(open(UP + 'alive-maps-data/nyc_trees.u16.xz', 'rb').read()), dtype=np.uint16).reshape(-1, 2).astype(float)
tx = px(tq[:, 1] * 1e-5 - 74.27); ty = py(tq[:, 0] * 1e-5 + 40.47)
ot = np.array(d['trees']); tx = np.concatenate([tx, px(ot[:, 1])]); ty = np.concatenate([ty, py(ot[:, 0])])
tk = np.unique(np.column_stack([np.rint(tx / 3), np.rint(ty / 3)]), axis=0) * 3.0
n_trees = len(tk)
tc = edge_mean(count_within(shapely.points(tk[:, 0], tk[:, 1]), 14))
log('trees', n_trees)

LW = {'cafe': 1.2, 'restaurant': 1.0, 'bar': 0.8, 'pub': 0.8, 'ice_cream': 1.2, 'fast_food': 0.4, 'theatre': 1.0,
      'cinema': 0.8, 'marketplace': 1.2, 'biergarten': 1.0, 'food_court': 0.8}
TWt = {'gallery': 0.8, 'museum': 1.0, 'artwork': 0.8, 'attraction': 0.8}
lx, ly, lw = [], [], []; sights = []  # [name, cat, x, y]
for lat, lon, t in d['pois']:
    w = 0; am = t.get('amenity'); sh = t.get('shop'); to = t.get('tourism'); nm = t.get('name')
    if am in LW: w = LW[am]
    elif sh: w = 1.2 if sh in ('bakery', 'books', 'florist', 'pastry', 'coffee', 'cheese', 'greengrocer') else 0.5
    elif to in TWt: w = TWt[to]
    elif t.get('leisure') == 'outdoor_seating': w = 1.0
    x, y = float(px(lon)), float(py(lat))
    if w: lx.append(x); ly.append(y); lw.append(w)
    if nm:
        cat = None
        if am in ('cafe', 'ice_cream') or sh in ('bakery', 'pastry', 'coffee'): cat = 'c'
        elif to in ('museum', 'gallery'): cat = 'm'
        elif to == 'artwork' or t.get('historic') in ('memorial', 'monument') or am == 'fountain': cat = 'a'
        elif to in ('viewpoint', 'attraction'): cat = 'v'
        elif am in ('theatre', 'cinema'): cat = 't'
        elif am == 'marketplace': cat = 'k'
        if cat: sights.append([nm, cat, x, y])
lc = edge_mean(count_within(shapely.points(lx, ly), 28, lw))
log('lively pois', len(lx), 'sights', len(sights))

tf = Transformer.from_crs(2263, 4326, always_xy=True)
hds, hd_names = [], []
for f in json.load(open(UP + 'alive_historic_districts.geojson'))['features']:
    p = f['properties']
    if not f['geometry'] or p.get('status_of_') not in (None, 'DESIGNATED') or p.get('current_') == 'No': continue
    g = proj_geom(shapely.transform(shape(f['geometry']), lambda c: np.column_stack(tf.transform(c[:, 0], c[:, 1]))))
    if not g.is_valid: g = g.buffer(0)
    hds.append(g); hd_names.append(p.get('area_name') or 'Historic district')
lms = {}
for f in json.load(open(UP + 'alive_landmark_sites.geojson'))['features']:
    p = f['properties']
    if not p.get('latitude') or p.get('lpc_sitest') not in (None, 'Designated'): continue
    nm = (p.get('lpc_name') or '').strip()
    if nm: lms[nm] = (float(px(float(p['longitude']))), float(py(float(p['latitude']))))
lm_xy = np.array(list(lms.values()))
log('historic districts', len(hds), 'landmarks', len(lms))
in_hd = within_any(hds)
nlm = count_within(shapely.points(lm_xy[:, 0], lm_xy[:, 1]), 45)
f_arch = edge_mean(np.minimum(1, 0.65 * in_hd + 0.45 * np.minimum(nlm, 2)))

tv = np.zeros(S)
for wgt, arrs in traffic.items():
    tl = shapely.linestrings(np.vstack(arrs), indices=np.repeat(np.arange(len(arrs)), [len(a) for a in arrs]))
    tv = np.maximum(tv, wgt * within_any(tl, 22))
    if wgt >= 0.9: tv = np.maximum(tv, 0.55 * within_any(tl, 55))
f_traf = edge_mean(tv)
log('traffic done')

def norm(v, q=95):
    s = np.percentile(v[v > 0], q); return np.minimum(1, v / s), s
f_tree, s1 = norm(tc); f_live, s2 = norm(lc, 97)
log('tree scale', s1, 'lively scale', s2)
feats = [f_green, f_water, f_tree, f_live, f_arch, f_traf]
for nme, f in zip('green water tree lively arch traffic'.split(), feats): log(nme, 'mean %.3f share>0.3 %.3f' % (f.mean(), (f > 0.3).mean()))
fq = np.clip(np.rint(np.column_stack(feats) * 9), 0, 9).astype(np.uint8)

named = [(g, n) for g, n, kk in greens if n and g.area >= 4000]
pn_names = sorted(set(n for _, n in named)); pn_idx = {n: i for i, n in enumerate(pn_names)}
m = majority([g for g, _ in named], None)
epark = np.where(m > 0, np.array([pn_idx[n] + 1 for _, n in named] + [0])[m - 1], 0).astype(np.uint16)
edist = majority(hds, None, 0.6).astype(np.uint8)
log('edges in named parks', (epark > 0).sum(), 'in districts', (edist > 0).sum())

# street names: unnamed sidewalks and paths take the nearest named street within 25 m
ename = np.array(ename, dtype=object)
has = np.array([bool(n) for n in ename]); street = has & (ekind >= 3)
mid = shapely.line_interpolate_point(lines, 0.5, normalized=True)
si = np.where(street)[0]; stree = STRtree(lines[si])
need = np.where(~has & (ekind != 2))[0]
qi, ti = stree.query_nearest(mid[need], max_distance=25, all_matches=False)
ename[need[qi]] = ename[si[ti]]
names = sorted(set(n for n in ename if n)); nidx = {n: i + 1 for i, n in enumerate(names)}
enm = np.array([nidx.get(n, 0) for n in ename], dtype='<u2')
log('names', len(names), 'edges named', (enm > 0).mean())

# ---------- basemap ----------
cl = unary_union([c for c in coast] + [frame.boundary])
faces = [f.intersection(frame) for f in polygonize(cl)]
dp = np.array(dens_pts); ptree = STRtree(shapely.points(dp[:, 0], dp[:, 1]))
land = []
for f in faces:
    if f.is_empty or f.area < 300: continue
    n = len(ptree.query(f, predicate='contains'))
    if n / (f.area / 1e6) > 15: land.append(f)
log('faces', len(faces), 'land', len(land), 'km2', sum(f.area for f in land) / 1e6)
def rings(g, tol, minarea):
    out = []; g = g.simplify(tol)
    for p in ([g] if isinstance(g, Polygon) else list(getattr(g, 'geoms', []))):
        if not isinstance(p, Polygon) or p.area < minarea: continue
        r = [[int(round(v)) for xy in p.exterior.coords for v in xy]]
        for h in p.interiors:
            if Polygon(h).area > 1500: r.append([int(round(v)) for xy in h.coords for v in xy])
        out.append(r)
    return out
land_r = [r for f in land for r in rings(f, 5, 500)]
green_r = [r for g, n, kk in greens if g.intersects(frame) for r in rings(g.intersection(frame), 3, 600)]
water_r = [r for g in waters if g.intersects(frame) for r in rings(g.intersection(frame), 4, 800)]
boro_r = [r for g in boros.values() for r in rings(g, 15, 1e5)]
log('rings', len(land_r), len(green_r), len(water_r))

places = []; seen = set(); labels = []
def inside(x, y): return bool(shapely.contains_xy(city, x, y))
def add(name, typ, x, y):
    kk = (name.lower(), typ)
    if kk in seen or not inside(x, y): return
    seen.add(kk); places.append([name, typ, int(round(x)), int(round(y))])
for lat, lon, t in d['pois']:
    nm = t.get('name')
    if not nm: continue
    x, y = float(px(lon)), float(py(lat))
    if t.get('place'):
        if inside(x, y): labels.append([nm, int(x), int(y), 1]); add(nm, 'n', x, y)
    elif t.get('railway') == 'station': add(nm + ' station', 's', x, y)
    elif t.get('tourism') in ('museum', 'attraction', 'viewpoint', 'gallery') or t.get('amenity') in ('theatre', 'library', 'university'): add(nm, 'a', x, y)
for g, n, kk in sorted(greens, key=lambda z: -z[0].area):
    if n and g.area >= 4000:
        p = g.representative_point(); add(n, 'p', p.x, p.y)
        if g.area >= 120000 and inside(p.x, p.y): labels.append([n, int(p.x), int(p.y), 0])
for n, (x, y) in lms.items(): add(n, 'l', x, y)
for n, g in boros.items(): p = g.representative_point(); labels.append([n, int(p.x), int(p.y), 2])
sights = [[n, c, int(x), int(y)] for n, c, x, y in sights if inside(x, y)] + [[n, 'l', int(x), int(y)] for n, (x, y) in lms.items()]
log('places', len(places), 'labels', len(labels), 'sights', len(sights))

# ---------- output ----------
import os
os.makedirs(OUT, exist_ok=True)
nodes = np.column_stack([np.clip(np.rint(NX), 0, 65535), np.clip(np.rint(NY), 0, 65535)]).astype('<u2')
open(OUT + 'nodes.bin', 'wb').write(nodes[:, 0].tobytes() + nodes[:, 1].tobytes())
el = np.clip(np.rint(L * 2), 1, 65535).astype('<u2')
open(OUT + 'topo.bin', 'wb').write(EA.astype('<u4').tobytes() + EB.astype('<u4').tobytes() + el.tobytes())
f3 = np.column_stack([fq[:, 0] * 16 + fq[:, 1], fq[:, 2] * 16 + fq[:, 3], fq[:, 4] * 16 + fq[:, 5]]).astype(np.uint8)
open(OUT + 'attr.bin', 'wb').write(ekind.tobytes() + f3.tobytes() + epark.astype('<u2').tobytes() + edist.tobytes() + (b'\0' if E % 2 else b'') + enm.tobytes())
inter = np.ones(len(coords), dtype=bool); inter[starts] = False; inter[ends] = False
gcnt = (npts - 2).astype(np.uint8)
gpts = np.clip(np.rint(coords[inter]), 0, 65535).astype('<u2')
open(OUT + 'geom.bin', 'wb').write(gcnt.tobytes() + gpts.tobytes())
meta = {'w': int(W), 'h': int(H), 'lat0': LAT0, 'lon0': LON0, 'kx': KX, 'ky': KY, 'N': N, 'E': E, 'G': int(len(gpts)),
        'ts': TS, 'tw': TW, 'th': TH, 'toff': tile_off.tolist(),
        'parks': pn_names, 'districts': hd_names, 'names': names, 'land': land_r, 'green': green_r, 'water': water_r, 'boro': boro_r,
        'labels': labels, 'places': places, 'sights': sights,
        'stats': {'trees': int(n_trees), 'pois': len(lx), 'landmarks': len(lms), 'districts': len(hds), 'km': int(L.sum() / 1000)}}
s = json.dumps(meta, separators=(',', ':'), ensure_ascii=False)
open(OUT + 'meta.json', 'w').write(s)
for fn in os.listdir(OUT):
    b = open(OUT + fn, 'rb').read(); log(fn, '%.2f MB' % (len(b) / 1e6), 'gz %.2f' % (len(gzip.compress(b, 3)) / 1e6))

import base64 as _b
for n in ['nodes','topo','attr','geom']:
    open(OUT + n + '.b64.txt','wb').write(_b.b64encode(open(OUT + n + '.bin','rb').read()))
