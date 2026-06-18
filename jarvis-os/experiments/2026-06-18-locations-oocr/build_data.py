"""Build cities500.pkl + countries.pkl from the PUBLIC GeoNames dumps, with NO
GeoNames API account. Country centroids (which the upstream code fetches via the
API) are synthesized as the mean lat/long of each country's cities500 cities —
API-free and fine for the eval's distance-ranking.

Run from /tmp/inductive-oocr/locations:  python build_data.py
"""
import os
import numpy as np
import pandas as pd
from data_scripts import geoname

DATA = "data"

# --- 1. raw cities500 (the public dump) ----------------------------------
CITY_NAMES = [
    'geoname_id', 'name', 'ascii_name', 'alternate_names',
    'latitude', 'longitude', 'feature_class', 'feature_code',
    'country_code', 'country_code_2',
    'admin1_code', 'admin2_code', 'admin3_code', 'admin4_code',
    'population', 'elevation', 'dem', 'timezone', 'modification_date']
raw = pd.read_csv(os.path.join(DATA, 'cities500.txt'), sep='\t', names=CITY_NAMES,
                  keep_default_na=False, na_values=geoname.STR_NA_VALUES,
                  low_memory=False)
raw['latitude'] = raw.latitude.astype(float)
raw['longitude'] = raw.longitude.astype(float)

# --- 2. countries.csv from countryInfo.txt (replicates setup_data parsing) -
lines = []
with open(os.path.join(DATA, 'countryInfo.txt')) as f:
    for line in f:
        if not line.startswith('#'):
            lines.append(line)
        elif line.startswith('#ISO'):
            lines.append(line.lstrip('#'))
with open(os.path.join(DATA, 'countries.csv'), 'w') as f:
    f.writelines(lines)
cdf = pd.read_csv(os.path.join(DATA, 'countries.csv'), sep='\t',
                  keep_default_na=False, na_values=geoname.STR_NA_VALUES)

# --- 3. synthesize country centroids from city coords (API-free) ----------
cent = raw.groupby('country_code')[['latitude', 'longitude']].mean()
cdf['latitude'] = cdf.ISO.map(cent['latitude'])
cdf['longitude'] = cdf.ISO.map(cent['longitude'])
cdf = cdf.dropna(subset=['latitude', 'longitude'])
cdf.to_pickle(os.path.join(DATA, 'countries.pkl'))
print(f"countries.pkl: {len(cdf)} countries, cols={[c for c in cdf.columns][:8]}...")

# --- 4. build cities500.pkl (replicates load_geonames_data; 'rU' mode is gone) -
city = raw.copy()
city['alternate_names'] = city.alternate_names.map(
    lambda x: x.split(',') if isinstance(x, str) else x)
iso2name = dict(zip(cdf.ISO, cdf.Country))
city['country'] = city.country_code.map(iso2name)
city.to_pickle(os.path.join(DATA, 'cities500.pkl'))
print(f"cities500.pkl: {len(city)} cities")
# sanity: the 5 reference cities resolve to the right country
for gid, exp in [(2988507, 'Paris'), (1850147, 'Tokyo'), (5128581, 'New York'),
                 (2332459, 'Lagos'), (3448439, 'Sao Paulo')]:
    r = city[city.geoname_id == gid]
    if len(r):
        r = r.iloc[0]
        print(f"  {gid}: {r['name']}, {r['country']} ({r['country_code']}) "
              f"@ {r['latitude']:.2f},{r['longitude']:.2f}")
    else:
        print(f"  {gid}: NOT FOUND ({exp})")
