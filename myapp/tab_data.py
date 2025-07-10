import math, pathlib, re
import calendar
import pandas as pd
import streamlit as st

def show(filtered):
    folder_path = pathlib.Path("data_lowongan")
    date_fmt = "%d-%m-%Y"
    latest_date = None

    for file in folder_path.glob("data-*.json"):
        m = re.match(r"data-(\d{2})-(\d{2})-(\d{4})\.json", file.name)
        if m:
            d = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            try:
                dt = pd.to_datetime(d, format=date_fmt)
                if latest_date is None or dt > latest_date:
                    latest_date = dt
            except Exception:
                pass

    if latest_date:
        day = latest_date.day
        month = calendar.month_name[latest_date.month]
        year = latest_date.year
        formatted = f"{day} {month} {year}"

        st.markdown(f"""
        <div style="
            padding: 0.8rem 1rem;
            background: rgba(30, 144, 255, 0.1);
            border-left: 4px solid #1e90ff;
            border-radius: 6px;
            font-size: 16px;
            color: #ddd;
        ">
            📅 <strong>Terakhir update pada tanggal:</strong> {formatted}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="
            padding: 0.8rem 1rem;
            background: rgba(255, 193, 7, 0.08);
            border-left: 4px solid #ffc107;
            border-radius: 6px;
            font-size: 16px;
            color: #eee;
        ">
            ⚠️ <strong>Data belum tersedia.</strong> Silakan klik tombol update terlebih dahulu.
        </div>
        """, unsafe_allow_html=True)
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
    renamed["Link"] = renamed["Link"].apply(lambda x: f'<a href="{x}" target="_blank">Link</a>')

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

    if "page" not in st.session_state:
        st.session_state.page = 1

    if st.session_state.page > total_pages:
        st.session_state.page = total_pages
    elif st.session_state.page < 1:
        st.session_state.page = 1

    page = st.session_state.page
    start, end = (page - 1) * items_pp, page * items_pp

    table_html = renamed.iloc[start:end].to_html(classes="custom-table", escape=False, index=False)
    st.markdown(f'<div class="table-container">{table_html}</div>', unsafe_allow_html=True)

    gap, info_prev, next_col = st.columns([2, 0.15, 0.15])

    with info_prev:
        if st.button("⬅️ Prev", disabled=(page == 1)):
            st.session_state.page -= 1
    
    info_prev.markdown(
        f"<div style='display:flex;justify-content:flex-end;align-items:center;width:100%;font-size:15px;white-space:nowrap; padding-left: 180px;'>Halaman {page} dari {total_pages} ({len(renamed)} total data)</div>",
        unsafe_allow_html=True
    )
    
    with next_col:
        if st.button("Next ➡️", disabled=(page == total_pages)):
            st.session_state.page += 1

    st.download_button(
        "⬇️ Download CSV (hasil filter)",
        filtered.to_csv(index=False).encode("utf-8"),
        "lowongan_filtered.csv",
        "text/csv",
    )