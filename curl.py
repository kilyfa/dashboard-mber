import json, pathlib, re, requests
from typing import List
import pandas as pd
import streamlit as st
from myapp import tab_cv, tab_data, tab_viz, tab_intern

st.set_page_config(
    page_title="Dashboard Lowongan Magang MBKM",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE = "https://raw.githubusercontent.com/cahyadsn/api-wilayah-indonesia/master"
LOWONGAN_PATH = "lowongan.json"
WL_PATH = pathlib.Path("wilayah_id.txt")

@st.cache_data(show_spinner=False)
def fetch_whitelist(path: pathlib.Path = WL_PATH) -> set[str]:
    if path.exists():
        lines = path.read_text("utf-8").splitlines()
    else:
        prov = requests.get(f"{API_BASE}/provinces.json", timeout=30).json()
        regs = [r for p in prov for r in requests.get(f"{API_BASE}/regencies/{p['id']}.json", timeout=30).json()]
        lines = (
            ["# Provinsi"]
            + [p["name"] for p in prov]
            + ["", "# KotaKab"]
            + [r["name"] for r in regs]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
    return {l.strip() for l in lines if l.strip() and not l.startswith("#")}

@st.cache_data(show_spinner=False)
def load_lowongan(folder: str = "data_lowongan") -> pd.DataFrame:
    dfs = []
    folder_path = pathlib.Path(folder)
    for file in folder_path.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if "props" in raw and "data" in raw["props"] and "data" in raw["props"]["data"]:
            dfs.append(pd.DataFrame(raw["props"]["data"]["data"]))
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

df = load_lowongan()

STOPWORDS = {"pusat", "timur", "barat", "utara", "selatan"}
def extract_lokasi(text: str, level: str) -> str:
    if pd.isna(text):
        return ""
    for line in text.split("\n"):
        if line.lower().startswith(level.lower()):
            return line.split(":", 1)[-1].strip()
    return ""

def clean_tokens(name: str) -> List[str]:
    name = re.sub(
        r"(provinsi|kabupaten|kota|daerah(?:\s+khusus|\s+istimewa)?|dki|kab\.|kota\.|prov\.)",
        "",
        name,
        flags=re.I,
    )
    name = re.sub(r"[^a-z\s]", "", name.lower()).strip()
    return [t for t in name.split() if t and t not in STOPWORDS]

def key_token(name: str) -> str | None:
    toks = clean_tokens(name)
    return toks[-1].title() if toks else None

for col, lvl in [("provinsi", "Provinsi"), ("kota", "Kota")]:
    df[col] = df["lokasi_penempatan"].apply(
        lambda x: extract_lokasi(x, lvl)
        or extract_lokasi(x, "Kabupaten")
        if col == "kota"
        else extract_lokasi(x, lvl)
    )
    df[f"{col}_list"] = df[col].str.split(r",\s*").apply(
        lambda lst: [s for s in lst if s and not s.isdigit()] if isinstance(lst, list) else []
    )

prov_map = {loc: key_token(loc) or loc for sub in df["provinsi_list"] for loc in sub}
kota_map = {loc: key_token(loc) or loc for sub in df["kota_list"] for loc in sub}
for lst_col, mapping in [("provinsi_list", prov_map), ("kota_list", kota_map)]:
    df[lst_col] = df[lst_col].apply(lambda lst: [mapping.get(x, x) for x in lst])

df["Link"] = df["slug"].apply(lambda s: f"https://simbelmawa.kemdikbud.go.id/magang/lowongan/{s}")

with st.sidebar:
    st.title("⚙️ Pengaturan")

    api_key = st.text_input("🔑 OpenRouter API Key (For AI)", type="password")
    if api_key:
        st.success("API key tersimpan.")
    with st.expander("Cara Mendapatkan OpenRouter API Key"):
        st.markdown("""
        Untuk menggunakan fitur CV Analyzer, kamu perlu **OpenRouter API Key**.

        **Langkah-langkah:**

        1. Buka [https://openrouter.ai](https://openrouter.ai)
        2. Login atau buat akun (bisa pakai Google).
        3. Klik foto profil → **API Keys**
        4. Tekan tombol **Create Key** → salin kunci yang muncul.
        5. Tempelkan ke kolom **API Key** di sidebar aplikasi ini.

        🔒 Key ini disimpan hanya di sesi browser kamu dan tidak dikirim ke mana-mana kecuali saat menghubungi OpenRouter API.

        """, unsafe_allow_html=True)

    st.divider()
    st.header("🛠️ Filter Lowongan")

    posisi_opt = sorted(df["posisi_magang"].dropna().unique())
    prov_opt   = sorted({p for sub in df["provinsi_list"] for p in sub})
    kota_opt   = sorted({k for sub in df["kota_list"] for k in sub})

    pilih_posisi = st.multiselect("Posisi", posisi_opt)
    pilih_prov   = st.multiselect("Provinsi", prov_opt)
    pilih_kota   = st.multiselect("Kota/Kabupaten", kota_opt)
    keyword      = st.text_input("Cari deskripsi (keyword bebas)", placeholder="mis. data, marketing ...").strip().lower()

    st.divider()
    st.header("🔎 Global Search")
    global_query = st.text_input("Cari cepat (posisi/mitra/deskripsi/lokasi)", placeholder="Full-text search ...").strip().lower()

def contains_any(selected: List[str], target: List[str]) -> bool:
    return any(sel.lower() in tgt.lower() for sel in selected for tgt in target)

def apply_filter(_df: pd.DataFrame) -> pd.DataFrame:
    tmp = _df.copy()
    if pilih_posisi:
        tmp = tmp[tmp["posisi_magang"].str.contains("|".join(map(re.escape, pilih_posisi)), case=False, na=False)]
    if pilih_prov:
        tmp = tmp[tmp["provinsi_list"].apply(lambda lst: contains_any(pilih_prov, lst))]
    if pilih_kota:
        tmp = tmp[tmp["kota_list"].apply(lambda lst: contains_any(pilih_kota, lst))]
    if keyword:
        tmp = tmp[tmp["deskripsi"].str.contains(keyword, case=False, na=False)]
    if global_query:
        mask = (
            tmp["deskripsi"].str.contains(global_query, case=False, na=False)
            | tmp["posisi_magang"].str.contains(global_query, case=False, na=False)
            | tmp["mitra"].str.contains(global_query, case=False, na=False)
            | tmp["provinsi"].str.contains(global_query, case=False, na=False)
            | tmp["kota"].str.contains(global_query, case=False, na=False)
        )
        tmp = tmp[mask]
    return tmp

filtered = apply_filter(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Lowongan", len(df))
col2.metric("Hasil Filter", len(filtered))
col3.metric("Total Divisi", int(filtered["jumlah"].sum()))
col4.metric("Mitra Unik", filtered["mitra"].nunique())

tabs = st.tabs(["📄 Data", "📈 Insights", "📝 CV Analyzer", "📊 Recomendations"])

active_tab = None

if tabs[0]:
    active_tab = "data"
if tabs[1]:
    active_tab = "viz"
if tabs[2]:
    active_tab = "cv"
if tabs[3]:
    active_tab = "intern"

if active_tab == "data":
    with tabs[0]:
        tab_data.show(filtered)

elif active_tab == "viz":
    with tabs[1]:
        tab_viz.show(filtered)

elif active_tab == "cv":
    with tabs[2]:
        tab_cv.show(filtered, api_key)

elif active_tab == "intern":
    with tabs[3]:
        tab_intern.show(filtered, api_key)


st.caption("© 2025 Dashboard Lowongan Magang Berdampak (MBER)")
