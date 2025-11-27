import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from datetime import datetime

st.set_page_config(
    page_title="Qualité de l'Air en France",
    page_icon="🌬️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6c757d;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2E86AB;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .insight-box {
        background-color: #e8f4f8;
        border-left: 4px solid #2E86AB;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
    }
    .metric-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


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
    
    return df


def get_pollutant_info(pollutant):
    info = {
        "NO2": {"name": "Dioxyde d'azote", "color": "#E74C3C", "icon": "🚗"},
        "O3": {"name": "Ozone", "color": "#3498DB", "icon": "☀️"},
        "PM10": {"name": "Particules PM10", "color": "#9B59B6", "icon": "🏭"},
        "PM2.5": {"name": "Particules fines PM2.5", "color": "#E67E22", "icon": "🌫️"},
        "SO2": {"name": "Dioxyde de soufre", "color": "#1ABC9C", "icon": "⚗️"},
        "NO": {"name": "Monoxyde d'azote", "color": "#F39C12", "icon": "🔥"},
        "CO": {"name": "Monoxyde de carbone", "color": "#34495E", "icon": "💨"}
    }
    return info.get(pollutant, {"name": pollutant, "color": "#7F8C8D", "icon": "📊"})


def create_map(df_filtered):
    center_lat = df_filtered["Latitude"].mean()
    center_lon = df_filtered["Longitude"].mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="CartoDB positron")
    
    for _, row in df_filtered.iterrows():
        value = row["Value"]
        pollutant = row["Pollutant"]
        info = get_pollutant_info(pollutant)
        
        if value < 25:
            color = "green"
        elif value < 50:
            color = "orange"
        else:
            color = "red"
        
        popup_text = f"""
        <b>{row['City']}</b><br>
        📍 {row['Location']}<br>
        🔬 {pollutant}: {value:.1f} µg/m³<br>
        📅 {row['Last Updated'].strftime('%Y-%m-%d %H:%M') if pd.notna(row['Last Updated']) else 'N/A'}
        """
        
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=6 + (value / 20),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(m)
    
    return m


df = load_data()

st.markdown('<p class="main-header">🌬️ Qualité de l\'Air en France</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Explorer les données de pollution atmosphérique à travers la France</p>', unsafe_allow_html=True)

st.markdown("""
<div class="insight-box">
<strong>L'air que nous respirons est essentiel à notre santé.</strong> Chaque jour, des milliers de capteurs 
mesurent la qualité de l'air en France. Cette application vous permet d'explorer ces données, de comprendre 
les tendances de pollution et d'identifier les zones les plus touchées.
</div>
""", unsafe_allow_html=True)

with st.expander("📚 Comprendre les polluants"):
    st.markdown("""
    ### NO2 (Dioxyde d'azote)
    - **Sources** : Trafic routier, centrales thermiques, chauffage
    - **Effets santé** : Irritation des voies respiratoires, aggravation de l'asthme
    - **Seuil OMS** : 25 µg/m³ (moyenne annuelle)
    
    ### PM10 / PM2.5 (Particules fines)
    - **Sources** : Combustion (véhicules, industrie, chauffage), poussières naturelles
    - **Effets santé** : Maladies cardiovasculaires et respiratoires, cancers
    - **Seuil OMS** : PM2.5: 15 µg/m³ | PM10: 45 µg/m³ (moyenne annuelle)
    
    ### O3 (Ozone)
    - **Sources** : Formé par réaction photochimique (NOx + COV + UV)
    - **Effets santé** : Irritation des yeux et voies respiratoires, crises d'asthme
    - **Seuil OMS** : 100 µg/m³ (moyenne sur 8h)
    
    ### SO2 (Dioxyde de soufre)
    - **Sources** : Combustion de combustibles fossiles (charbon, pétrole), industrie
    - **Effets santé** : Irritation des voies respiratoires, bronchites
    - **Seuil OMS** : 40 µg/m³ (moyenne sur 24h)
    
    ### CO (Monoxyde de carbone)
    - **Sources** : Combustion incomplète (véhicules, chauffage défectueux)
    - **Effets santé** : Maux de tête, vertiges, intoxication grave à forte dose
    - **Seuil OMS** : 4 mg/m³ (moyenne sur 24h)
    """)

