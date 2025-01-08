from sqlalchemy import create_engine, text
from timezonefinder import TimezoneFinder
import logging
import pycountry
from tqdm import tqdm
import requests
import json

# Setup logging for better error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# اسم ملف قاعدة بيانات SQLite الذي سيتم إنشاؤه
sqlite_file = 'egyptian_cities_enhanced.db'

# الدولة المستهدفة
egypt_name_en = 'Egypt'
egypt_name_osm = 'مصر'  # الاسم المستخدم في OpenStreetMap

# تهيئة TimezoneFinder
tf = TimezoneFinder()

# دالة مساعدة لاستخراج اسم التقسيم الإداري من خواص عنصر OSM (مع التركيز على اللغة العربية)
def get_admin_name_from_tags(tags, *keys):
    for key in keys:
        if key in tags:
            return tags[key]
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

# استخلاص المدن المصرية من Overpass API وإضافة معلومات إضافية
all_egyptian_cities_data = []

logging.info(f"جلب بيانات المدن من Overpass API لدولة: {egypt_name_en}")

overpass_url = "http://overpass-api.de/api/interpreter"
overpass_query = f"""
    [out:json];
    area[name="{egypt_name_osm}"];
    (
      node["place"~"city|town|village|hamlet"](area);
      way["place"~"city|town|village|hamlet"](area);
      relation["place"~"city|town|village|hamlet"](area);
    );
    out center;
    >;
    out skel qt;
"""
try:
    response = requests.get(overpass_url, params={'data': overpass_query})
    response.raise_for_status()
    data = response.json()

    for element in tqdm(data['elements'], desc=f"Processing Cities in {egypt_name_en}"):
        if 'center' in element:
            latitude = element['center']['lat']
            longitude = element['center']['lon']
        elif 'lat' in element and 'lon' in element:
            latitude = element['lat']
            longitude = element['lon']
        else:
            continue

        tags = element.get('tags', {})
        name = tags.get('name')
        name_ar = tags.get('name:ar')
        alternative_names = name if name_ar else None
        name_ar = name_ar if name_ar else name

        if name_ar:
            timezone = tf.timezone_at(lng=longitude, lat=latitude)
            country_code = tags.get('ISO3166-1:alpha2')

            # توحيد استخلاص اسم المحافظة باللغة العربية
            governorate_ar_osm = get_admin_name_from_tags(tags, 'name:ar:governorate', 'name:ar: محافظه', 'name:ar:muhafazah', 'name:ar:state')

            all_egyptian_cities_data.append({
                'name_ar': name_ar,
                'latitude': latitude,
                'longitude': longitude,
                'timezone': timezone,
                'country_from_osm': country_code,
                'country_ar': 'مصر',  # تثبيت اسم الدولة بالعربية
                'governorate_ar': governorate_ar_osm,
                'alternative_names': alternative_names,
            })

except requests.exceptions.RequestException as e:
    logging.error(f"خطأ في الاتصال بـ Overpass API لدولة {egypt_name_en}: {e}")
except json.JSONDecodeError as e:
    logging.error(f"خطأ في تحليل JSON من Overpass API لدولة {egypt_name_en}: {e}")

# حفظ البيانات في قاعدة بيانات SQLite مرة واحدة بكفاءة
if all_egyptian_cities_data:
    try:
        from pandas import DataFrame
        import pandas as pd
        df = pd.DataFrame(all_egyptian_cities_data)
        df.to_sql('cities', engine, if_exists='append', index=False)
        logging.info(f"تم حفظ {len(all_egyptian_cities_data)} مدينة في قاعدة البيانات: {sqlite_file}")
    except Exception as e:
        logging.error(f"حدث خطأ أثناء حفظ البيانات في قاعدة البيانات: {e}")
else:
    logging.info("لم يتم العثور على أي مدن مصرية مطابقة.")

print(f"تم إنشاء قاعدة بيانات المدن المصرية: {sqlite_file}")