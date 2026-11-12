"""Make sevastopol/index.html from the New York index.html.

The Sevastopol page is the same app with the city-specific parts swapped. After a change to index.html
(design, routing, directions), run this again from the repository root so Sevastopol gets the change too:

    python3 build/make_sevastopol_page.py

Each swap below must match the New York page exactly once. If index.html changed near one of them the script
stops and names the swap to fix.
"""
import sys
src = open('index.html', encoding='utf-8').read()
SITE = 'https://alive-maps-chi.vercel.app/'
DESC = 'Walking directions for Sevastopol that trade a few minutes for parks, sea views, trees, old stones and streets with life.'
def swap(old, new, count=1):
    global src
    n = src.count(old)
    if n != count: sys.exit('Swap failed (found %d times, expected %d): %s' % (n, count, old[:90]))
    src = src.replace(old, new)

# ----- head -----
swap('Walking directions for New York City that trade a few minutes for parks, trees, old buildings and streets with life.', DESC, 2)
swap('<title>Alive Maps NYC</title>', '<title>Alive Maps Sevastopol</title>')
swap('<meta property="og:title" content="Alive Maps NYC">', '<meta property="og:title" content="Alive Maps Sevastopol">')
swap('content="%s"' % SITE, 'content="%ssevastopol/"' % SITE)
swap(SITE + 'og.png', SITE + 'sevastopol/og.png', 2)

# ----- page text -----
# the city picker: this page is the chosen one, and New York is one folder up
swap('<option value="./" selected>New York</option><option value="sevastopol/">Sevastopol</option>', '<option value="../">New York</option><option value="./" selected>Sevastopol</option>')
swap('Walking directions for a more alive journey: parks, trees, old buildings and streets with life, for a few minutes more.',
     'Walking directions for a more alive journey: parks, sea views, trees, old stones and streets with life, for a few minutes more.')
swap('placeholder="Start: address, venue or place"', 'placeholder="Start: улица, place or landmark"')
swap('placeholder="End: address, venue or place"', 'placeholder="End: улица, place or landmark"')
swap('Type a park, station or landmark, or pick on the map.', 'Type a park, beach, pier or landmark, or pick on the map.')
swap('Limits of this version: it does not know park opening hours, so check before a night walk. Directions are a guide. Follow street signs and signals. Street life uses places mapped in OpenStreetMap, which is not complete.',
     'Limits of this version: the map is only as current as OpenStreetMap, so a path, a gate or an embankment may be closed on the day. Paths inside mapped military land are left out, but not every fence is on the map. Ferries stop in bad weather and when the bay is closed. Few pavements are mapped here, so many walks follow the street itself. Directions are a guide. Follow signs and signals.')
swap('Map data © OpenStreetMap contributors. Trees and landmarks from NYC Open Data. Aerial photos from the City of New York. Place search by Photon (Komoot) and NYC Planning GeoSearch.',
     'Map data © OpenStreetMap contributors. Tree cover from the Global Canopy Height map by Meta and the World Resources Institute. Place search by Photon (Komoot).')
swap('aria-label="Map of New York City with the fastest route and two alive routes"', 'aria-label="Map of Sevastopol with the fastest route and two alive routes"')
swap('Loading New York streets…', 'Loading Sevastopol streets…', 2)
swap("title: 'Alive Maps NYC'", "title: 'Alive Maps Sevastopol'")
swap("'The walk in that link is outside New York City. Here is another one.'", "'The walk in that link is outside Sevastopol. Here is another one.'")
swap("'You are outside New York City, so there is no street data for your spot.'", "'You are outside Sevastopol, so there is no street data for your spot.'")
swap("'The start is outside New York City. Pick a start in one of the five boroughs.'", "'The start is outside the mapped area. Pick a start inside the city boundary.'")
swap("'The end is outside New York City. Pick an end in one of the five boroughs.'", "'The end is outside the mapped area. Pick an end inside the city boundary.'")
swap("'That point is outside New York City. Pick a point in one of the five boroughs.'", "'There is no mapped street near that point. Pick a point closer to a street or path.'")
swap("'No walking route joins these two points. There is water between them and no bridge on foot.'", "'No walking route joins these two points on this map.'")
swap("const NONE = 'No match yet. Try the street address, or use Pick on map.';", "const NONE = 'No match yet. Try the name in Russian, or use Pick on map.';")
swap("{ k: 'arch', label: 'Historic architecture', short: 'Historic blocks', w: 0.55 }", "{ k: 'arch', label: 'History and monuments', short: 'Historic places', w: 0.55 }")
swap("{ k: 'tree', label: 'Tree-lined streets', short: 'Tree cover', w: 0.55 }", "{ k: 'tree', label: 'Shade from trees', short: 'Tree cover', w: 0.55 }")
swap("{ k: 'water', label: 'Waterfront', short: 'Along the water', w: 0.9 }", "{ k: 'water', label: 'Sea and bays', short: 'Along the water', w: 0.9 }")

