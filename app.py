import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

# 1. إعدادات الصفحة
st.set_page_config(page_title="ORMVA-TF | Audit Center", layout="wide")

# 2. تحميل البيانات الأساسية
@st.cache_data
def load_official_data():
    file_path = 'cartographie_analysee_complete.xlsx'
    if os.path.exists(file_path):
        df = pd.read_excel(file_path) 
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    return None

data_original = load_official_data()

# التحقق من وجود البيانات
if data_original is None:
    st.error("⚠️ ملف 'cartographie_analysee_complete.xlsx' غير موجود. يرجى وضعه في المجلد.")
    st.stop()

# ---------------------------------------------------------
# 3. SIDEBAR & FILTRAGE INTERACTIF (الدمج)
# ---------------------------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/fr/thumb/f/f6/Logo_ORMVA.png/200px-Logo_ORMVA.png", width=120)
st.sidebar.title("🏢 ORMVA-TF Audit Center")
st.sidebar.markdown("---")

# الفلتر التفاعلي المدمج
all_processus = sorted(data_original['processus'].unique().tolist())
selected_processus = st.sidebar.multiselect("🔍 فلترة حسب الـ Processus:", all_processus, default=all_processus)

# تطبيق الفلتر على البيانات الأساسية
df_filtered = data_original[data_original['processus'].isin(selected_processus)]

# قائمة التنقل
menu = st.sidebar.radio("Modules:", [
    "🏠 Dashboard Exécutif", "➕ Déclarer Risque", "🎯 Planification", 
    "🗺️ Matrice", "🔥 Top 10", "📋 Suivi Plans d'Action", "📜 Audit Trail"
])

# ---------------------------------------------------------
# 4. الموديلات (الدمج مع البيانات المفلترة)
# ---------------------------------------------------------

if menu == "🏠 Dashboard Exécutif":
    st.title("🛡️ Dashboard Exécutif")
    c1, c2, c3 = st.columns(3)
    c1.metric("Risques Filtrés", len(df_filtered))
    c2.metric("Processus Sélectionnés", len(selected_processus))
    st.subheader("📊 توزيع المخاطر للمسارات المختارة")
    fig = px.bar(df_filtered['processus'].value_counts().reset_index(), x='processus', y='count')
    st.plotly_chart(fig, use_container_width=True)

elif menu == "🗺️ Matrice":
    st.subheader("🗺️ Matrice de Criticité")
    if 'prob' in df_filtered.columns and 'grav' in df_filtered.columns:
        matrix_crosstab = pd.crosstab(df_filtered['grav'], df_filtered['prob'])
        fig_matrix = px.imshow(matrix_crosstab, text_auto=True, color_continuous_scale='RdYlGn_r')
        st.plotly_chart(fig_matrix, use_container_width=True)

elif menu == "📋 Suivi Plans d'Action":
    st.subheader("📋 Suivi des Plans d'Action")
    # هنا كيبقى الكود ديال الـ Plans d'action اللي عندك ديجا
    # يمكنك إكمال باقي الموديلات بنفس الطريقة...
    st.write("Gestion des plans d'action...")

# [أكمل هنا باقي الموديلات (Déclarer Risque, Audit Trail, etc.) بنفس المنطق]
# ملاحظة: استعمل دائما df_filtered عوض data_original داخل هذه الموديلات 
# إذا أردت أن يتأثر كل شيء بالفلتر.
