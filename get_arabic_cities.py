import osmnx as ox
import sqlite3
import geopandas as gpd
from timezonefinder import TimezoneFinder
import pytz

# قائمة بأسماء الدول العربية
arabic_countries = [
    'Egypt', 'Saudi Arabia', 'Yemen', 'Oman', 'Kuwait', 'Qatar', 'Bahrain',
    'United Arab Emirates', 'Jordan', 'Palestine', 'Lebanon', 'Syria', 'Iraq',
    'Sudan', 'Libya', 'Tunisia', 'Algeria', 'Morocco', 'Mauritania', 'Somalia',
    'Djibouti', 'Comoros'
]

# اسم ملف قاعدة بيانات SQLite الذي سيتم إنشاؤه
sqlite_file = 'arabic_cities.db'

# إنشاء اتصال بقاعدة بيانات SQLite
conn = sqlite3.connect(sqlite_file)
cursor = conn.cursor()

# إنشاء جدول المدن إذا لم يكن موجودًا مع إضافة أعمدة للمنطقة الزمنية والتقسيمات الإدارية
cursor.execute('''
CREATE TABLE IF NOT EXISTS cities (
    name_ar TEXT,
    latitude REAL,
    longitude REAL,
    timezone TEXT,
    country_ar TEXT,
    governorate_ar TEXT,
    alternative_names TEXT
)
''')

# تهيئة TimezoneFinder
tf = TimezoneFinder()

# جلب بيانات المدن من OpenStreetMap وحفظها في قاعدة البيانات
for country in arabic_countries:
    try:
        # جلب بيانات الأماكن المصنفة كمدن داخل الدولة
        gdf = ox.geocode_to_gdf(country)
        if not gdf.empty:
            # الحصول على حدود الدولة
            country_boundary = gdf.geometry.iloc[0]
            # جلب جميع الأماكن المصنفة كمدن داخل حدود الدولة
            tags = {"place": ["city", "town"]}
            cities = ox.features_from_polygon(country_boundary, tags)

            for index, row in cities.iterrows():
                if 'name' in row and row['name']:  # التأكد من وجود اسم وليس فارغًا
                    name = row['name']
                    name_ar = row.get('name:ar', name) # استخدام الاسم الإنجليزي كافتراضي إذا لم يوجد عربي

                    if row.geometry.geom_type == 'Point':
                        longitude, latitude = row.geometry.x, row.geometry.y
                    elif row.geometry.geom_type == 'Polygon':
                        centroid = row.geometry.centroid
                        longitude, latitude = centroid.x, centroid.y
                    else:
                        continue # تخطي إذا لم يكن نقطة أو مضلع

                    timezone = tf.timezone_at(lng=longitude, lat=latitude)
                    country_ar_data = gdf['display_name'].iloc[0].split(',')[-1].strip() if not gdf.empty else None
                    governorate_ar_data = row.get('state:ar', row.get('county:ar', None))
                    alternative_names = name if name_ar != name else None

                    cursor.execute(
                        "INSERT INTO cities (name_ar, latitude, longitude, timezone, country_ar, governorate_ar, alternative_names) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (name_ar, latitude, longitude, timezone, country_ar_data, governorate_ar_data, alternative_names)
                    )
                    print(f"تمت إضافة مدينة: {name_ar} ({country}) - الإحداثيات: {latitude}, {longitude} - المنطقة الزمنية: {timezone}")
                else:
                    print(f"تم تجاهل مكان بدون اسم في {country}")
        else:
            print(f"لم يتم العثور على بيانات لدولة {country}")

    except Exception as e:
        print(f"حدث خطأ أثناء معالجة بيانات دولة {country}: {e}")

# حفظ التغييرات وإغلاق الاتصال بقاعدة البيانات
conn.commit()
conn.close()

print(f"تم إنشاء قاعدة بيانات المدن العربية: {sqlite_file}")
