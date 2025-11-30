# Configuration centralisée pour les polluants et seuils OMS
# Module externalisé pour faciliter la maintenance

# Constantes de configuration
MAX_NORMALIZED_SCORE = 150  # Score maximum pour la normalisation
INDEX_MODERATE_THRESHOLD = 50  # Seuil pour catégorie "Modéré"
INDEX_HIGH_THRESHOLD = 100  # Seuil pour catégorie "Élevé"
SENSITIVE_POPULATION_FACTOR = 0.7  # Facteur de réduction des seuils pour populations sensibles

POLLUTANT_THRESHOLDS = {
    "PM2.5": {"good": 15, "moderate": 25, "weight": 1.5},
    "PM10": {"good": 45, "moderate": 75, "weight": 1.2},
    "NO2": {"good": 25, "moderate": 50, "weight": 1.3},
    "O3": {"good": 100, "moderate": 180, "weight": 1.0},
    "SO2": {"good": 40, "moderate": 100, "weight": 0.8},
    "CO": {"good": 4000, "moderate": 10000, "weight": 0.5},
    "NO": {"good": 25, "moderate": 50, "weight": 0.6}
}

POLLUTANT_INFO = {
    "NO2": {"name": "Dioxyde d'azote", "color": "#E74C3C", "icon": "🚗", "group": "Oxydes d'azote"},
    "O3": {"name": "Ozone", "color": "#3498DB", "icon": "☀️", "group": "Oxydants"},
    "PM10": {"name": "Particules PM10", "color": "#9B59B6", "icon": "🏭", "group": "Particules"},
    "PM2.5": {"name": "Particules fines PM2.5", "color": "#E67E22", "icon": "🌫️", "group": "Particules"},
    "SO2": {"name": "Dioxyde de soufre", "color": "#1ABC9C", "icon": "⚗️", "group": "Soufre"},
    "NO": {"name": "Monoxyde d'azote", "color": "#F39C12", "icon": "🔥", "group": "Oxydes d'azote"},
    "CO": {"name": "Monoxyde de carbone", "color": "#34495E", "icon": "💨", "group": "Carbone"}
}

MAJOR_CITIES = [
    "PARIS", "LYON", "MARSEILLE", "TOULOUSE", "NICE", 
    "NANTES", "STRASBOURG", "MONTPELLIER", "BORDEAUX", "LILLE"
]

HIGH_IMPACT_POLLUTANTS = ["PM2.5", "PM10", "NO2"]

# Questions narratives directrices
GUIDING_QUESTIONS = [
    "🗺️ Où se situent les zones les plus critiques ?",
    "🔬 Quels polluants dominent et menacent notre santé ?",
    "📅 Quand les pics de pollution surviennent-ils ?",
    "💡 Quelles actions concrètes mettre en place ?"
]

# Palette de couleurs cohérente (3 tons + neutre)
COLOR_PALETTE = {
    "primary": "#2E86AB",
    "secondary": "#A23B72",
    "accent": "#F18F01",
    "neutral": "#6c757d",
    "good": "#28a745",
    "moderate": "#ffc107",
    "bad": "#dc3545"
}


def get_pollutant_info(pollutant):
    """Retourne les informations d'un polluant"""
    default = {"name": pollutant, "color": "#7F8C8D", "icon": "📊", "group": "Autre"}
    return POLLUTANT_INFO.get(pollutant, default)


def get_color_discrete_map(pollutants=None):
    """Retourne le mapping des couleurs pour les graphiques"""
    if pollutants is None:
        pollutants = POLLUTANT_INFO.keys()
    return {p: get_pollutant_info(p)["color"] for p in pollutants}


def calculate_pollution_index(values_by_pollutant):
    """
    Calcule un indice de pollution composite pondéré.
    Plus le score est élevé, plus la pollution est préoccupante.
    
    Args:
        values_by_pollutant: dict avec {pollutant: valeur_moyenne}
    
    Returns:
        float: indice composite entre 0 et 100
    """
    if not values_by_pollutant:
        return 0
    
    total_weighted_score = 0
    total_weight = 0
    
    for pollutant, value in values_by_pollutant.items():
        if pollutant in POLLUTANT_THRESHOLDS:
            thresholds = POLLUTANT_THRESHOLDS[pollutant]
            weight = thresholds.get("weight", 1.0)
            moderate = thresholds["moderate"]
            
            # Normalise la valeur par rapport au seuil modéré (100 = seuil modéré)
            normalized_score = min((value / moderate) * 100, MAX_NORMALIZED_SCORE)
            
            total_weighted_score += normalized_score * weight
            total_weight += weight
    
    if total_weight == 0:
        return 0
    
    return round(total_weighted_score / total_weight, 1)


def get_index_category(index_value):
    """Catégorise l'indice de pollution"""
    if index_value < INDEX_MODERATE_THRESHOLD:
        return {"label": "Bon", "color": COLOR_PALETTE["good"], "emoji": "🟢"}
    elif index_value < INDEX_HIGH_THRESHOLD:
        return {"label": "Modéré", "color": COLOR_PALETTE["moderate"], "emoji": "🟠"}
    else:
        return {"label": "Élevé", "color": COLOR_PALETTE["bad"], "emoji": "🔴"}
