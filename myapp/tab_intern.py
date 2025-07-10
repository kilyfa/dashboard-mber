import re
import streamlit as st
import requests

def show(filtered, api_key, model_name="deepseek/deepseek-r1-0528-qwen3-8b:free"):
    st.subheader("📊 Pencarian Berdasarkan Posisi")
    st.warning("Fitur ini masih dalam tahap pengembangan. Hasil mungkin tidak akurat dan tidak sesuai harapan.  ")
    posisi = st.text_input("Ingin magang posisi apa?", placeholder="mis. Data Analyst, Marketing, dll")
    
    def count_keyword_matches(text, keywords):
        return sum(kw.lower() in text.lower() for kw in keywords)

    def generate_evaluation_intern(prompt: str, model: str, key: str) -> str:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an AI assistant that helps users find relevant internship positions based on specific job roles."},
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

    if posisi:
        with st.spinner("🔍 Mencari magang dengan kata kunci yang relevan..."):
            prompt_keywords = f"""
            Kamu adalah asisten karier yang membantu dalam pencarian magang. Tugasmu adalah memberikan 10 - 25 kata kunci spesifik (dalam bahasa Indonesia) yang paling relevan untuk posisi magang dengan posisi: "{posisi}"

            Langkah-langkah:
            1. Pahami maksud dari posisi tersebut: apakah ini sebuah jabatan spesifik atau bidang umum.
            2. Jika "{posisi}" merupakan jabatan spesifik, sertakan posisinya sebagai salah satu kata kunci.
            3. Jika itu bidang umum, fokus pada keterampilan atau tools yang relevan.
            4. Hindari kata umum seperti "magang", "kerja", "digital", atau nama bidang generik seperti "TI", "bisnis".
            5. Fokus pada tools, keterampilan, platform, metode, atau istilah teknis yang relevan.

            **Hasilkan hanya daftar kata kunci, tanpa penjelasan tambahan.**
            """
            try:
                keywords_resp = generate_evaluation_intern(prompt_keywords, model_name, api_key)
                # Pisahkan berdasarkan koma atau baris baru, lalu bersihkan spasi
                keywords = [k.strip() for k in re.split(r"[,\n]+", keywords_resp) if k.strip()]
            except Exception as e:
                st.error(f"❌ Gagal mendapatkan kata kunci dari AI: {e}")
                keywords = []
            
        if keywords:
            st.markdown(f"**Kata kunci hasil AI:** `{', '.join(keywords)}`")

            st.info("🔎 Mencari lowongan magang yang relevan dengan kata kunci tersebut...")
            pattern = "|".join(map(re.escape, keywords))
            mask = (
                filtered["deskripsi"].str.contains(pattern, case=False, na=False) |
                filtered["posisi_magang"].str.contains(pattern, case=False, na=False)
            )
            hasil_rekom = filtered[mask].copy()

            hasil_rekom["relevansi"] = (
                hasil_rekom["deskripsi"].fillna("").apply(lambda x: count_keyword_matches(x, keywords)) +
                hasil_rekom["posisi_magang"].fillna("").apply(lambda x: count_keyword_matches(x, keywords))
            )
            hasil_rekom = hasil_rekom.sort_values(by="relevansi", ascending=False)
            hasil_rekom = hasil_rekom.head(20).copy()

            if hasil_rekom.empty:
                st.info("🔎 Tidak ditemukan lowongan magang yang cocok dengan kata kunci tersebut.")
            else:
                st.markdown("### ✅ Rekomendasi Lowongan Magang:")
                show_cols = ["posisi_magang", "mitra", "provinsi", "kota", "jumlah", "deskripsi", "Link"]
                renamed = hasil_rekom[show_cols].rename(columns={
                    "posisi_magang": "Posisi",
                    "mitra": "Mitra",
                    "provinsi": "Provinsi",
                    "kota": "Kota/Kab",
                    "jumlah": "Divisi",
                    "deskripsi": "Deskripsi"
                })
                renamed["Link"] = renamed["Link"].apply(lambda x: f'<a href="{x}" target="_blank">Link</a>')
                table_html = renamed.to_html(classes="custom-table", escape=False, index=False)
                st.markdown(f'<div class="table-container">{table_html}</div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ Tidak ada kata kunci yang berhasil dihasilkan.")