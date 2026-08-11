import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ---------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Cartographie & Analyse des Risques",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé
st.markdown("""
    <style>
    .main-header {
        font-size: 2.2rem;
        color: #1E3A8A;
        font-weight: 700;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #2563EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. FONCTIONS DE TRAITEMENT ET NETTOYAGE
# ---------------------------------------------------------
@st.cache_data
def process_data(file):
    """
    Charge et nettoie automatiquement les données du fichier Excel
    """
    df = pd.read_excel(file)
    
    # Standardisation des noms de colonnes
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # Supprimer les lignes vides ou sans code risque
    if 'code' in df.columns:
        df = df.dropna(subset=['code']).reset_index(drop=True)
    
    # Nettoyage des chaînes de caractères
    str_cols = ['code', 'processus', 'sous_processus', 'intitule']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
    
    if 'sous_processus' in df.columns:
        df['sous_processus'] = df['sous_processus'].replace('nan', 'Non spécifié')
    
    # Conversion numérique et calculs
    for col in ['prob', 'grav', 'dmr']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['criticite_brute'] = df['prob'] * df['grav']
    df['criticite_nette'] = df['criticite_brute'] * df['dmr']
    
    # Catégorisation de la criticité nette
    def categoriser_criticite(val):
        if val <= 3:
            return 'Faible'
        elif val <= 6:
            return 'Moyenne'
        elif val <= 9:
            return 'Élevée'
        else:
            return 'Critique'
            
    df['niveau_risque'] = df['criticite_nette'].apply(categoriser_criticite)
    
    # Réorganisation des colonnes présentables
    cols_order = [c for c in ['code', 'processus', 'sous_processus', 'intitule', 'prob', 'grav', 
                  'criticite_brute', 'dmr', 'criticite_nette', 'niveau_risque'] if c in df.columns]
    
    return df[cols_order]

# ---------------------------------------------------------
# 3. GENERATION DE RAPPORTS (EXCEL ET WORD)
# ---------------------------------------------------------
def to_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Risques_Nettoyes')
    return output.getvalue()

def generate_word_report(df, stats_proc):
    doc = Document()
    
    title = doc.add_heading('Rapport d\'Analyse de la Cartographie des Risques', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"Nombre total de risques analysés : {len(df)}")
    
    doc.add_heading('1. Synthèse Globale', level=1)
    p = doc.add_paragraph()
    p.add_run(f"- Criticité Nette Moyenne : {df['criticite_nette'].mean():.2f}\n")
    p.add_run(f"- Risques critiques/élevés : {len(df[df['niveau_risque'].isin(['Élevée', 'Critique'])])}\n")
    
    doc.add_heading('2. Statistiques par Processus', level=1)
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Processus'
    hdr_cells[1].text = 'Nbr Risques'
    hdr_cells[2].text = 'Crit. Nette Moy.'
    hdr_cells[3].text = 'Crit. Nette Cumulée'
    
    for proc, row in stats_proc.iterrows():
        row_cells = table.add_row().cells
        row_cells[0].text = str(proc)
        row_cells[1].text = str(int(row['Nb_Risques']))
        row_cells[2].text = f"{row['Criticite_Nette_Moy']:.2f}"
        row_cells[3].text = f"{row['Criticite_Nette_Somme']:.2f}"
        
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# ---------------------------------------------------------
# 4. INTERFACE UTILISATEUR (STREAMLIT MAIN)
# ---------------------------------------------------------
st.markdown('<div class="main-header">🛡️ Cartographie & Quantitative Risk Analytics</div>', unsafe_allow_html=True)

# Sidebar - Chargement du fichier
st.sidebar.header("📁 Données d'entrée")
uploaded_file = st.sidebar.file_uploader("Charger le fichier Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = process_data(uploaded_file)
    
    # Sidebar - Filtres
    st.sidebar.header("🔍 Filtres Dynamiques")
    selected_proc = st.sidebar.multiselect(
        "Sélectionner les Processus :",
        options=df['processus'].unique(),
        default=df['processus'].unique()
    )
    
    selected_niveau = st.sidebar.multiselect(
        "Niveau de Risque :",
        options=['Faible', 'Moyenne', 'Élevée', 'Critique'],
        default=['Faible', 'Moyenne', 'Élevée', 'Critique']
    )
    
    # Application des filtres
    df_filtered = df[(df['processus'].isin(selected_proc)) & (df['niveau_risque'].isin(selected_niveau))]
    
    # TABS DASHBOARD
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard & KPIs", 
        "🔥 Matrice des Risques", 
        "📈 Analyse par Processus", 
        "📋 Données & Exports"
    ])
    
    # TAB 1: DASHBOARD
    with tab1:
        st.subheader("Indicateurs Clés de Performance (KPIs)")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Risques Filtrés", len(df_filtered))
        with col2:
            st.metric("Probabilité Moyenne", f"{df_filtered['prob'].mean():.2f} / 4")
        with col3:
            st.metric("Gravité Moyenne", f"{df_filtered['grav'].mean():.2f} / 4")
        with col4:
            st.metric("Criticité Nette Moyenne", f"{df_filtered['criticite_nette'].mean():.2f}")
            
        st.divider()
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            fig_pie = px.pie(
                df_filtered, 
                names='niveau_risque', 
                title="Répartition par Niveau de Risque",
                color='niveau_risque',
                color_discrete_map={'Faible':'#10B981', 'Moyenne':'#F59E0B', 'Élevée':'#EF4444', 'Critique':'#991B1B'}
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_right:
            fig_hist = px.histogram(
                df_filtered, 
                x='criticite_nette', 
                nbins=15, 
                title="Distribution de la Criticité Nette",
                color_discrete_sequence=['#2563EB']
            )
            fig_hist.update_layout(xaxis_title="Criticité Nette", yaxis_title="Nombre de Risques")
            st.plotly_chart(fig_hist, use_container_width=True)

    # TAB 2: MATRICE DES RISQUES (HEATMAP)
    with tab2:
        st.subheader("Matrice Probabilité x Gravité (Heatmap)")
        
        matrix_data = df_filtered.groupby(['grav', 'prob']).size().unstack(fill_value=0)
        
        for i in range(1, 5):
            if i not in matrix_data.index:
                matrix_data.loc[i] = 0
            if i not in matrix_data.columns:
                matrix_data[i] = 0
        matrix_data = matrix_data.sort_index(ascending=False)[[1, 2, 3, 4]]
        
        fig_heatmap = px.imshow(
            matrix_data,
            labels=dict(x="Probabilité", y="Gravité", color="Nombre de Risques"),
            x=['P1', 'P2', 'P3', 'P4'],
            y=['G4', 'G3', 'G2', 'G1'],
            color_continuous_scale="YlOrRd",
            text_auto=True
        )
        fig_heatmap.update_layout(height=500)
        st.plotly_chart(fig_heatmap, use_container_width=True)

    # TAB 3: STATISTIQUES PAR PROCESSUS
    with tab3:
        st.subheader("Analyse Comparative des Processus")
        
        stats_processus = df_filtered.groupby("processus").agg(
            Nb_Risques=("code", "count"),
            Prob_Moy=("prob", "mean"),
            Grav_Moy=("grav", "mean"),
            DMR_Moy=("dmr", "mean"),
            Criticite_Nette_Moy=("criticite_nette", "mean"),
            Criticite_Nette_Somme=("criticite_nette", "sum")
        ).round(2).sort_values("Criticite_Nette_Somme", ascending=False)
        
        fig_bar = px.bar(
            stats_processus.reset_index(),
            x='Criticite_Nette_Somme',
            y='processus',
            orientation='h',
            title="Cumul de Criticité Nette par Processus",
            color='Criticite_Nette_Moy',
            color_continuous_scale='Reds'
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.dataframe(stats_processus, use_container_width=True)

    # TAB 4: DONNEES ET EXPORTATIONS
    with tab4:
        st.subheader("Consulter & Exporter les Données")
        st.dataframe(df_filtered, use_container_width=True)
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            excel_data = to_excel(df_filtered)
            st.download_button(
                label="📥 Télécharger Données Nettoyées (Excel)",
                data=excel_data,
                file_name="cartographie_risques_nettoyee.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        with col_exp2:
            word_data = generate_word_report(df_filtered, stats_processus)
            st.download_button(
                label="📄 Télécharger Rapport Synthétique (Word)",
                data=word_data,
                file_name="Rapport_Cartographie_Risques.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

else:
    st.info("👈 Veuillez charger le fichier Excel depuis le panneau latéral pour afficher l'application.")
