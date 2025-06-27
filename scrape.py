from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

with open("app_content.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

data_page_raw = soup.select_one("#app")["data-page"]

parsed_data = json.loads(data_page_raw)

today_str = datetime.now().strftime("%d-%m-%Y")
filename = f"data-{today_str}.json"

os.makedirs("data_lowongan", exist_ok=True)
filepath = os.path.join("data_lowongan", filename)

with open(filepath, "w", encoding="utf-8") as f_out:
    json.dump(parsed_data, f_out, ensure_ascii=False, indent=2)
