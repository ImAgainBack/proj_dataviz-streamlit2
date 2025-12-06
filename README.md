# 🌬️ Qualité de l'Air en France

**L'air que nous respirons nous tue-t-il ?**

Dashboard interactif de data storytelling explorant les données de pollution atmosphérique en France.

## 🎯 Objectif

Transformer une question de données en récit visuel guidant l'utilisateur de la **problématique** vers l'**analyse**, les **insights** et les **implications**.

**Public cible** : Citoyens, décideurs politiques et chercheurs.

## 🚀 Lancer l'application

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📊 Source des données

**European Environment Agency (EEA)** - OpenData Qualité de l'Air
- Période : 2016-2025
- Polluants : NO2, PM10, PM2.5, O3, SO2, CO, NO
- Couverture : ~600 stations en France
- Licence : Open Data

## 📁 Structure

```
├── app.py                 # Application Streamlit
├── config/pollutants.py   # Seuils OMS et configuration
├── qualite-de-lair-france.csv
└── requirements.txt
```

## ⚠️ Limitations

- Mesures ponctuelles (horaires), non représentatives des moyennes annuelles
- Couverture plus dense en zones urbaines

---

*Projet Data Visualization - EFREI Paris*