# ----- sample walks -----
a = src.index('const TRIPS = ['); b = src.index('];', a) + 2
src = src[:a] + """const TRIPS = [
  ['Centre: Count\\'s Quay to the Panorama', [44.6170, 33.5267], 'Графская пристань', [44.5955, 33.5233], 'Панорама «Оборона Севастополя»'],
  ['Seafront: Artillery Bay to Chersonesus', [44.6142, 33.5191], 'Артбухта', [44.6112, 33.4922], 'Херсонес Таврический'],
  ['By ferry: Count\\'s Quay to Mikhailovskaya Battery', [44.6170, 33.5267], 'Графская пристань', [44.6281, 33.5257], 'Михайловская батарея'],
  ['Ship Side: Nakhimov Square to Malakhov Kurgan', [44.6169, 33.5256], 'площадь Нахимова', [44.6047, 33.5480], 'Малахов курган'],
  ['West: Victory Park to Omega Beach', [44.6031, 33.4558], 'Парк Победы', [44.5976, 33.4441], 'Пляж Омега'],
  ['Balaklava: the quay to Cembalo Fortress', [44.5010, 33.5977], 'Балаклава, набережная', [44.4948, 33.5995], 'Крепость Чембало'],
];""" + src[b:]

# ----- data and search -----
swap("const KIND = { P: 'Park', D: 'Historic district', W: 'Waterfront', l: 'Landmark', c: 'Café', m: 'Museum', a: 'Art', v: 'Sight', t: 'Theatre', k: 'Market' };",
     "const KIND = { P: 'Park', D: 'Historic site', W: 'Waterfront', l: 'Landmark', c: 'Café', m: 'Museum', a: 'Art', v: 'Sight', t: 'Theatre', k: 'Market', b: 'Beach' };")
swap("const TYPE = { p: 'Park', s: 'Subway', l: 'Landmark', n: 'Area', a: 'Place', x: 'Address', v: 'Place' };",
     "const TYPE = { p: 'Park', s: 'Station', f: 'Pier', b: 'Beach', l: 'Landmark', n: 'Area', a: 'Place', x: 'Address', v: 'Place' };")
# the data files sit beside this page, also when the address has no closing slash
swap("const bin = f => fetch(f.replace('.bin', '.b64.txt'))", "const HERE = /\\/$|\\.html$/.test(location.pathname) ? '' : location.pathname.split('/').pop() + '/';\nconst bin = f => fetch(HERE + f.replace('.bin', '.b64.txt'))")
swap("fetch('meta.json')", "fetch(HERE + 'meta.json')")
swap("'alive-v2'", "'alive-sev-v1'", 2)
swap("bbox=-74.27,40.47,-73.68,40.93", "bbox=33.36,44.37,33.95,44.86")
# search has to match Cyrillic as well as Latin letters
swap("const norm = t => t.toLowerCase().normalize('NFD').replace(/[^a-z0-9]/g, '');", "const norm = t => t.toLowerCase().replace(/ё/g, 'е').normalize('NFD').replace(/[^\\p{L}\\p{N}]/gu, '');")
# Photon gives addresses too (there is no city address service here): a house shows as street and number
swap(".filter(f => f.properties.name).map(f => { const pr = f.properties, [x, y] = toXY(f.geometry.coordinates[1], f.geometry.coordinates[0]); return [pr.name + (pr.street ? ' · ' + pr.street : '') + (pr.district || pr.city ? ', ' + (pr.district || pr.city) : ''), 'v', x, y, norm(pr.name)]; })",
     ".filter(f => f.properties.name || (f.properties.street && f.properties.housenumber)).map(f => { const pr = f.properties, [x, y] = toXY(f.geometry.coordinates[1], f.geometry.coordinates[0]), ad = pr.street ? pr.street + (pr.housenumber ? ', ' + pr.housenumber : '') : ''; return pr.name ? [pr.name + (ad ? ' · ' + ad : ''), 'v', x, y, norm(pr.name)] : [ad, 'x', x, y, norm(ad)]; })")
