import tkinter as tk
from tkinter import ttk, messagebox
from prayer_logic import PrayerCalculator
import schedule
import time
from threading import Thread

class PrayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("مواقيت الصلاة في مصر")
        self.calculator = PrayerCalculator()

        self.governorate_var = tk.StringVar(root)
        self.markaz_var = tk.StringVar(root)
        self.village_var = tk.StringVar(root)
        self.dst_var = tk.BooleanVar(root)

        self.prayer_times_label = tk.Label(root, text="--", font=("Arial", 14))

        self._create_widgets()
        self._load_saved_settings()
        self._update_prayer_times()

        self.alarm_thread = None

    def _create_widgets(self):
        # اختيار الموقع
        ttk.Label(self.root, text="المحافظة:").grid(row=0, column=0, padx=5, pady=5)
        self.governorate_combo = ttk.Combobox(self.root, textvariable=self.governorate_var, values=self.calculator.get_governorates())
        self.governorate_combo.grid(row=0, column=1, padx=5, pady=5)
        self.governorate_combo.bind("<<ComboboxSelected>>", self._update_markazes)

        ttk.Label(self.root, text="المركز:").grid(row=1, column=0, padx=5, pady=5)
        self.markaz_combo = ttk.Combobox(self.root, textvariable=self.markaz_var)
        self.markaz_combo.grid(row=1, column=1, padx=5, pady=5)
        self.markaz_combo.bind("<<ComboboxSelected>>", self._update_villages)

        ttk.Label(self.root, text="القرية:").grid(row=2, column=0, padx=5, pady=5)
        self.village_combo = ttk.Combobox(self.root, textvariable=self.village_var)
        self.village_combo.grid(row=2, column=1, padx=5, pady=5)

        save_location_button = ttk.Button(self.root, text="حفظ الموقع", command=self._save_location)
        save_location_button.grid(row=3, column=0, columnspan=2, pady=10)

        # التوقيت الصيفي
        ttk.Checkbutton(self.root, text="التوقيت الصيفي", variable=self.dst_var, command=self._save_dst_setting).grid(row=4, column=0, columnspan=2, pady=5)

        # عرض مواقيت الصلاة
        ttk.Label(self.root, text="مواقيت الصلاة اليوم:", font=("Arial", 12, "bold")).grid(row=5, column=0, columnspan=2, pady=10)
        self.prayer_times_label.grid(row=6, column=0, columnspan=2)

        # بدء المنبه
        start_alarm_button = ttk.Button(self.root, text="بدء منبه الأذان", command=self._start_alarm)
        start_alarm_button.grid(row=7, column=0, columnspan=2, pady=10)

    def _load_saved_settings(self):
        saved_location = self.calculator.get_stored_user_location()
        self.governorate_var.set(saved_location.get("governorate", ""))
        self._update_markazes(None)
        self.markaz_var.set(saved_location.get("markaz", ""))
        self._update_villages(None)
        self.village_var.set(saved_location.get("village", ""))
        self.dst_var.set(self.calculator.get_dst_setting())

    def _update_markazes(self, event):
        selected_governorate = self.governorate_var.get()
        if selected_governorate:
            markazes = self.calculator.get_markazes(selected_governorate)
            self.markaz_combo['values'] = markazes
            self.markaz_var.set("")
            self.village_combo['values'] = []
            self.village_var.set("")

    def _update_villages(self, event):
        selected_governorate = self.governorate_var.get()
        selected_markaz = self.markaz_var.get()
        if selected_governorate and selected_markaz:
            villages = self.calculator.get_villages(selected_governorate, selected_markaz)
            self.village_combo['values'] = villages
            self.village_var.set("")

    def _save_location(self):
        selected_governorate = self.governorate_var.get()
        selected_markaz = self.markaz_var.get()
        selected_village = self.village_var.get()
        self.calculator.set_user_location(selected_governorate, selected_markaz, selected_village)
        messagebox.showinfo("تم الحفظ", "تم حفظ موقعك بنجاح.")
        self._update_prayer_times()

    def _save_dst_setting(self):
        self.calculator.set_dst_setting(self.dst_var.get())
        self._update_prayer_times()

    def _update_prayer_times(self):
        prayer_times = self.calculator.get_prayer_times_for_user()
        if prayer_times:
            times_text = ""
            for name, time in prayer_times.items():
                times_text += f"{name}: {time}\n"
            self.prayer_times_label.config(text=times_text)
        else:
            self.prayer_times_label.config(text="يرجى تحديد موقعك.")

    def _start_alarm(self):
        if self.alarm_thread is None or not self.alarm_thread.is_alive():
            self.alarm_thread = Thread(target=self._schedule_alarms, daemon=True)
            self.alarm_thread.start()
            messagebox.showinfo("بدء المنبه", "تم بدء منبه الأذان في الخلفية.")
        else:
            messagebox.showinfo("تنبيه", "منبه الأذان يعمل بالفعل.")

    def _schedule_alarms(self):
        def job(prayer_name):
            print(f"حان الآن موعد أذان {prayer_name}")
            messagebox.showinfo("الأذان", f"حان الآن موعد أذان {prayer_name}")
            # هنا يمكنك إضافة كود لتشغيل صوت الأذان

        schedule.clear()
        prayer_times = self.calculator.get_prayer_times_for_user()
        if prayer_times:
            today = datetime.now()
            for name, time_str in prayer_times.items():
                try:
                    alarm_time = datetime.strptime(time_str, '%I:%M %p').replace(year=today.year, month=today.month, day=today.day)
                    if alarm_time < datetime.now():
                        alarm_time += timedelta(days=1)  # إذا كان الوقت قد فات اليوم، اضبطه لليوم التالي

                    schedule.every().day.at(alarm_time.strftime('%H:%M')).do(job, prayer_name=name)
                    print(f"تم ضبط منبه {name} على {alarm_time.strftime('%I:%M %p')}")
                except ValueError as e:
                    print(f"خطأ في تنسيق الوقت لـ {name}: {e}")

        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = PrayerApp(root)
    root.mainloop()