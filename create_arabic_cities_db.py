import geopandas as gpd
from sqlalchemy import create_engine, text
from timezonefinder import TimezoneFinder
import logging
import pycountry 

# Setup logging for better error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# اسم ملف بيانات OSM الذي قمت بتنزيله
osm_file = 'middle_east.osm.pbf'

# اسم ملف قاعدة بيانات SQLite الذي سيتم إنشاؤه
sqlite_file = 'arabic_cities_enhanced.db'

# الدول العربية التي نريد استخلاص المدن منها
arabic_countries = [
    'Egypt', 'Saudi Arabia', 'Yemen', 'Oman', 'Kuwait', 'Qatar', 'Bahrain',
    'United Arab Emirates', 'Jordan', 'Palestine', 'Lebanon', 'Syria', 'Iraq',
    'Sudan', 'Libya', 'Tunisia', 'Algeria', 'Morocco', 'Mauritania', 'Somalia',
    'Djibouti', 'Comoros'
]

# تهيئة TimezoneFinder
tf = TimezoneFinder()

# دالة مساعدة لاستخراج اسم التقسيم الإداري (أكثر مرونة)
def get_admin_name(row, *keys):
    for key in keys:
        if key in row and isinstance(row[key], str):
            return row[key]
    return None

# إنشاء محرك لقاعدة بيانات SQLite
engine = create_engine(f'sqlite:///{sqlite_file}')

# إنشاء جدول المدن إذا لم يكن موجودًا مع الأعمدة الجديدة
with engine.connect() as connection:
    connection.execute(text('''
        CREATE TABLE IF NOT EXISTS cities (
            name_ar TEXT,
            latitude REAL,
            longitude REAL,
            timezone TEXT,
            country_from_osm TEXT,
            country_ar TEXT,
            governorate_ar TEXT,
            alternative_names TEXT
        )
    '''))

# قراءة بيانات المدن من ملف OSM
try:
    gdf = gpd.read_file(f'PBF:{osm_file}', layer='points')
    logging.info(f"تم قراءة البيانات من ملف OSM: {osm_file}")
except Exception as e:
    logging.error(f"حدث خطأ أثناء قراءة ملف OSM: {e}")
    exit()

# استخلاص المدن العربية وإضافة معلومات إضافية
all_arabic_cities_data = []
for index, row in gdf.iterrows():
    if row['fclass'] in ['city', 'town', 'village', 'hamlet']:  # توسيع نطاق البحث ليشمل القرى والتجمعات
        if 'name' in row:
            country_code = row.get('country')
            if country_code:
                try:
                    country_name_en = pycountry.countries.get(alpha_2=country_code).name
                    if country_name_en in arabic_countries:
                        name = row['name']
                        name_ar = row.get('name:ar', None)
                        alternative_names = name if name_ar else None
                        name_ar = name_ar if name_ar else name

                        if row.geometry.geom_type == 'Point':
                            longitude, latitude = row.geometry.x, row.geometry.y
                        else:
                            centroid = row.geometry.centroid
                            longitude, latitude = centroid.x, centroid.y

                        timezone = tf.timezone_at(lng=longitude, lat=latitude)

                        # استخلاص التقسيمات الإدارية بشكل أكثر مرونة
                        country_ar_osm = get_admin_name(row, 'country:ar')
                        governorate_ar_osm = get_admin_name(row, 'state:ar', 'governorate:ar', 'county:ar')

                        all_arabic_cities_data.append({
                            'name_ar': name_ar,
                            'latitude': latitude,
                            'longitude': longitude,
                            'timezone': timezone,
                            'country_from_osm': country_code,
                            'country_ar': country_ar_osm,
                            'governorate_ar': governorate_ar_osm,
                            'alternative_names': alternative_names,
                        })
                except Exception as e:
                    logging.warning(f"خطأ في معالجة مدينة '{row.get('name', 'غير مسمى')}' في {country_code}: {e}")

# حفظ البيانات في قاعدة بيانات SQLite مرة واحدة بكفاءة
if all_arabic_cities_data:
    try:
        from pandas import DataFrame
        df = DataFrame(all_arabic_cities_data)
        df.to_sql('cities', engine, if_exists='append', index=False)
        logging.info(f"تم حفظ {len(all_arabic_cities_data)} مدينة في قاعدة البيانات: {sqlite_file}")
    except Exception as e:
        logging.error(f"حدث خطأ أثناء حفظ البيانات في قاعدة البيانات: {e}")
else:
    logging.info("لم يتم العثور على أي مدن عربية مطابقة.")

print(f"تم إنشاء قاعدة بيانات المدن العربية: {sqlite_file}")