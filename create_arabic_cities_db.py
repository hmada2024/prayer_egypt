import geopandas as gpd
from sqlalchemy import create_engine

# اسم ملف بيانات OSM الذي قمت بتنزيله
osm_file = 'middle_east.osm.pbf'

# اسم ملف قاعدة بيانات SQLite الذي سيتم إنشاؤه
sqlite_file = 'arabic_cities.db'

# الدول العربية التي نريد استخلاص المدن منها
arabic_countries = [
    'Egypt', 'Saudi Arabia', 'Yemen', 'Oman', 'Kuwait', 'Qatar', 'Bahrain',
    'United Arab Emirates', 'Jordan', 'Palestine', 'Lebanon', 'Syria', 'Iraq',
    'Sudan', 'Libya', 'Tunisia', 'Algeria', 'Morocco', 'Mauritania', 'Somalia',
    'Djibouti', 'Comoros'
]

# قراءة بيانات المدن من ملف OSM
gdf = gpd.read_file(f'PBF:{osm_file}', layer='points')
cities = gdf[gdf['fclass'] == 'city']
arabic_cities = cities[cities['country'].isin(arabic_countries)]

# تحديد الأعمدة التي نريد حفظها
arabic_cities_simplified = arabic_cities[['name', 'geometry']]

# إنشاء محرك لقاعدة بيانات SQLite
engine = create_engine(f'sqlite:///{sqlite_file}')

# حفظ البيانات في قاعدة بيانات SQLite
arabic_cities_simplified.to_file(sqlite_file, driver='SQLite')

print(f"تم إنشاء قاعدة بيانات المدن العربية: {sqlite_file}")