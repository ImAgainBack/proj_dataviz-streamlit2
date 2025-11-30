import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from datetime import datetime

# Import configuration centralisée
from config.pollutants import (
    POLLUTANT_THRESHOLDS, POLLUTANT_INFO, MAJOR_CITIES, HIGH_IMPACT_POLLUTANTS,
    GUIDING_QUESTIONS, COLOR_PALETTE, get_pollutant_info, get_color_discrete_map,
    calculate_pollution_index, get_index_category, SENSITIVE_POPULATION_FACTOR,
    INDEX_MODERATE_THRESHOLD, INDEX_HIGH_THRESHOLD
)

# Constantes de configuration de l'application
RECENT_DATA_YEARS_BACK = 1  # Nombre d'années pour considérer les données comme récentes
MIN_DATA_WARNING_THRESHOLD = 100  # Seuil pour afficher un avertissement de données limitées

st.set_page_config(
    page_title="Qualité de l'Air en France - L'air que nous respirons nous tue-t-il ?",
    page_icon="🌬️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def normalize_city(city):
    if pd.isna(city):
        return city
    city_upper = city.upper()
    if 'PARIS' in city_upper and ('ARRONDISSEMENT' in city_upper or city_upper.startswith('PARIS ')):
        return 'PARIS'
    if 'MARSEILLE' in city_upper and ('ARRONDISSEMENT' in city_upper or city_upper.startswith('MARSEILLE ')):
        return 'MARSEILLE'
    if 'LYON' in city_upper and ('ARRONDISSEMENT' in city_upper or city_upper.startswith('LYON ')):
        return 'LYON'
    return city


def is_valid_city(city):
    if pd.isna(city) or city == '':
        return False
    if len(city) > 2 and city.startswith('FR') and city[2].isdigit():
        return False
    if city.startswith('ATMO'):
        return False
    if 'NET-' in city:
        return False
    return True


MAX_CITIES_IN_ALERT = 3


@st.cache_data
def load_data():
    df = pd.read_csv("qualite-de-lair-france.csv", sep=";")
    
    def parse_coords(coord_str):
        try:
            parts = coord_str.split(",")
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            return lat, lon
        except (ValueError, AttributeError, IndexError):
            return None, None
    
    df[["Latitude", "Longitude"]] = df["Coordinates"].apply(
        lambda x: pd.Series(parse_coords(x))
    )
    
    df["Last Updated"] = pd.to_datetime(df["Last Updated"], utc=True, errors="coerce")
    df["Date"] = df["Last Updated"].dt.date
    df["Year"] = df["Last Updated"].dt.year
    df["Month"] = df["Last Updated"].dt.month
    
    air_pollutants = ["NO2", "O3", "PM10", "PM2.5", "SO2", "NO", "CO"]
    df = df[df["Pollutant"].isin(air_pollutants)]
    
    df = df[(df["Value"] >= 0) & (df["Value"] < 1000)]
    
    df = df.dropna(subset=["Latitude", "Longitude", "Value"])
    
    df["City"] = df["City"].fillna(df["Location"])
    
    df = df[df["City"].apply(is_valid_city)]
    
    df["City_Normalized"] = df["City"].apply(normalize_city)
    
    # Ajouter une colonne pour distinguer données récentes vs historiques
    current_year = datetime.now().year
    df["Is_Recent"] = df["Year"] >= (current_year - RECENT_DATA_YEARS_BACK)
    df["Data_Age"] = current_year - df["Year"]
    
    return df


def get_color_for_value(value, pollutant):
    thresholds = POLLUTANT_THRESHOLDS.get(pollutant, {"good": 25, "moderate": 50})
    if value < thresholds["good"]:
        return "green"
    elif value < thresholds["moderate"]:
        return "orange"
    else:
        return "red"


def get_quality_badge(value, pollutant):
    thresholds = POLLUTANT_THRESHOLDS.get(pollutant, {"good": 25, "moderate": 50})
    if value < thresholds["good"]:
        return '<span style="background-color: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-weight: 500;">🟢 Bon</span>'
    elif value < thresholds["moderate"]:
        return '<span style="background-color: #ffc107; color: #212529; padding: 2px 6px; border-radius: 3px; font-weight: 500;">🟠 Modéré</span>'
    else:
        return '<span style="background-color: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-weight: 500;">🔴 Élevé</span>'


def calculate_city_pollution_index(df, city):
    """Calcule l'indice de pollution composite pour une ville"""
    city_data = df[df["City_Normalized"] == city]
    if len(city_data) == 0:
        return 0
    
    values_by_pollutant = city_data.groupby("Pollutant")["Value"].mean().to_dict()
    return calculate_pollution_index(values_by_pollutant)


def create_map(df_filtered, dark_mode=False, selected_pollutants=None):
    center_lat = df_filtered["Latitude"].mean()
    center_lon = df_filtered["Longitude"].mean()
    
    tiles = "CartoDB dark_matter" if dark_mode else "CartoDB positron"
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles=tiles)
    
    if selected_pollutants is None:
        selected_pollutants = df_filtered["Pollutant"].unique().tolist()
    
    location_data = df_filtered.groupby(["Latitude", "Longitude", "City", "Location"]).agg({
        "Value": list,
        "Pollutant": list,
        "Last Updated": "max"
    }).reset_index()
    
    for _, row in location_data.iterrows():
        city = row["City"]
        location = row["Location"]
        values = row["Value"]
        pollutants = row["Pollutant"]
        last_updated = row["Last Updated"]
        date_str = last_updated.strftime('%Y-%m-%d %H:%M') if pd.notna(last_updated) else 'N/A'
        
        pollutant_rows = ""
        avg_value = 0
        main_pollutant = None
        max_value = 0
        
        for poll, val in zip(pollutants, values):
            quality_badge = get_quality_badge(val, poll)
            pollutant_rows += f"<tr><td>{poll}</td><td><b>{val:.1f} µg/m³</b></td><td>{quality_badge}</td></tr>"
            avg_value += val
            if val > max_value:
                max_value = val
                main_pollutant = poll
        
        avg_value = avg_value / len(values)
        
        if len(selected_pollutants) == 1 and main_pollutant:
            color = get_color_for_value(max_value, main_pollutant)
        else:
            color = get_color_for_value(avg_value, main_pollutant) if main_pollutant else "orange"
        
        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px; min-width: 250px;">
            <b style="font-size: 14px;">{city}</b><br>
            <span style="color: #666;">{location}</span>
            <hr style="margin: 5px 0;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background-color: #f8f9fa;">
                    <th style="text-align: left; padding: 4px;">Polluant</th>
                    <th style="text-align: left; padding: 4px;">Valeur</th>
                    <th style="text-align: left; padding: 4px;">Qualité</th>
                </tr>
                {pollutant_rows}
            </table>
            <hr style="margin: 5px 0;">
            <small style="color: #666;">📅 {date_str}</small>
        </div>
        """
        
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=6 + (avg_value / 20),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=350)
        ).add_to(m)
    
    return m


df = load_data()

st.sidebar.markdown("### 🇫🇷")
st.sidebar.title("🎛️ Filtres")

dark_mode = st.sidebar.toggle("🌙 Mode sombre", value=False)

# Nouveau: Toggle données récentes vs historiques
data_mode = st.sidebar.radio(
    "📅 Type de données",
    options=["Toutes", "Récentes (2024-2025)", "Historiques (<2024)"],
    index=0,
    help="Sépare les données récentes des données historiques pour une analyse plus pertinente"
)

# Nouveau: Toggle métropoles uniquement
show_metropoles_only = st.sidebar.toggle(
    "🏙️ Métropoles uniquement",
    value=False,
    help="Afficher uniquement les 10 principales métropoles françaises"
)

if dark_mode:
    template = "plotly_dark"
    st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stMarkdown, .stText, p, span, label, .stSelectbox label, .stMultiSelect label {
        color: #fafafa !important;
    }
    .stSidebar {
        background-color: #1a1a2e;
    }
    .stMetric label, .stMetric [data-testid="stMetricValue"] {
        color: #fafafa !important;
    }
    div[data-testid="stExpander"] {
        background-color: #1a1a2e;
        border-color: #333;
    }
    .chapter-box {
        background-color: #1a1a2e;
        border-left: 4px solid #2E86AB;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .insight-box {
        background-color: #1a1a2e;
        border-left: 4px solid #2E86AB;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
    }
    .legend-box {
        background-color: #1a1a2e;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .legend-box th, .legend-box td {
        color: #fafafa !important;
    }
    .nav-box {
        background-color: #1a1a2e;
        padding: 0.8rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: center;
    }
    .nav-link {
        background-color: #2E86AB;
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        text-decoration: none;
        font-size: 0.9rem;
        font-weight: 500;
    }
    .scoreboard {
        background: linear-gradient(135deg, #2E86AB 0%, #1a5a7a 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .methodology-banner {
        background-color: #3d3d00;
        border: 1px solid #ffc107;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #fafafa;
    }
    .question-card {
        background-color: #1a1a2e;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        height: 100%;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    template = "plotly_white"
    st.markdown("""
    <style>
    .chapter-box {
        background-color: #e8f4f8;
        border-left: 4px solid #2E86AB;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .insight-box {
        background-color: #e8f4f8;
        border-left: 4px solid #2E86AB;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
    }
    .legend-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .nav-box {
        background-color: #f8f9fa;
        padding: 0.8rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: center;
    }
    .nav-link {
        background-color: #2E86AB;
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        text-decoration: none;
        font-size: 0.9rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    .nav-link:hover {
        background-color: #1a5a7a;
        transform: translateY(-2px);
    }
    .scoreboard {
        background: linear-gradient(135deg, #2E86AB 0%, #1a5a7a 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .methodology-banner {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
    .question-card {
        background-color: #e8f4f8;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        height: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

all_pollutants = sorted(df["Pollutant"].unique())
selected_pollutants = st.sidebar.multiselect(
    "Polluants",
    options=all_pollutants,
    default=["NO2", "PM10", "PM2.5"]
)

# Filtrer les villes selon le toggle métropoles
if show_metropoles_only:
    available_cities = [c for c in sorted(df["City_Normalized"].dropna().unique()) if c in MAJOR_CITIES]
else:
    available_cities = sorted(df["City_Normalized"].dropna().unique())

# Nouveau: Recherche de ville avec autocomplétion
search_city = st.sidebar.text_input("🔍 Rechercher une ville", placeholder="Tapez le nom...")
if search_city:
    filtered_cities = [c for c in available_cities if search_city.upper() in c.upper()]
else:
    filtered_cities = available_cities

selected_cities = st.sidebar.multiselect(
    "Villes",
    options=filtered_cities,
    default=[]
)

if df["Date"].notna().any():
    min_date = df["Date"].min()
    max_date = df["Date"].max()
    date_range = st.sidebar.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
else:
    date_range = None

# Application des filtres
df_filtered = df.copy()

# Filtre par type de données (récentes vs historiques)
if data_mode == "Récentes (2024-2025)":
    df_filtered = df_filtered[df_filtered["Is_Recent"] == True]
elif data_mode == "Historiques (<2024)":
    df_filtered = df_filtered[df_filtered["Is_Recent"] == False]

# Filtre métropoles uniquement
if show_metropoles_only:
    df_filtered = df_filtered[df_filtered["City_Normalized"].isin(MAJOR_CITIES)]

if selected_pollutants:
    df_filtered = df_filtered[df_filtered["Pollutant"].isin(selected_pollutants)]
if selected_cities:
    df_filtered = df_filtered[df_filtered["City_Normalized"].isin(selected_cities)]
if date_range and len(date_range) == 2:
    df_filtered = df_filtered[
        (df_filtered["Date"] >= date_range[0]) & 
        (df_filtered["Date"] <= date_range[1])
    ]

# Afficher un avertissement si les données sont limitées
n_filtered = len(df_filtered)
if n_filtered < MIN_DATA_WARNING_THRESHOLD and n_filtered > 0:
    st.sidebar.warning(f"⚠️ Données limitées ({n_filtered} mesures)")
elif n_filtered == 0:
    st.sidebar.error("❌ Aucune donnée avec ces filtres")

st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="font-size: 2.8rem; margin-bottom: 0.5rem;">🌬️ L'air que nous respirons nous tue-t-il ?</h1>
    <p style="font-size: 1.3rem; color: #6c757d;">Une exploration des données de pollution atmosphérique en France</p>
</div>
""", unsafe_allow_html=True)

# Navigation interne (ancres)
st.markdown("""
<div class="nav-box">
    <a href="#synthese" class="nav-link">📊 Synthèse</a>
    <a href="#carte" class="nav-link">🗺️ Carte</a>
    <a href="#analyse" class="nav-link">📈 Analyse</a>
    <a href="#sante" class="nav-link">❤️ Santé</a>
    <a href="#recommandations" class="nav-link">💡 Actions</a>
</div>
""", unsafe_allow_html=True)

# Bandeau méthodologique
date_min_data = df["Date"].min()
date_max_data = df["Date"].max()
st.markdown(f"""
<div class="methodology-banner">
⚠️ <strong>Note méthodologique</strong> : Les mesures présentées sont ponctuelles (horaires) et ne doivent pas être interprétées 
comme des moyennes annuelles officielles. Les seuils OMS indiqués sont des valeurs de référence annuelles ou sur 8h. 
Données couvrant la période du <strong>{date_min_data}</strong> au <strong>{date_max_data}</strong>.
</div>
""", unsafe_allow_html=True)

# Questions directrices
st.markdown('<a id="synthese"></a>', unsafe_allow_html=True)
st.markdown("## 🎯 Questions clés pour guider notre exploration")

q_cols = st.columns(4)
for i, question in enumerate(GUIDING_QUESTIONS):
    with q_cols[i]:
        st.markdown(f"""
        <div class="question-card">
            <p style="font-size: 1rem; margin: 0;">{question}</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("")

# Résumé exécutif dynamique (scoreboard)
if len(df_filtered) > 0:
    # Calcul des indicateurs clés
    most_polluted_city = df_filtered.groupby("City_Normalized")["Value"].mean().idxmax()
    most_polluted_value = df_filtered.groupby("City_Normalized")["Value"].mean().max()
    
    dominant_pollutant = df_filtered.groupby("Pollutant")["Value"].mean().idxmax()
    dominant_pollutant_value = df_filtered.groupby("Pollutant")["Value"].mean().max()
    
    overall_avg = df_filtered["Value"].mean()
    
    # Calcul de l'indice composite pour la ville la plus polluée
    city_pollution_index = calculate_city_pollution_index(df_filtered, most_polluted_city)
    index_category = get_index_category(city_pollution_index)
    
    st.markdown(f"""
    <div class="scoreboard">
        <h3 style="margin-top: 0; color: white;">📊 Résumé exécutif - Indicateurs clés</h3>
        <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 1rem;">
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold;">{most_polluted_city}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Zone la plus critique</div>
                <div style="font-size: 1.2rem;">{most_polluted_value:.1f} µg/m³</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold;">{dominant_pollutant}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Polluant dominant</div>
                <div style="font-size: 1.2rem;">{dominant_pollutant_value:.1f} µg/m³</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold;">{index_category['emoji']} {city_pollution_index}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Indice composite</div>
                <div style="font-size: 1.2rem;">{index_category['label']}</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold;">{len(df_filtered):,}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Mesures analysées</div>
                <div style="font-size: 1.2rem;">n = {len(df_filtered):,}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

st.markdown("""
## 📖 Le problème

### Pourquoi la qualité de l'air est un enjeu majeur en France ?
""")

st.markdown("""
<div class="chapter-box">
La pollution de l'air est responsable de <strong>40 000 décès prématurés</strong> chaque année en France. 
C'est la <strong>3ème cause de mortalité</strong> après le tabac et l'alcool, avec un coût sanitaire estimé 
à <strong>100 milliards d'euros par an</strong>.

<blockquote style="font-style: italic; border-left: 3px solid #888; padding-left: 1rem; margin: 1rem 0;">
"L'air que nous respirons dans nos villes nous tue lentement."
</blockquote>

Face à ce constat alarmant, des questions s'imposent : <strong>Où se situent les zones les plus à risque ? 
Quels polluants surveiller en priorité ?</strong>
</div>
""", unsafe_allow_html=True)

st.markdown("#### 📊 Les données à notre disposition")

n_stations = df["Location"].nunique()
n_cities_total = df["City_Normalized"].nunique()
date_min = df["Date"].min()
date_max = df["Date"].max()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🔬 Mesures totales", f"{len(df):,}")
with col2:
    st.metric("📍 Stations de mesure", n_stations)
with col3:
    st.metric("🏙️ Villes couvertes", n_cities_total)
with col4:
    st.metric("📅 Période", f"{date_min} → {date_max}")

st.markdown("""
*Ces données nous permettent d'analyser la situation de la pollution atmosphérique sur l'ensemble du territoire français. 
Explorons maintenant la répartition géographique de ces mesures...*
""")

st.markdown("---")

st.markdown('<a id="carte"></a>', unsafe_allow_html=True)
st.markdown("""
## 🗺️ Cartographie de la pollution

Visualisation géographique des niveaux de pollution. Chaque point représente une station, colorée selon le niveau mesuré.
""")

st.caption(f"📍 Nombre de mesures affichées : {len(df_filtered):,}")

st.markdown("""
<div class="legend-box">
<strong>Légende des couleurs (seuils OMS par polluant en µg/m³) :</strong>
<table style="width: 100%; margin-top: 0.5rem; font-size: 0.9rem;">
<tr><th>Polluant</th><th>🟢 Bon</th><th>🟠 Modéré</th><th>🔴 Élevé</th></tr>
<tr><td>PM2.5</td><td>&lt; 15</td><td>15 - 25</td><td>&gt; 25</td></tr>
<tr><td>PM10</td><td>&lt; 45</td><td>45 - 75</td><td>&gt; 75</td></tr>
<tr><td>NO2</td><td>&lt; 25</td><td>25 - 50</td><td>&gt; 50</td></tr>
<tr><td>O3</td><td>&lt; 100</td><td>100 - 180</td><td>&gt; 180</td></tr>
<tr><td>SO2</td><td>&lt; 40</td><td>40 - 100</td><td>&gt; 100</td></tr>
<tr><td>CO</td><td>&lt; 4000</td><td>4000 - 10000</td><td>&gt; 10000</td></tr>
<tr><td>NO</td><td>&lt; 25</td><td>25 - 50</td><td>&gt; 50</td></tr>
</table>
</div>
""", unsafe_allow_html=True)

if len(df_filtered) > 0:
    map_data = df_filtered.groupby(["City", "Location", "Latitude", "Longitude", "Pollutant"]).agg({
        "Value": "mean",
        "Last Updated": "max"
    }).reset_index()
    
    if len(map_data) > 500:
        map_data = map_data.sample(500, random_state=42)
    
    m = create_map(map_data, dark_mode, selected_pollutants)
    st_folium(m, width=None, height=500)
else:
    st.warning("Aucune donnée à afficher avec les filtres sélectionnés.")

st.markdown("""
*La carte révèle une concentration des stations de mesure dans les grandes agglomérations. 
Mais que nous disent réellement ces données ? Passons à l'analyse des tendances...*
""")

st.markdown("---")

st.markdown('<a id="analyse"></a>', unsafe_allow_html=True)
st.markdown("## 📊 Analyse des données")

# Onglet pour choisir le type de visualisation
analysis_view = st.radio(
    "Type d'analyse",
    options=["🏙️ Par ville", "🔬 Par polluant", "📅 Temporelle", "🔗 Corrélations"],
    horizontal=True
)

if analysis_view == "🏙️ Par ville":
    st.markdown("### 🏆 Classement des villes avec indice de pollution composite")
    
    # Calcul de l'indice composite pour chaque ville
    if len(df_filtered) > 0:
        cities_list = df_filtered["City_Normalized"].unique()
        city_indices = []
        for city in cities_list:
            idx = calculate_city_pollution_index(df_filtered, city)
            city_count = len(df_filtered[df_filtered["City_Normalized"] == city])
            city_indices.append({
                "Ville": city, 
                "Indice": idx,
                "Catégorie": get_index_category(idx)["label"],
                "n_mesures": city_count
            })
        
        city_idx_df = pd.DataFrame(city_indices).sort_values("Indice", ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔴 Top 10 - Indice le plus élevé")
            top_10 = city_idx_df.head(10)
            fig_index = px.bar(
                top_10,
                x="Indice",
                y="Ville",
                orientation="h",
                title="Indice de pollution composite par ville",
                labels={"Indice": "Indice composite (0-150)", "Ville": ""},
                color="Indice",
                color_continuous_scale="RdYlGn_r",
                template=template
            )
            fig_index.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_index, use_container_width=True)
            st.caption(f"Basé sur {len(cities_list)} villes, pondéré par dangerosité des polluants (PM2.5×1.5, NO2×1.3, PM10×1.2)")
        
        with col2:
            # Heatmap villes vs polluants (simplifié)
            city_pollutant = df_filtered.groupby(["City_Normalized", "Pollutant"])["Value"].mean().reset_index()
            top_cities_list = city_idx_df.head(8)["Ville"].tolist()
            city_pollutant_top = city_pollutant[city_pollutant["City_Normalized"].isin(top_cities_list)]
            
            fig_heatmap = px.density_heatmap(
                city_pollutant_top,
                x="Pollutant",
                y="City_Normalized",
                z="Value",
                title="Profil de pollution des villes critiques",
                labels={"Value": "µg/m³", "Pollutant": "Polluant", "City_Normalized": "Ville"},
                color_continuous_scale="YlOrRd",
                template=template
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

elif analysis_view == "🔬 Par polluant":
    st.markdown("### 🔬 Distribution et statistiques par polluant")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Box plot des distributions
        fig_box = px.box(
            df_filtered,
            x="Pollutant",
            y="Value",
            title="Distribution des concentrations",
            labels={"Value": "Concentration (µg/m³)", "Pollutant": "Polluant"},
            color="Pollutant",
            color_discrete_map=get_color_discrete_map(selected_pollutants),
            template=template
        )
        fig_box.update_layout(showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)
    
    with col2:
        # Tableau statistique
        pollutant_stats = df_filtered.groupby("Pollutant").agg({
            "Value": ["mean", "median", "std", "count"]
        }).round(2)
        pollutant_stats.columns = ["Moyenne", "Médiane", "Écart-type", "Nb mesures"]
        pollutant_stats = pollutant_stats.reset_index()
        
        # Ajouter seuil OMS
        pollutant_stats["Seuil OMS"] = pollutant_stats["Pollutant"].apply(
            lambda p: POLLUTANT_THRESHOLDS.get(p, {}).get("moderate", "-")
        )
        
        st.dataframe(pollutant_stats, use_container_width=True, hide_index=True)
        
        st.markdown("""
        <div class="insight-box">
        <strong>💡 Interprétation</strong> : Un écart-type élevé indique une forte variabilité des mesures. 
        Comparez la moyenne au seuil OMS pour évaluer le niveau de risque.
        </div>
        """, unsafe_allow_html=True)

elif analysis_view == "📅 Temporelle":
    st.markdown("### 📈 Évolution temporelle")
    
    # Switch mensuel/annuel
    time_view = st.radio("Granularité", ["Mensuelle", "Annuelle"], horizontal=True)
    
    if time_view == "Mensuelle":
        df_temporal = df_filtered.groupby(["Year", "Month", "Pollutant"])["Value"].mean().reset_index()
        df_temporal["Date"] = pd.to_datetime(df_temporal[["Year", "Month"]].assign(day=1))
        
        fig_temporal = px.line(
            df_temporal,
            x="Date",
            y="Value",
            color="Pollutant",
            title="Évolution mensuelle des concentrations",
            labels={"Value": "Concentration (µg/m³)", "Date": "", "Pollutant": "Polluant"},
            color_discrete_map=get_color_discrete_map(selected_pollutants),
            template=template
        )
        fig_temporal.update_layout(hovermode="x unified")
    else:
        df_temporal = df_filtered.groupby(["Year", "Pollutant"])["Value"].mean().reset_index()
        
        fig_temporal = px.bar(
            df_temporal,
            x="Year",
            y="Value",
            color="Pollutant",
            title="Concentration moyenne par année",
            labels={"Value": "Concentration (µg/m³)", "Year": "Année", "Pollutant": "Polluant"},
            barmode="group",
            color_discrete_map=get_color_discrete_map(selected_pollutants),
            template=template
        )
    
    st.plotly_chart(fig_temporal, use_container_width=True)
    
    st.markdown("""
    <div class="insight-box">
    <strong>💡 Tendances saisonnières</strong> : L'ozone augmente en été (réaction photochimique avec le soleil), 
    tandis que les particules fines sont plus élevées en hiver (chauffage domestique).
    </div>
    """, unsafe_allow_html=True)

elif analysis_view == "🔗 Corrélations":
    st.markdown("### 🔗 Corrélations entre polluants")
    
    # Préparer les données pour la corrélation
    if len(df_filtered) > 0 and len(selected_pollutants) >= 2:
        # Pivoter pour avoir les polluants en colonnes
        pivot_data = df_filtered.pivot_table(
            values="Value",
            index=["City_Normalized", "Date"],
            columns="Pollutant",
            aggfunc="mean"
        ).dropna()
        
        if len(pivot_data) > 10:
            corr_matrix = pivot_data.corr()
            
            fig_corr = px.imshow(
                corr_matrix,
                title="Matrice de corrélation entre polluants",
                labels=dict(color="Corrélation"),
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1,
                template=template
            )
            fig_corr.update_layout(width=600, height=500)
            st.plotly_chart(fig_corr, use_container_width=True)
            
            st.markdown("""
            <div class="insight-box">
            <strong>💡 Interprétation</strong> : 
            <ul>
                <li>Corrélation proche de <strong>+1</strong> : les polluants varient ensemble (sources communes)</li>
                <li>Corrélation proche de <strong>-1</strong> : variation inverse (ex: NO et O3 en journée)</li>
                <li>Corrélation proche de <strong>0</strong> : pas de relation directe</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Pas assez de données communes pour calculer les corrélations. Essayez d'élargir les filtres.")
    else:
        st.info("Sélectionnez au moins 2 polluants pour voir les corrélations.")

st.markdown("---")

# Section métropoles simplifiée avec l'indice composite
st.markdown("## 🏙️ Comparaison des grandes métropoles")

df_metro = df_filtered[df_filtered["City_Normalized"].isin(MAJOR_CITIES)]

if len(df_metro) > 0:
    # Calcul de l'indice pour chaque métropole
    metro_indices = []
    for city in MAJOR_CITIES:
        if city in df_metro["City_Normalized"].values:
            idx = calculate_city_pollution_index(df_metro, city)
            metro_indices.append({"Métropole": city, "Indice": idx})
    
    metro_df = pd.DataFrame(metro_indices).sort_values("Indice", ascending=False)
    
    fig_metro = px.bar(
        metro_df,
        x="Indice",
        y="Métropole",
        orientation="h",
        title="Indice de pollution composite par métropole",
        labels={"Indice": "Indice composite", "Métropole": ""},
        color="Indice",
        color_continuous_scale="RdYlGn_r",
        template=template
    )
    fig_metro.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_metro, use_container_width=True)
    st.caption("Indice pondéré : PM2.5 (×1.5), NO2 (×1.3), PM10 (×1.2). Score 0-50: bon, 50-100: modéré, >100: élevé")
else:
    st.info("Aucune donnée disponible pour les grandes métropoles avec les filtres actuels.")

st.markdown("---")

st.markdown('<a id="sante"></a>', unsafe_allow_html=True)
st.markdown("## ❤️ Impact santé et alertes")

# Toggle pour les populations sensibles
sensitive_population = st.checkbox("👶 Afficher les recommandations pour populations sensibles (enfants, asthmatiques)")

df_high_impact = df_filtered[df_filtered["Pollutant"].isin(HIGH_IMPACT_POLLUTANTS)]

if len(df_high_impact) > 0:
    city_high_impact = df_high_impact.groupby(["City_Normalized", "Pollutant"])["Value"].mean().reset_index()
    city_high_impact = city_high_impact.sort_values("Value", ascending=False).head(15)
    
    def get_risk_level(value, pollutant, sensitive=False):
        thresholds = POLLUTANT_THRESHOLDS.get(pollutant, {"good": 25, "moderate": 50})
        # Seuils plus stricts pour populations sensibles
        factor = SENSITIVE_POPULATION_FACTOR if sensitive else 1.0
        good_threshold = thresholds["good"] * factor
        moderate_threshold = thresholds["moderate"] * factor
        
        if value < good_threshold:
            return "🟢 Faible"
        elif value < moderate_threshold:
            return "🟠 Modéré"
        else:
            return "🔴 Élevé"
    
    def get_health_recommendation(value, pollutant, sensitive=False):
        thresholds = POLLUTANT_THRESHOLDS.get(pollutant, {"good": 25, "moderate": 50})
        factor = SENSITIVE_POPULATION_FACTOR if sensitive else 1.0
        good_threshold = thresholds["good"] * factor
        moderate_threshold = thresholds["moderate"] * factor
        
        if value < good_threshold:
            return "Activités normales" if not sensitive else "Activités normales avec surveillance"
        elif value < moderate_threshold:
            return "Limiter les efforts prolongés" if not sensitive else "Éviter les efforts, rester à l'intérieur"
        else:
            return "Éviter les activités en extérieur" if not sensitive else "Rester à l'intérieur, consulter si symptômes"
    
    city_high_impact["Niveau de risque"] = city_high_impact.apply(
        lambda row: get_risk_level(row["Value"], row["Pollutant"], sensitive_population), axis=1
    )
    city_high_impact["Recommandation"] = city_high_impact.apply(
        lambda row: get_health_recommendation(row["Value"], row["Pollutant"], sensitive_population), axis=1
    )
    
    display_df = city_high_impact.rename(columns={
        "City_Normalized": "Ville",
        "Pollutant": "Polluant",
        "Value": "Concentration (µg/m³)"
    })
    display_df["Concentration (µg/m³)"] = display_df["Concentration (µg/m³)"].round(1)
    
    st.dataframe(
        display_df[["Ville", "Polluant", "Concentration (µg/m³)", "Niveau de risque", "Recommandation"]],
        use_container_width=True,
        hide_index=True
    )
    st.caption(f"n = {len(df_high_impact):,} mesures pour les polluants à impact élevé (PM2.5, PM10, NO2)")
else:
    st.info("Aucune donnée disponible pour les polluants à impact élevé avec les filtres actuels.")

# Alertes dynamiques
if len(df_filtered) > 0:
    alerts = []
    
    for pollutant in ["PM2.5", "PM10", "NO2", "O3"]:
        df_poll = df_filtered[df_filtered["Pollutant"] == pollutant]
        if len(df_poll) > 0:
            avg_value = df_poll["Value"].mean()
            thresholds = POLLUTANT_THRESHOLDS.get(pollutant, {"good": 25, "moderate": 50})
            factor = SENSITIVE_POPULATION_FACTOR if sensitive_population else 1.0
            threshold = thresholds["moderate"] * factor
            
            if avg_value > threshold:
                if selected_cities:
                    city_name = ", ".join(selected_cities[:MAX_CITIES_IN_ALERT])
                    if len(selected_cities) > MAX_CITIES_IN_ALERT:
                        city_name += "..."
                else:
                    city_name = "les zones sélectionnées"
                
                recommendations = {
                    "PM2.5": "Évitez les activités sportives en extérieur.",
                    "PM10": "Limitez le jogging et le vélo en extérieur.",
                    "NO2": "Restez à l'intérieur si possible.",
                    "O3": "Évitez les efforts physiques entre 12h et 16h."
                }
                
                alerts.append(f"⚠️ **{pollutant}** dans {city_name} : {avg_value:.1f} µg/m³. {recommendations[pollutant]}")
    
    if alerts:
        st.markdown("### 🚨 Alertes actives")
        for alert in alerts:
            st.warning(alert)

st.markdown("---")

st.markdown('<a id="recommandations"></a>', unsafe_allow_html=True)
st.markdown("## 💡 Recommandations et actions")

if len(df_filtered) > 0:
    highest_pollutant = df_filtered.groupby("Pollutant")["Value"].mean().idxmax()
    highest_city = df_filtered.groupby("City_Normalized")["Value"].mean().idxmax()
else:
    highest_pollutant = "N/A"
    highest_city = "N/A"

st.markdown("""
<div class="chapter-box">
<h4>📌 Résumé des insights clés</h4>
<ul>
    <li><strong>Les grandes métropoles</strong> sont les plus touchées par la pollution atmosphérique</li>
    <li><strong>Le NO2 et les particules fines</strong> sont les polluants les plus préoccupants</li>
    <li><strong>Des variations saisonnières</strong> existent : ozone en été, particules en hiver</li>
    <li><strong>Les zones rurales et côtières</strong> bénéficient d'un air de meilleure qualité</li>
</ul>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="insight-box">
    <h4>👤 Pour les citoyens</h4>
    <ul>
        <li>Consultez régulièrement les indices de qualité de l'air de votre ville</li>
        <li>Limitez les activités physiques extérieures lors des pics de pollution</li>
        <li>Privilégiez les déplacements à pied, vélo ou transports en commun</li>
        <li>Aérez votre logement aux heures de moindre trafic</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="insight-box">
    <h4>🏛️ Pour les décideurs</h4>
    <ul>
        <li>Renforcer et étendre les Zones à Faibles Émissions (ZFE)</li>
        <li>Développer les transports en commun et infrastructures cyclables</li>
        <li>Soutenir la rénovation énergétique des bâtiments</li>
        <li>Encourager le passage aux véhicules électriques</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

with st.expander("📚 Comprendre les polluants en détail"):
    st.markdown("""
    ### PM2.5 et PM10 (Particules fines) - ⚠️ IMPACT TRÈS ÉLEVÉ
    - **Sources** : Trafic routier, chauffage au bois, industrie, agriculture
    - **Effets santé** : Pénètrent profondément dans les poumons (PM2.5 jusqu'au sang)
    - **Risques** : Maladies cardiovasculaires, cancers, asthme
    - **Prévalence** : Très présent en hiver (chauffage) et en zone urbaine dense
    - **Seuil OMS** : PM2.5: 15 µg/m³ | PM10: 45 µg/m³ (moyenne annuelle)
    
    ### NO2 (Dioxyde d'azote) - ⚠️ IMPACT ÉLEVÉ
    - **Sources** : Principalement le trafic routier (moteurs diesel)
    - **Effets santé** : Irritation des voies respiratoires, aggrave l'asthme
    - **Risques** : Bronchites chroniques, diminution fonction pulmonaire
    - **Prévalence** : Très élevé le long des grands axes routiers
    - **Seuil OMS** : 25 µg/m³ (moyenne annuelle)
    
    ### O3 (Ozone) - ⚠️ IMPACT ÉLEVÉ EN ÉTÉ
    - **Sources** : Formé par réaction chimique (NOx + COV + soleil)
    - **Effets santé** : Irritation yeux et voies respiratoires, toux
    - **Risques** : Crises d'asthme, diminution capacité respiratoire
    - **Prévalence** : Pics en été lors des canicules
    - **Seuil OMS** : 100 µg/m³ (moyenne sur 8h)
    
    ### SO2 (Dioxyde de soufre) - IMPACT MODÉRÉ
    - **Sources** : Industrie, centrales thermiques, transport maritime
    - **Effets santé** : Irritation des bronches
    - **Risques** : Aggravation de l'asthme et bronchites
    - **Prévalence** : En baisse grâce aux régulations, reste élevé près des industries
    - **Seuil OMS** : 40 µg/m³ (moyenne sur 24h)
    
    ### CO (Monoxyde de carbone) - IMPACT LOCALISÉ
    - **Sources** : Combustion incomplète (voitures, chauffage)
    - **Effets santé** : Se fixe sur l'hémoglobine, réduit transport d'oxygène
    - **Risques** : Maux de tête, vertiges, mortel à forte dose
    - **Prévalence** : Rare en extérieur, problématique en intérieur
    - **Seuil OMS** : 4 mg/m³ (moyenne sur 24h)
    
    ### NO (Monoxyde d'azote) - IMPACT MODÉRÉ
    - **Sources** : Trafic, se transforme rapidement en NO2
    - **Effets santé** : Moins toxique que NO2 directement
    - **Prévalence** : Marqueur du trafic routier
    - **Seuil OMS** : 25 µg/m³
    """)

st.markdown(f"""
<div class="insight-box">
<h4>🎯 Call to Action</h4>
<p>
<strong>Consultez la qualité de l'air de votre ville</strong> en utilisant les filtres dans la barre latérale. 
Sélectionnez votre ville et les polluants qui vous intéressent pour obtenir une analyse personnalisée.
</p>
<p>
Parmi les données actuellement affichées, <strong>{highest_pollutant}</strong> présente la concentration moyenne la plus élevée,
et <strong>{highest_city}</strong> est la zone la plus touchée.
</p>
</div>
""", unsafe_allow_html=True)

st.download_button(
    label="📥 Télécharger les données filtrées",
    data=df_filtered.to_csv(index=False),
    file_name="qualite_air_export.csv",
    mime="text/csv"
)

st.markdown("---")

last_update = df["Last Updated"].max()
last_update_str = last_update.strftime("%Y-%m-%d %H:%M") if pd.notna(last_update) else "N/A"
st.markdown(f"""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    <p>📊 <strong>Source des données</strong> : European Environment Agency (EEA) - OpenData Qualité de l'Air</p>
    <p>📅 <strong>Dernière mise à jour des données</strong> : {last_update_str}</p>
    <p>🔬 <strong>Méthodologie</strong> : Données issues des stations de mesure officielles, agrégées et analysées pour cette application</p>
    <p>🔗 <a href="https://github.com/ImAgainBack/proj_dataviz-streamlit2" target="_blank">Voir le projet sur GitHub</a></p>
    <p>💡 Cette application utilise des données publiques pour sensibiliser à la qualité de l'air.</p>
</div>
""", unsafe_allow_html=True)
