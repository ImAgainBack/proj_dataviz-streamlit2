# 🌬️ Qualité de l'Air en France - Dashboard Streamlit

**L'air que nous respirons nous tue-t-il ?** Une exploration interactive des données de pollution atmosphérique en France.

![Dashboard Screenshot](https://github.com/user-attachments/assets/4acc5bbb-e265-44ed-a3b4-77685afb3c7a)

## 🎯 Public cible

- **Citoyens** : Consultez la qualité de l'air de votre ville
- **Décideurs politiques** : Analysez les tendances et identifiez les zones prioritaires
- **Chercheurs** : Explorez les corrélations et les données historiques

## 📊 Fonctionnalités

- 🗺️ **Carte interactive** : Visualisation géographique des stations de mesure
- 📈 **Analyses multiples** : Par ville, par polluant, temporelle, corrélations
- 🔮 **Simulation What-If** : Impact simulé d'une réduction des émissions
- ❤️ **Impact santé** : Recommandations personnalisées selon les populations
- 🌙 **Mode sombre** : Interface adaptative
- 📥 **Export CSV** : Téléchargez les données filtrées

## 🚀 Installation

### Prérequis
- Python 3.8+
- pip

### Étapes

```bash
# 1. Cloner le repository
git clone https://github.com/ImAgainBack/proj_dataviz-streamlit2.git
cd proj_dataviz-streamlit2

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer l'application
streamlit run app.py
```

L'application sera accessible à l'adresse `http://localhost:8501`

## 📁 Structure du projet

```
proj_dataviz-streamlit2/
├── app.py                          # Application principale Streamlit
├── config/
│   ├── __init__.py
│   └── pollutants.py               # Configuration des polluants et seuils OMS
├── qualite-de-lair-france.csv      # Dataset (EEA)
├── requirements.txt                # Dépendances Python
├── .streamlit/
│   └── config.toml                 # Configuration Streamlit
└── README.md
```

## 📦 Dépendances

| Package | Version | Usage |
|---------|---------|-------|
| streamlit | ≥1.33 | Framework web |
| pandas | ≥2.0 | Manipulation de données |
| plotly | ≥5.0 | Visualisations interactives |
| folium | ≥0.14 | Cartes géographiques |
| streamlit-folium | ≥0.15 | Intégration Folium/Streamlit |
| numpy | ≥1.24 | Calculs numériques |

## 📊 Source des données

**European Environment Agency (EEA)** - OpenData Qualité de l'Air

- **Période couverte** : 2016-2025
- **Polluants mesurés** : NO2, PM10, PM2.5, O3, SO2, CO, NO
- **Couverture** : ~600 stations, ~450 villes en France
- **Licence** : Open Data - Réutilisation libre avec attribution

## 🔬 Méthodologie

### Seuils OMS utilisés (µg/m³)

| Polluant | Bon | Modéré | Élevé |
|----------|-----|--------|-------|
| PM2.5 | < 15 | 15-25 | > 25 |
| PM10 | < 45 | 45-75 | > 75 |
| NO2 | < 25 | 25-50 | > 50 |
| O3 | < 100 | 100-180 | > 180 |

### Indice composite

L'indice de pollution composite est pondéré par la dangerosité des polluants :
- PM2.5 : ×1.5 (impact très élevé)
- NO2 : ×1.3 (impact élevé)
- PM10 : ×1.2 (impact élevé)

## ⚠️ Limitations

- Les mesures sont ponctuelles (horaires) et ne représentent pas les moyennes annuelles officielles
- La couverture géographique est plus dense en zones urbaines
- Certaines stations peuvent avoir des interruptions de service

## 📝 Licence

Ce projet est sous licence MIT. Les données EEA sont sous licence Open Data.

## 👤 Auteur

Projet réalisé dans le cadre du cours de Data Visualization - EFREI Paris

---

*💡 Cette application utilise des données publiques pour sensibiliser à la qualité de l'air.*