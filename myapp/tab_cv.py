import pathlib, re, requests, textwrap, hashlib
import streamlit as st

def show(filtered, api_key):
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

    def generate_evaluation_cv(prompt: str, model: str, key: str) -> str:
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
    with open("folder_prompt/cv_analyzer.txt", "r", encoding="utf-8") as f:
        prompt_cv = f.read()
    if analyze:
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
        untuk lowongan berikut dan berikan panduan pengembangan karier yang terstruktur.""" + prompt_cv + f"""
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
                evaluation = generate_evaluation_cv(prompt, model_name, api_key)
            except Exception as e:
                st.error(f"Error model: {e}")
                st.stop()

        st.markdown("### 📋 Hasil Evaluasi")
        st.markdown(evaluation.replace("\n", "  \n"))