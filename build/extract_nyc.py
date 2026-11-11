import osmium, json, lzma, sys, time, base64
import shapely.wkb
BB=(40.47,-74.27,40.93,-73.68)
def inbb(lat,lon): return BB[0]<=lat<=BB[2] and BB[1]<=lon<=BB[3]
fab=osmium.geom.WKBFactory()
AM={'cafe','restaurant','bar','pub','ice_cream','fast_food','theatre','cinema','marketplace','biergarten','food_court','fountain','library','university','place_of_worship'}
TO={'gallery','museum','artwork','attraction','viewpoint'}
WAY_KEYS=('highway','footway','foot','access','name','tunnel','indoor','level','layer','service','area')
BORO={'Manhattan','Brooklyn','Queens','The Bronx','Bronx','Staten Island'}
ext=[90,180,-90,-180]
class H(osmium.SimpleHandler):
    def __init__(s):
        super().__init__(); s.pois=[]; s.ways=[]; s.areas=[]; s.coast=[]; s.trees=[]
    def node(s,n):
        if not n.location.valid(): return
        lat,lon=n.location.lat,n.location.lon
        if lat<ext[0]: ext[0]=lat
        if lat>ext[2]: ext[2]=lat
        if lon<ext[1]: ext[1]=lon
        if lon>ext[3]: ext[3]=lon
        if len(n.tags)==0 or not inbb(lat,lon): return
        t=n.tags
        if t.get('natural')=='tree': s.trees.append([round(lat,5),round(lon,5)]); return
        d={}
        a=t.get('amenity'); sh=t.get('shop'); to=t.get('tourism'); hi=t.get('historic'); pl=t.get('place'); rw=t.get('railway'); le=t.get('leisure')
        if a in AM: d['amenity']=a
        if sh and sh not in ('vacant','no'): d['shop']=sh
        if to in TO: d['tourism']=to
        if hi in ('memorial','monument'): d['historic']=hi
        if pl in ('neighbourhood','suburb','quarter'): d['place']=pl
        if rw=='station': d['railway']=rw
        if le=='outdoor_seating': d['leisure']=le
        if d:
            if 'name' in t: d['name']=t['name']
            s.pois.append([round(lat,6),round(lon,6),d])
    def way(s,w):
        t=w.tags
        hw=t.get('highway'); co=t.get('natural')=='coastline'
        if not hw and not co: return
        if hw in ('construction','proposed','elevator','corridor','platform','emergency_bay','rest_area','busway','raceway'): return
        try: pts=[(n.ref,n.lat,n.lon) for n in w.nodes]
        except Exception: return
        if not any(inbb(p[1],p[2]) for p in pts): return
        if co:
            s.coast.append([[round(p[1],6),round(p[2],6)] for p in pts]); return
        s.ways.append([{k:t[k] for k in WAY_KEYS if k in t},[p[0] for p in pts],[int(round((p[1]-BB[0])*1e6)) for p in pts],[int(round((p[2]-BB[1])*1e6)) for p in pts]])
    def area(s,a):
        t=a.tags
        kind=None
        le=t.get('leisure'); lu=t.get('landuse'); na=t.get('natural')
        if le in ('park','garden','nature_reserve','playground'): kind=le
        elif lu in ('recreation_ground','village_green','cemetery','forest'): kind=lu
        elif na in ('wood','water'): kind=na
        elif t.get('waterway')=='riverbank': kind='water'
        elif t.get('boundary')=='administrative' and t.get('name') in BORO: kind='boro'
        if not kind: return
        if t.get('access') in ('private','no') and kind!='water': return
        try: g=shapely.wkb.loads(fab.create_multipolygon(a),hex=True)
        except Exception: return
        w,so,e,n=g.bounds
        if e<BB[1] or w>BB[3] or n<BB[0] or so>BB[2]: return
        if kind!='boro':
            if g.area < 4e-8: return
            g=g.simplify(0.00002)
        else: g=g.simplify(0.00001)
        s.areas.append({'k':kind,'name':t.get('name',''),'al':t.get('admin_level',''),'wkb':base64.b64encode(g.wkb).decode()})
t0=time.time()
h=H(); h.apply_file(sys.argv[1],locations=True)
print('parsed',time.time()-t0,len(h.pois),len(h.ways),len(h.areas),len(h.coast),len(h.trees),'extent',ext,flush=True)
with open(sys.argv[2],"w") as f: json.dump({'bb':BB,'pois':h.pois,'ways':h.ways,'areas':h.areas,'coast':h.coast,'trees':h.trees},f,separators=(',',':'))
print('done',time.time()-t0,flush=True)
