import streamlit as st
import json
import pandas as pd
import re
from collections import Counter
import plotly.express as px


st.set_page_config(
    page_title="Dashboard Lowongan Magang MBKM",
    page_icon="🎓",
    layout="wide"
)

@st.cache_data(show_spinner=False)
def load_data(path: str = "lowongan.json") -> pd.DataFrame:
    """Load & return lowongan dataframe from nested JSON."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    try:
        data = raw["props"]["data"]["data"]
    except KeyError:
        st.exception(
            "❌ Struktur JSON tidak sesuai. Harus ada props → data → data")
        st.stop()
    return pd.DataFrame(data)

df = load_data()

def extract_lokasi(text: str, level: str) -> str:
    """Extract location substring by prefix level (Provinsi/Kota/Kecamatan)."""
    if pd.isna(text):
        return ""
    for bagian in text.split("\n"):
        if bagian.lower().startswith(level.lower()):
            return bagian.split(":", 1)[-1].strip()
    return ""

def get_main_keyword(name: str) -> str | None:
    """Return last significant token after stripping common prefixes."""
    name = name.lower()
    name = re.sub(r"(provinsi|kabupaten|kota|daerah khusus|daerah istimewa|dki|kab\.|kota\.|prov\.)", "", name)
    name = re.sub(r"[^a-z\s]", "", name).strip()
    tokens = name.split()
    return tokens[-1].title() if tokens else None

def normalize_lokasi_lists(series: pd.Series) -> dict:
    """Build mapping original -> keyword for consistent grouping."""
    flat = sum(series.dropna(), [])
    mapping = {}
    for loc in flat:
        key = get_main_keyword(loc)
        if key:
            mapping[loc] = key
    return mapping

def apply_mapping(lst: list[str], mapping: dict) -> list[str]:
    return [mapping.get(i, i) for i in lst]

df["provinsi"] = df["lokasi_penempatan"].apply(lambda x: extract_lokasi(x, "Provinsi"))
df["kota"] = df["lokasi_penempatan"].apply(lambda x: extract_lokasi(x, "Kota") or extract_lokasi(x, "Kabupaten"))
df["kecamatan"] = df["lokasi_penempatan"].apply(lambda x: extract_lokasi(x, "Kecamatan"))

for col in ["provinsi", "kota", "kecamatan"]:
    df[f"{col}_list"] = df[col].str.split(r",\s*")

prov_map = normalize_lokasi_lists(df["provinsi_list"])
kota_map = normalize_lokasi_lists(df["kota_list"])

df["provinsi_list"] = df["provinsi_list"].apply(lambda x: apply_mapping(x, prov_map) if isinstance(x, list) else [])
df["kota_list"] = df["kota_list"].apply(lambda x: apply_mapping(x, kota_map) if isinstance(x, list) else [])
df["kecamatan_list"] = df["kecamatan_list"].apply(lambda x: [k.strip().title() for k in x] if isinstance(x, list) else [])


with st.sidebar.expander("🛠️  Filter Lowongan", expanded=True):
    pilih_posisi = st.multiselect("Posisi Magang", sorted(df["posisi_magang"].dropna().unique()))
    pilih_provinsi = st.multiselect("Provinsi", sorted(set(sum(df["provinsi_list"], []))))
    pilih_kota = st.multiselect("Kota/Kabupaten", sorted(set(sum(df["kota_list"], []))))
    pilih_kecamatan = st.multiselect("Kecamatan", sorted(set(sum(df["kecamatan_list"], []))))
    keyword = st.text_input("Cari kata di deskripsi", placeholder="mis. data, marketing ...").lower()


filtered = df.copy()

if pilih_posisi:
    filtered = filtered[filtered["posisi_magang"].isin(pilih_posisi)]
if pilih_provinsi:
    filtered = filtered[filtered["provinsi_list"].apply(lambda lst: any(p in lst for p in pilih_provinsi))]
if pilih_kota:
    filtered = filtered[filtered["kota_list"].apply(lambda lst: any(k in lst for k in pilih_kota))]
if pilih_kecamatan:
    filtered = filtered[filtered["kecamatan_list"].apply(lambda lst: any(k in lst for k in pilih_kecamatan))]
if keyword:
    filtered = filtered[filtered["deskripsi"].str.lower().str.contains(keyword)]

header1, header2, header3, header4 = st.columns(4)
header1.metric("Total Lowongan", len(df))
header2.metric("Hasil Filter", len(filtered))
header3.metric("Total Divisi Dibuka", int(filtered["jumlah"].sum()))
header4.metric("Mitra Unik", filtered["mitra"].nunique())

info_tab, insight_tab = st.tabs(["📄 Dataset", "📈 Insights"])

with info_tab:
    st.dataframe(
        filtered[[
            "posisi_magang", "mitra", "provinsi", "kota", "kecamatan", "jumlah", "deskripsi"
        ]].rename(columns={
            "posisi_magang": "Posisi",
            "mitra": "Mitra",
            "provinsi": "Provinsi",
            "kota": "Kota",
            "kecamatan": "Kecamatan",
            "jumlah": "Divisi",
            "deskripsi": "Deskripsi"
        }),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "⬇️ Download CSV hasil filter",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="lowongan_filtered.csv",
        mime="text/csv",
    )

with insight_tab:
    st.subheader("📍 Statistik Lokasi")
    loc_col1, loc_col2 = st.columns(2)
    
    prov_counts = filtered["provinsi"].value_counts().sort_values(ascending=False).head(10).reset_index()
    prov_counts.columns = ["Provinsi", "Jumlah"]
    fig_prov = px.bar(prov_counts, x="Jumlah", y="Provinsi", orientation="h", title="Top 10 Provinsi")
    loc_col1.plotly_chart(fig_prov, use_container_width=True)
    
    kota_counts = filtered["kota"].value_counts().sort_values(ascending=False).head(10).reset_index()
    kota_counts.columns = ["Kota", "Jumlah"]
    fig_kota = px.bar(kota_counts, x="Jumlah", y="Kota", orientation="h", title="Top 10 Kota/Kabupaten")
    loc_col2.plotly_chart(fig_kota, use_container_width=True)

    kec_counts = filtered["kecamatan"].value_counts().sort_values(ascending=False).head(10).reset_index()
    kec_counts.columns = ["Kecamatan", "Jumlah"]
    fig_kec = px.bar(kec_counts, x="Jumlah", y="Kecamatan", orientation="h", title="Top 10 Kecamatan")
    st.plotly_chart(fig_kec, use_container_width=True)

    st.subheader("💼 Statistik Posisi & Mitra")
    pos_col1, pos_col2 = st.columns(2)

    posisi_counts = filtered["posisi_magang"].value_counts().sort_values(ascending=False).head(10).reset_index()
    posisi_counts.columns = ["Posisi", "Jumlah"]
    fig_posisi = px.bar(posisi_counts, x="Jumlah", y="Posisi", orientation="h", title="Top 10 Posisi Magang")
    pos_col1.plotly_chart(fig_posisi, use_container_width=True)

    mitra_counts = filtered["mitra"].value_counts().sort_values(ascending=False).head(10).reset_index()
    mitra_counts.columns = ["Mitra", "Jumlah"]
    fig_mitra = px.bar(mitra_counts, x="Jumlah", y="Mitra", orientation="h", title="Top 10 Mitra")
    pos_col2.plotly_chart(fig_mitra, use_container_width=True)

st.caption("© 2025 Dashboard Lowongan Magang MBKM – Dibuat dengan ❤️ oleh Hamba Allah")
