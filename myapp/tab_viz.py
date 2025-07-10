import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

def show(filtered):
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
