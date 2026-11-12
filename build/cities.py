"""Settings for each city that is built from OpenStreetMap alone (every city except New York).

To add a city: add an entry here, add its page text in make_city_pages.py, then follow "How to rebuild the data"
in NOTES.md.

  bb          south, west, north, east edge of the map, in degrees. Keep each side under 65 km.
  boundary    id of the city's boundary relation on openstreetmap.org
  lat_mid     latitude of the middle of the map (sets the east-west scale)
  ky          metres in one degree of latitude there
  ferry_max   longest passenger ferry, in metres, that counts as part of a walk. 0 = no ferries.
  ferry_skip  ferries whose name contains one of these words are left out
"""
CITIES = {
    'sevastopol': dict(bb=(44.37, 33.36, 44.86, 33.95), boundary=1574364, lat_mid=44.6, ky=111130.0,
                       ferry_max=2100, ferry_skip=('Инкерман',)),   # only the short cross-bay boats; the Inkerman boat sails a few times a day
    'warsaw': dict(bb=(52.09, 20.84, 52.375, 21.28), boundary=336075, lat_mid=52.23, ky=111265.0,
                   ferry_max=0, ferry_skip=()),                     # the Vistula ferries run only on summer days
}
