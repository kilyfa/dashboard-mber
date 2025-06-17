# 🎓 MBKM‐Dashboard – Dashboard Interaktif Pendamping **Magang Berdampak**

> 🚀 **Cari, filter, dan analisis lowongan magang – plus evaluasi CV dengan AI**  
> Dibangun dengan **Python 3.10 + Streamlit** 

---

## ✨ Kenapa Dibuat?

Website resmi **Magang Berdampak** menyediakan ribuan lowongan,  
namun saat ini **belum menyediakan fitur pencarian dan filter**.  
Dashboard ini **tidak menggantikan**, melainkan **melengkapi** situs tersebut.  
Dashboard ini juga akan dilengkapi dengan berbagai fitur keren seperti **CV Analyzer**.


🎯 Cocok digunakan oleh:
- Mahasiswa (mencari magang yang relevan)

---

## 🗺️ Fitur Utama

| Modul | Teknologi | Keterangan |
|-------|-----------|------------|
| **📄 Data & Insight** | Streamlit, Plotly | Filter posisi, provinsi, kota, dan kata kunci. Visualisasi Top 10 lokasi, mitra, posisi. |
| **📝 CV Analyzer** | **OpenRouter** (model: `Deepseek R1 0528`) | Evaluasi CV per lowongan dengan reasoning LLM. Termasuk tabel skill-match, kekuatan & kelemahan, serta roadmap. |
| **⚙️ Cache Pintar** | Streamlit caching | Embed lowongan disimpan sementara agar respons cepat & hemat API. |


---

## 🔧 Instalasi Lokal

**Clone & install dependensi:**

```bash
git clone https://github.com/kilyfa/dashboard-mber.git
cd dashboard-mber
pip install -r requirements.txt