st.sidebar.markdown("### 🇫🇷")
st.sidebar.title("🎛️ Filtres")

all_pollutants = sorted(df["Pollutant"].unique())
selected_pollutants = st.sidebar.multiselect(
    "Polluants",
    options=all_pollutants,
    default=["NO2", "PM10", "O3"]
)

all_cities = sorted(df["City"].dropna().unique())
selected_cities = st.sidebar.multiselect(
    "Villes",
    options=all_cities,
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

df_filtered = df.copy()
if selected_pollutants:
    df_filtered = df_filtered[df_filtered["Pollutant"].isin(selected_pollutants)]
if selected_cities:
    df_filtered = df_filtered[df_filtered["City"].isin(selected_cities)]
if date_range and len(date_range) == 2:
    df_filtered = df_filtered[
        (df_filtered["Date"] >= date_range[0]) & 
        (df_filtered["Date"] <= date_range[1])
    ]

st.markdown('<p class="section-header">📊 Indicateurs Clés</p>', unsafe_allow_html=True)

years = sorted(df_filtered["Year"].dropna().unique())
current_year = max(years) if years else None
prev_year = years[-2] if len(years) >= 2 else None

col1, col2, col3, col4 = st.columns(4)

with col1:
    has_filters_applied = selected_cities or len(selected_pollutants) != len(all_pollutants)
    delta_text = f"{len(df_filtered) - len(df)} par rapport au total" if has_filters_applied else None
    st.metric(
        label="🔬 Mesures",
        value=f"{len(df_filtered):,}",
        delta=delta_text
    )

with col2:
    avg_value = df_filtered["Value"].mean()
    avg_delta = None
    if current_year and prev_year:
        current_avg = df_filtered[df_filtered["Year"] == current_year]["Value"].mean()
        prev_avg = df_filtered[df_filtered["Year"] == prev_year]["Value"].mean()
        if pd.notna(current_avg) and pd.notna(prev_avg) and prev_avg > 0:
            avg_delta = f"{((current_avg - prev_avg) / prev_avg * 100):.1f}% vs {prev_year}"
    st.metric(
        label="📈 Concentration moyenne",
        value=f"{avg_value:.1f} µg/m³",
        delta=avg_delta,
        delta_color="inverse"
    )

with col3:
    max_value = df_filtered["Value"].max()
    max_delta = None
    if current_year and prev_year:
        current_max = df_filtered[df_filtered["Year"] == current_year]["Value"].max()
        prev_max = df_filtered[df_filtered["Year"] == prev_year]["Value"].max()
        if pd.notna(current_max) and pd.notna(prev_max) and prev_max > 0:
            max_delta = f"{((current_max - prev_max) / prev_max * 100):.1f}% vs {prev_year}"
    st.metric(
        label="⚠️ Maximum observé",
        value=f"{max_value:.1f} µg/m³",
        delta=max_delta,
        delta_color="inverse"
    )

with col4:
    n_cities = df_filtered["City"].nunique()
    st.metric(
        label="🏙️ Villes couvertes",
        value=n_cities
    )

st.download_button(
    label="📥 Télécharger les données",
    data=df_filtered.to_csv(index=False),
    file_name="qualite_air_export.csv",
    mime="text/csv"
)

st.markdown('<p class="section-header">🗺️ Carte des Stations de Mesure</p>', unsafe_allow_html=True)

st.markdown("""
<div style="background-color: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
<strong>Légende des couleurs (concentration en µg/m³) :</strong>
<table style="width: 100%; margin-top: 0.5rem;">
<tr>
<td style="text-align: center;"><span style="background-color: green; color: white; padding: 4px 12px; border-radius: 4px;">🟢 Bon</span><br><small>&lt; 25</small></td>
<td style="text-align: center;"><span style="background-color: orange; color: white; padding: 4px 12px; border-radius: 4px;">🟠 Modéré</span><br><small>25 - 50</small></td>
<td style="text-align: center;"><span style="background-color: red; color: white; padding: 4px 12px; border-radius: 4px;">🔴 Élevé</span><br><small>&gt; 50</small></td>
</tr>
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
    
    m = create_map(map_data)
    st_folium(m, width=None, height=500)
else:
    st.warning("Aucune donnée à afficher avec les filtres sélectionnés.")

st.markdown('<p class="section-header">📈 Analyse Temporelle</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    df_monthly = df_filtered.groupby(["Year", "Month", "Pollutant"])["Value"].mean().reset_index()
    df_monthly["Date"] = pd.to_datetime(df_monthly[["Year", "Month"]].assign(day=1))
    
    fig_temporal = px.line(
        df_monthly,
        x="Date",
        y="Value",
        color="Pollutant",
        title="Évolution Mensuelle des Polluants",
        labels={"Value": "Concentration (µg/m³)", "Date": "Date", "Pollutant": "Polluant"},
        color_discrete_map={p: get_pollutant_info(p)["color"] for p in all_pollutants}
    )
    fig_temporal.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_temporal, use_container_width=True)

with col2:
    df_yearly = df_filtered.groupby(["Year", "Pollutant"])["Value"].mean().reset_index()
    
    fig_bar = px.bar(
        df_yearly,
        x="Year",
        y="Value",
        color="Pollutant",
        title="Concentration Moyenne Annuelle",
        labels={"Value": "Concentration (µg/m³)", "Year": "Année", "Pollutant": "Polluant"},
        barmode="group",
        color_discrete_map={p: get_pollutant_info(p)["color"] for p in all_pollutants}
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown('<p class="section-header">🏙️ Comparaison par Ville</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    top_cities = df_filtered.groupby("City")["Value"].mean().nlargest(15).reset_index()
    
    fig_cities = px.bar(
        top_cities,
        x="Value",
        y="City",
        orientation="h",
        title="Top 15 Villes - Concentration Moyenne",
        labels={"Value": "Concentration (µg/m³)", "City": "Ville"},
        color="Value",
        color_continuous_scale="RdYlGn_r"
    )
    fig_cities.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_cities, use_container_width=True)

with col2:
    city_pollutant = df_filtered.groupby(["City", "Pollutant"])["Value"].mean().reset_index()
    top_10_cities = df_filtered.groupby("City")["Value"].mean().nlargest(10).index.tolist()
    city_pollutant_top = city_pollutant[city_pollutant["City"].isin(top_10_cities)]
    
    fig_heatmap = px.density_heatmap(
        city_pollutant_top,
        x="Pollutant",
        y="City",
        z="Value",
        title="Heatmap: Villes vs Polluants",
        labels={"Value": "Concentration", "Pollutant": "Polluant", "City": "Ville"},
        color_continuous_scale="YlOrRd"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown('<p class="section-header">🆚 Comparateur de Villes</p>', unsafe_allow_html=True)

compare_cities = st.multiselect(
    "Sélectionnez 2-3 villes à comparer",
    options=all_cities,
    default=[],
    max_selections=3
)

if len(compare_cities) >= 2:
    df_compare = df_filtered[df_filtered["City"].isin(compare_cities)]
    city_pollutant_compare = df_compare.groupby(["City", "Pollutant"])["Value"].mean().reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_radar = go.Figure()
        for city in compare_cities:
            city_data = city_pollutant_compare[city_pollutant_compare["City"] == city]
            fig_radar.add_trace(go.Scatterpolar(
                r=city_data["Value"].tolist(),
                theta=city_data["Pollutant"].tolist(),
                fill='toself',
                name=city
            ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            title="Comparaison Radar des Polluants",
            showlegend=True
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    
    with col2:
        cols = st.columns(len(compare_cities))
        for i, city in enumerate(compare_cities):
            with cols[i]:
                st.markdown(f"**{city}**")
                city_stats = df_compare[df_compare["City"] == city]["Value"]
                st.metric("Moyenne", f"{city_stats.mean():.1f} µg/m³")
                st.metric("Maximum", f"{city_stats.max():.1f} µg/m³")
                st.metric("Mesures", f"{len(city_stats)}")
else:
    st.info("Sélectionnez au moins 2 villes pour les comparer.")

st.markdown('<p class="section-header">🏆 Classement des Villes</p>', unsafe_allow_html=True)

city_avg = df_filtered.groupby("City")["Value"].mean().sort_values(ascending=False)

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 🔴 Top 5 - Plus polluées")
    for i, (city, value) in enumerate(city_avg.head(5).items(), 1):
        st.markdown(f"{i}. **{city}** - {value:.1f} µg/m³")

with col2:
    st.markdown("#### 🟢 Top 5 - Moins polluées")
    least_polluted = city_avg.tail(5).sort_values(ascending=True)
    for i, (city, value) in enumerate(least_polluted.items(), 1):
        st.markdown(f"{i}. **{city}** - {value:.1f} µg/m³")

st.markdown('<p class="section-header">🔬 Analyse par Polluant</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    pollutant_stats = df_filtered.groupby("Pollutant").agg({
        "Value": ["mean", "max", "min", "std"]
    }).round(2)
    pollutant_stats.columns = ["Moyenne", "Maximum", "Minimum", "Écart-type"]
    pollutant_stats = pollutant_stats.reset_index()
    
    fig_pie = px.pie(
        df_filtered,
        names="Pollutant",
        title="Répartition des Mesures par Polluant",
        color="Pollutant",
        color_discrete_map={p: get_pollutant_info(p)["color"] for p in all_pollutants}
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    fig_box = px.box(
        df_filtered,
        x="Pollutant",
        y="Value",
        title="Distribution des Concentrations par Polluant",
        labels={"Value": "Concentration (µg/m³)", "Pollutant": "Polluant"},
        color="Pollutant",
        color_discrete_map={p: get_pollutant_info(p)["color"] for p in all_pollutants}
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

st.markdown('<p class="section-header">📋 Statistiques Détaillées</p>', unsafe_allow_html=True)

st.dataframe(
    pollutant_stats.style.background_gradient(subset=["Moyenne"], cmap="YlOrRd"),
    use_container_width=True
)

st.markdown('<p class="section-header">💡 Insights et Conclusions</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="insight-box">
    <h4>🔍 Observations Clés</h4>
    <ul>
        <li><strong>NO2 (dioxyde d'azote)</strong> : Principalement lié au trafic routier, concentré dans les zones urbaines</li>
        <li><strong>PM10 et PM2.5</strong> : Particules fines provenant de la combustion, industrie et chauffage</li>
        <li><strong>O3 (ozone)</strong> : Formé par réaction photochimique, plus élevé en été et zones ensoleillées</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="insight-box">
    <h4>🎯 Recommandations</h4>
    <ul>
        <li>Privilégier les transports en commun et mobilités douces</li>
        <li>Éviter les activités extérieures lors des pics de pollution</li>
        <li>Surveiller les indices de qualité de l'air locaux</li>
        <li>Soutenir les politiques de réduction des émissions</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

highest_pollutant = df_filtered.groupby("Pollutant")["Value"].mean().idxmax()
highest_city = df_filtered.groupby("City")["Value"].mean().idxmax()
info = get_pollutant_info(highest_pollutant)

st.markdown(f"""
<div class="insight-box">
<h4>{info['icon']} Focus sur les données analysées</h4>
<p>
Parmi les données filtrées, <strong>{highest_pollutant}</strong> présente la concentration moyenne la plus élevée,
tandis que <strong>{highest_city}</strong> est la ville avec les niveaux de pollution les plus importants.
</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
last_update = df["Last Updated"].max()
last_update_str = last_update.strftime("%Y-%m-%d %H:%M") if pd.notna(last_update) else "N/A"
st.markdown(f"""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    <p>📊 <strong>Source des données</strong> : European Environment Agency (EEA) - OpenData Qualité de l'Air</p>
    <p>📅 <strong>Dernière mise à jour des données</strong> : {last_update_str}</p>
    <p>🔗 <a href="https://github.com/ImAgainBack/proj_dataviz-streamlit2" target="_blank">Voir le projet sur GitHub</a></p>
    <p>💡 Cette application utilise des données publiques pour sensibiliser à la qualité de l'air.</p>
</div>
""", unsafe_allow_html=True)