a = src.index("      const ad = getJSON(GEO + "); b = src.index("\n", a)
src = src[:a] + "      const ad = Promise.resolve([]);" + src[b:]
swap("if (fails > qs.length) { geoOK = false;", "if (fails >= qs.length) { geoOK = false;")
swap("const GEO = 'https://geosearch.planninglabs.nyc/v2/autocomplete?text=';\n", "")
swap("(${s.km.toLocaleString()} km in all five boroughs) gets six scores: parks, waterfront, ${s.trees.toLocaleString()} mapped trees, ${s.pois.toLocaleString()} cafés, shops and venues, ${s.districts} historic districts with ${s.landmarks.toLocaleString()} landmarks, and distance from heavy traffic.",
     "(${s.km.toLocaleString()} km, from the city centre to Balaklava, the North Side and the hills) gets six scores: parks and woods, the sea and the bays, tree cover measured from satellite images, ${s.pois.toLocaleString()} cafés, shops and venues, ${s.districts} historic sites with ${s.landmarks.toLocaleString()} monuments and memorials, and distance from heavy traffic. The passenger boats across the bay count as part of a walk.")

# ----- ferries: edge kind 7 -----
swap("T = { path: new Path2D(), side: new Path2D(), minor: new Path2D(), major: new Path2D() };", "T = { path: new Path2D(), side: new Path2D(), minor: new Path2D(), major: new Path2D(), ferry: new Path2D() };")
swap("const k = ek[e], p = k === 0 ? T.path : k < 3 ? T.side : k === 3 ? T.minor : T.major;", "const k = ek[e], p = k === 7 ? T.ferry : k === 0 ? T.path : k < 3 ? T.side : k === 3 ? T.minor : T.major;")
swap("  if (!sat && s > 0.1) pass('path', css['m-path'], lw(2.2, 0.9));", "  if (s > 0.03) { ctx.setLineDash([lw(40, 5), lw(32, 4)]); ctx.lineCap = 'butt'; pass('ferry', css.me, lw(6, 1.4)); ctx.setLineDash([]); ctx.lineCap = 'round'; }\n  if (!sat && s > 0.1) pass('path', css['m-path'], lw(2.2, 0.9));")
swap("recs.push([ek[e] === 2 ? null : enm[e] ?", "recs.push([ek[e] === 7 ? '\\u26F4' + (enm[e] ? D.names[enm[e] - 1] : 'the ferry') : ek[e] === 2 ? null : enm[e] ?")
swap("if (!k) text = `Head ${", "if (nm[0] === '\\u26F4') { r.ferry = true; text = `Take the ferry ${nm.slice(1)}`; }\n    else if (!k) text = `Head ${")
swap("  if (same(R.alive, f) && same(R.most, f)) { $('msg').hidden = false; $('msg').textContent = 'The fastest route is already the nicest one here. Try a longer trip.'; }",
     "  if (same(R.alive, f) && same(R.most, f)) { $('msg').hidden = false; $('msg').textContent = 'The fastest route is already the nicest one here. Try a longer trip.'; }\n  if (R[state.sel].ferry) { $('msg').hidden = false; $('msg').textContent = 'This walk crosses the bay by passenger ferry. The time includes about 5 minutes of waiting. Check that the boats are running today.'; }")
# ferry steps must not swallow or be swallowed by short neighbours
swap("if (last && (g.len < 20 || last.name === g.name)) last.len += g.len; else out.push(g);", "if (last && (g.len < 20 || last.name === g.name) && (g.name || '')[0] !== '\\u26F4') last.len += g.len; else out.push(g);")

# ----- aerial photos -----
# The photo views use the City of New York's own aerial photos, which stop at the city line. Sevastopol has no such source yet, so the switch is hidden and no photo layer is on offer.
swap('<div class="views" id="views" role="group" aria-label="Map view">', '<div class="views" id="views" role="group" aria-label="Map view" hidden>')
swap("const LAYERS = { '2024': 'NYC_Orthos_2024', '2006': 'NYC_Orthos_2006', '1996': 'Ortho_1996_Mosaic', '1951': 'NYC_Orthos_1951', '1924': 'Ortho_1924_Mosaic' },", "const LAYERS = {},")

# ----- beaches -----
swap("for (const ts of ['P', 'DW', 'lm', 'c', 'avtk'])", "for (const ts of ['P', 'DW', 'lm', 'c', 'bavtk'])")
swap("t === 'c' ? css.cafe : t === 'W' ? css.me :", "t === 'c' ? css.cafe : t === 'W' || t === 'b' ? css.me :")
swap("else if (t === 'W') { for (const dy of [-1.8, 2])", "else if (t === 'W' || t === 'b') { for (const dy of [-1.8, 2])")

open('sevastopol/index.html', 'w', encoding='utf-8').write(src)
print('wrote sevastopol/index.html', len(src), 'characters')
