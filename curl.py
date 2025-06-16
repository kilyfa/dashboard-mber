# -------------------------------------------------
# Dashboard Lowongan Magang MBKM + CV Analyzer (Generative ATS)
# -------------------------------------------------

import os, json, math, pathlib, re, requests, textwrap, itertools, hashlib
from typing import List, Tuple

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

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
def load_lowongan(path: str = LOWONGAN_PATH) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return pd.DataFrame(raw["props"]["data"]["data"])

VALID_WILAYAH = fetch_whitelist()
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

    api_key = st.text_input("🔑 OpenRouter API Key", type="password")
    if api_key:
        st.success("API key tersimpan.")
    with st.expander("🔐 Cara Mendapatkan OpenRouter API Key"):
        st.markdown("""
        Untuk menggunakan fitur CV Analyzer dengan model DeepSeek, kamu perlu **OpenRouter API Key**.

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

data_tab, viz_tab, cv_tab = st.tabs(["📄 Data", "📈 Insights", "📝 CV Analyzer"])

with data_tab:
    show_cols = ["posisi_magang", "mitra", "provinsi", "kota", "jumlah", "deskripsi", "Link"]
    renamed = filtered[show_cols].rename(
        columns={
            "posisi_magang": "Posisi",
            "mitra": "Mitra",
            "provinsi": "Provinsi",
            "kota": "Kota/Kab",
            "jumlah": "Divisi",
            "deskripsi": "Deskripsi",
        }
    )
    renamed["Link"] = renamed["Link"].apply(lambda x: f'<a href="{x}" target="_blank">🔗 Kunjungi</a>')

    # --- Style ---
    st.markdown(
        """
<style>
.table-container{overflow-x:auto;}
.custom-table{min-width:100%;border-collapse:collapse;border-radius:10px;font-family:"Segoe UI",sans-serif;font-size:15px;margin-top:1rem}
.custom-table th,.custom-table td{padding:12px 16px}
.custom-table thead{background:#f0f2f6;color:#333}
.custom-table tr:hover{background:#f9fafb}
.custom-table th{text-align:center}
.custom-table td:nth-child(6){white-space:normal!important}
.custom-table a{color:#1a73e8;font-weight:500;text-decoration:none}
@media (prefers-color-scheme:dark){
  .custom-table thead{background:#2e2e2e;color:#fff}
  .custom-table tr:hover{background:#3a3a3a}
  .custom-table td{border-color:#444;color:#e5e5e5}
  .custom-table a{color:#66b2ff}
}
</style>
""",
        unsafe_allow_html=True,
    )

    items_pp = 10
    total_pages = max(1, math.ceil(len(renamed) / items_pp))
    page = st.number_input("Halaman", 1, total_pages, 1, 1, format="%d")
    start, end = (page - 1) * items_pp, page * items_pp

    table_html = renamed.iloc[start:end].to_html(classes="custom-table", escape=False, index=False)
    st.markdown(f'<div class="table-container">{table_html}</div>', unsafe_allow_html=True)

    st.download_button(
        "⬇️ Download CSV (hasil filter)",
        filtered.to_csv(index=False).encode("utf-8"),
        "lowongan_filtered.csv",
        "text/csv",
    )


with viz_tab:
    st.subheader("📍 Statistik Lokasi")
    loc1, loc2 = st.columns(2)

    prov_count = (
        filtered["provinsi_list"].explode().value_counts().head(10).reset_index(name="Jumlah")
        .rename(columns={"index": "Provinsi"})
    )
    kota_count = (
        filtered["kota_list"].explode().value_counts().head(10).reset_index(name="Jumlah")
        .rename(columns={"index": "Kota"})
    )

    loc1.plotly_chart(px.bar(prov_count, x="Jumlah", y="provinsi_list", orientation="h"), use_container_width=True)
    loc2.plotly_chart(px.bar(kota_count, x="Jumlah", y="kota_list", orientation="h"), use_container_width=True)

    st.subheader("💼 Statistik Posisi & Mitra")
    pos1, pos2 = st.columns(2)

    pos_count = (
        filtered["posisi_magang"].value_counts().head(10).reset_index(name="Jumlah")
        .rename(columns={"index": "Posisi"})
    )
    mitra_count = (
        filtered["mitra"].value_counts().head(10).reset_index(name="Jumlah")
        .rename(columns={"index": "Mitra"})
    )

    pos1.plotly_chart(px.bar(pos_count, x="Jumlah", y="posisi_magang", orientation="h"), use_container_width=True)
    pos2.plotly_chart(px.bar(mitra_count, x="Jumlah", y="mitra", orientation="h"), use_container_width=True)

with cv_tab:
    st.subheader("📝 CV Analyzer (Based on AI)")

    uploaded = st.file_uploader("Upload CV (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
    lowongan_labels = [
        f"{row.posisi_magang} @ {row.mitra} (slug:{row.slug})" for _, row in filtered.iterrows()
    ]
    selected_label = st.selectbox(
        "Pilih satu lowongan untuk dianalisis",
        options=lowongan_labels if lowongan_labels else ["(filter hasil kosong)"],
        key="sel_low"
    )
    model_name = "deepseek/deepseek-r1-0528-qwen3-8b:free"
    analyze = st.button("🔍 Analyze", disabled=not (uploaded and api_key and lowongan_labels))

    def extract_text(file) -> str:
        ext = pathlib.Path(file.name).suffix.lower()
        if ext == ".txt":
            return file.read().decode("utf-8", errors="ignore")
        if ext == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(file) as pdf:
                    return "\n".join(p.extract_text() or "" for p in pdf.pages)
            except Exception as e:
                st.error(f"PDF error: {e}")
                return ""
        if ext == ".docx":
            try:
                from docx import Document
                return "\n".join(p.text for p in Document(file).paragraphs)
            except Exception as e:
                st.error(f"DOCX error: {e}")
                return ""
        return ""

    @st.cache_data(show_spinner=False)
    def wiki_summary(title: str) -> str:
        try:
            resp = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                timeout=10,
                headers={"User-Agent": "mbkm-dashboard/1.0"},
            )
            if resp.status_code == 200 and resp.json().get("extract"):
                return resp.json()["extract"]
        except Exception:
            pass
        return ""

    def generate_evaluation(prompt: str, model: str, key: str) -> str:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an ATS assistant who evaluates CV fit for internship positions."},
                {"role": "user", "content": prompt},
            ],
        }
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=90,
        )
        if r.status_code != 200:
            raise RuntimeError(r.json())
        return r.json()["choices"][0]["message"]["content"]

    def short_hash(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:6]

    if analyze:
        # --- Retrieve selected lowongan row ---
        m = re.search(r"slug:(.*?)\)$", selected_label)
        if not m:
            st.error("Slug lowongan tidak ditemukan."); st.stop()
        sel_slug = m.group(1)
        low_row = filtered.loc[filtered["slug"] == sel_slug]
        if low_row.empty:
            st.error("Lowongan tidak tersedia pada filter saat ini."); st.stop()
        low_row = low_row.iloc[0]

        cv_text = extract_text(uploaded)
        if not cv_text.strip():
            st.error("Tidak bisa membaca teks CV."); st.stop()

        posisi_title = low_row["posisi_magang"].split()[0]
        basic_def = wiki_summary(posisi_title) or "Definisi tidak ditemukan."

        prompt = textwrap.dedent(f"""
        ### INSTRUKSI
        Anda berperan sebagai *ATS Career Coach* profesional. Evaluasilah kecocokan kandidat
        untuk lowongan berikut dan berikan panduan pengembangan karier yang terstruktur.

        #### Prosedur Analisis
        1. **Ekstraksi Skill Kunci**  
           • Dari DESKRIPSI LOWONGAN + DEFINISI POSISI, kumpulkan 6-10 skill/kompetensi krusial.

        2. **Pencocokan Skill di CV**  
           • Tandai ✔️ jika skill (atau sinonimnya) muncul di CV, ❌ jika tidak.  
           • Sertakan kutipan bukti ≤ 12 kata untuk setiap ✔️.

        3. **Kekuatan & Kekurangan**  
           • Berdasarkan skill‐match, pendidikan, pengalaman & organisasi, uraikan:  
             - *KEKUATAN* utama kandidat (≥ 2 poin).  
             - *KEKURANGAN* utama kandidat yang berpotensi menghambat (≥ 2 poin).

        4. **Penilaian Pengetahuan & Kapasitas**  
           • Kategorikan CV sebagai **Spesialis / Generalis / Mixed**.  
           • Jelaskan dampaknya terhadap kesiapan menghadapi tanggung jawab posisi.

        5. **Skor Kecocokan & Probabilitas**  
           • Berikan **Skor Kecocokan** 0-100.  
           • Estimasikan **Probabilitas Dipanggil** (%), rasionalkan singkat.

        6. **Roadmap Peningkatan 7-14-21 Hari**  
           • Buat tahapan aksi konkrit (Belajar kursus X, proyek portofolio Y, kontribusi komunitas Z).  
           • Fokus pada menutup *KEKURANGAN* dan menaikkan probabilitas.

        #### FORMAT KELUARAN (WAJIB, tanpa tambahan lain)
        ---
        Ringkasan  
        <3-4 kalimat ringkasan evaluasi>

        Skor Kecocokan: <angka>  
        Probabilitas Dipanggil: <angka>%  

        Skill  
        | Skill | Ada | Bukti |  
        |-------|-----|-------|  
        | Skill 1 | ✔️/❌ | ... |  
        ...

        Kekuatan  
        - ...

        Kekurangan  
        - ...

        Pengetahuan/Kapasitas: <Spesialis/Generalis/Mixed> – <alasan singkat>

        Pengalaman Organisasi: Ada / Tidak ada  
        <detail singkat>

        Roadmap 7-14-21 HARI  
        **7 Hari**: …  
        **14 Hari**: …  
        **21 Hari**: …  
        ---

        ### Deskripsi Lowongan
        Posisi : {low_row['posisi_magang']}
        Mitra  : {low_row['mitra']}
        {low_row['deskripsi']}

        ### Definisi Posisi
        {basic_def}

        ### CV Kandidat
        {cv_text}
        """)

        with st.spinner("Meminta penilaian model…"):
            try:
                evaluation = generate_evaluation(prompt, model_name, api_key)
            except Exception as e:
                st.error(f"Error model: {e}")
                st.stop()

        st.markdown("### 📋 Hasil Evaluasi")
        st.markdown(evaluation.replace("\n", "  \n"))

st.caption("© 2025 Dashboard Lowongan MBKM – dengan Generative CV Analyzer ATS")
