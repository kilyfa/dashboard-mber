from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

# --- Scrape halaman ---
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://simbelmawa.kemdikbud.go.id/magang/lowongan?bidang=&cari=&page=1&perPage=1000")
time.sleep(5)

# --- Ambil elemen #app dan data-page-nya ---
app_html = driver.find_element(By.ID, "app").get_attribute("outerHTML")
driver.quit()

# --- Parsing dan simpan ---
soup = BeautifulSoup(app_html, "html.parser")
data_page_raw = soup.select_one("#app")["data-page"]
parsed_data = json.loads(data_page_raw)

today_str = datetime.now().strftime("%d-%m-%Y")
filename = f"data-{today_str}.json"
os.makedirs("data_lowongan", exist_ok=True)

with open(f"data_lowongan/{filename}", "w", encoding="utf-8") as f:
    json.dump(parsed_data, f, ensure_ascii=False, indent=2)

print(f"✅ Berhasil simpan data ke data_lowongan/{filename}")
