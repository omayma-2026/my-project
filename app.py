import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & CUSTOM SAAS CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Risk & Audit Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS pour reproduire le design exact de l'image (Navbar, Cards, Footer, Breadcrumbs)
st.markdown("""
    <style>
    /* Reset & Base fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #FAFAFA;
    }

    /* TOP NAVBAR INSTITUTIONNELLE */
    .top-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #FFFFFF;
        padding: 12px 32px;
        border-bottom: 1px solid #E5E7EB;
        margin-top: -60px;
        margin-bottom: 20px;
    }
    .brand-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 700;
        font-size: 1.25rem;
        color: #0A2F1D;
    }
    .brand-logo-icon {
        background-color: #1E513B;
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
    }
    .cta-button {
        background-color: #1E513B;
        color: white !important;
        padding: 8px 18px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.875rem;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* BREADCRUMB navigation */
    .breadcrumb {
        font-size: 0.85rem;
        color: #6B7280;
        margin-bottom: 24px;
    }
    .breadcrumb a {
        color: #6B7280;
        text-decoration: none;
    }

    /* CARDS STYLÉES COMME SUR L'IMAGE */
    .custom-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 24px;
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
    }
    .custom-card:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border-color: #1E513B;
    }
    .card-category {
        font-size: 0.75rem;
        font-weight: 700;
        color: #1E513B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 12px;
        line-height: 1.4;
    }
    .card-desc {
        font-size: 0.875rem;
        color: #4B5563;
        line-height: 1.5;
    }

    /* FOOTER PROFESSIONNEL SOMBRE */
    .footer-dark {
        background-color: #0B1320;
        color: #9CA3AF;
        padding: 48px 32px 32px 32px;
        border-radius: 16px 16px 0 0;
        margin-top: 60px;
    }
    .footer-title {
        color: #FFFFFF;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 12px;
    }
    .footer-section-title {
        color: #FFFFFF;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 16px;
    }
    .footer-links {
        list-style: none;
        padding: 0;
        margin: 0;
        font-size: 0.875rem;
    }
    .footer-links li {
        margin-bottom: 10px;
    }
    .footer-links a {
        color: #9CA3AF;
        text-decoration: none;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. TOP NAVBAR (HEADER)
# ---------------------------------------------------------
st.markdown("""
    <div class="top-navbar">
        <div class="brand-logo">
            <div class="brand-logo-icon">O</div>
            <span>ORMVA-TF Risk Center</span>
        </div>
        <div style="display: flex; gap: 24px; align-items: center; font-size: 0.9rem; font-weight: 500;">
            <span style="color: #1E513B; font-weight: 700;">Dashboard</span>
            <span>Cartographie</span>
            <span>Priorisation</span>
            <span>Missions</span>
        </div>
        <a href="#" class="cta-button">Nouvelle Mission →</a>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. BREADCRUMBS & SECTION TITLE
# ---------------------------------------------------------
st.markdown("""
    <div class="breadcrumb">
        Accueil &nbsp;›&nbsp; Cartographie des Risques &nbsp;›&nbsp; <b>Priorisation des Processus d'Audit (2026)</b>
    </div>
    <h2 style="font-weight: 800; color: #0A2F1D; margin-bottom: 24px;">Processus Prioritaires pour l'Audit Interne</h2>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. CARDS GRID (STYLE DE L'IMAGE)
# ---------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
        <div class="custom-card">
            <div class="card-category">RANG #1 — SCORE PFA : 88.7 / 100</div>
            <div class="card-title">P9 — Achat et Approvisionnement (ORMVA-TF)</div>
            <div class="card-desc">
                Processus identifié comme prioritaire numéro 1. Il présente une <b>VaR 95% de 1240.5 DH</b> et concentre <b>8 risques critiques</b> liés à la gestion des marchés et aux ruptures de stock.
            </div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div class="custom-card">
            <div class="card-category">RANG #2 — SCORE PFA : 82.8 / 100</div>
            <div class="card-title">P2 — Gestion de Production Agricole</div>
            <div class="card-desc">
                Deuxième axe d'intervention majeur. Exposition financière élevée avec une <b>VaR 95% de 1080.2 DH</b> et 7 risques nécessitant un audit approfondi sur les itinéraires techniques.
            </div>
        </div>
    """, unsafe_allow_html=True)

st.write("") # Spacer

col3, col4 = st.columns(2)

with col3:
    st.markdown("""
        <div class="custom-card">
            <div class="card-category">RANG #3 — SCORE PFA : 71.8 / 100</div>
            <div class="card-title">P7 — Gestion Budgétaire, Financière et Comptable</div>
            <div class="card-desc">
                Score élevé justifié par 5 risques critiques et une anomalie détectée sur le Dispositif de Maîtrise des Risques (DMR surestimé sur la comptabilité des subventions).
            </div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
        <div class="custom-card">
            <div class="card-category">RANG #4 — SCORE PFA : 61.1 / 100</div>
            <div class="card-title">P1 — Aides et Incitations Financières de l’État</div>
            <div class="card-desc">
                Sous surveillance élevée. Risques principalement axés sur les délais de traitement des dossiers du Fonds de Développement Agricole (FDA).
            </div>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. SECTION ANALYTIQUE COMPLÉMENTAIRE
# ---------------------------------------------------------
st.write("")
st.write("")
st.subheader("📊 Synthèse de la Priorisation et Répartition Stochastique")

df_data = pd.DataFrame([
    {'Processus': 'P9 - Achat', 'Score': 88.7},
    {'Processus': 'P2 - Production', 'Score': 82.8},
    {'Processus': 'P7 - Finance', 'Score': 71.8},
    {'Processus': 'P1 - Aides FDA', 'Score': 61.1},
    {'Processus': 'P4 - Irrigation', 'Score': 48.9},
])

fig = px.bar(df_data, x='Score', y='Processus', orientation='h', color='Score',
             color_continuous_scale=['#4E7D5B', '#1E513B', '#0A2F1D'])
fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='#FAFAFA')
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 6. FOOTER SOMBRE (STYLE DE L'IMAGE)
# ---------------------------------------------------------
st.markdown("""
    <div class="footer-dark">
        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 32px;">
            <div>
                <div class="footer-title">🛡️ ORMVA-TF Risk & Audit</div>
                <p style="font-size: 0.85rem; line-height: 1.6;">
                    Système d'Information d'Aide à la Décision pour le pilotage des risques et la priorisation des missions d'audit interne du Office Régional de Mise en Valeur Agricole du Tafilalet.
                </p>
                <p style="font-size: 0.8rem; margin-top: 16px; color: #6B7280;">
                    📍 Errachidia, Maroc | 📞 +212 5 35 57 20 22
                </p>
            </div>
            <div>
                <div class="footer-section-title">MODULES</div>
                <ul class="footer-links">
                    <li><a href="#">Cartographie</a></li>
                    <li><a href="#">Workflow Validation</a></li>
                    <li><a href="#">Scoring & Priorisation</a></li>
                    <li><a href="#">Simulations Monte Carlo</a></li>
                </ul>
            </div>
            <div>
                <div class="footer-section-title">ANALYTIQUE</div>
                <ul class="footer-links">
                    <li><a href="#">Analyse ANOVA</a></li>
                    <li><a href="#">Contrôle du DMR</a></li>
                    <li><a href="#">Calcul VaR / TVaR</a></li>
                    <li><a href="#">Clustering Risques</a></li>
                </ul>
            </div>
            <div>
                <div class="footer-section-title">GOVERNANCE</div>
                <ul class="footer-links">
                    <li><a href="#">Audit Trail & Logs</a></li>
                    <li><a href="#">Gestion des Accès</a></li>
                    <li><a href="#">Versions du Modèle</a></li>
                    <li><a href="#">Rapports PDF / Excel</a></li>
                </ul>
            </div>
        </div>
        <div style="border-top: 1px solid #1F2937; margin-top: 32px; padding-top: 16px; text-align: center; font-size: 0.75rem; color: #6B7280;">
            © 2026 ORMVA-TF — Projet de Fin d'Études en Génie Financier et Actuariat. Tous droits réservés.
        </div>
    </div>
""", unsafe_allow_html=True)
