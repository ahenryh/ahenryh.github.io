from flask import Blueprint, render_template, request, jsonify
import folium
import geopandas as gpd
import branca
import os

# Ce module fournit désormais la carte régionale précédemment dans app_carte_region.py
bp = Blueprint('mongraph', __name__, template_folder='templates', static_folder='static')

# Charger les données une seule fois (peut être modifié en chargement paresseux si l'import est trop lent)
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data_etrangers.geojson')
try:
    data = gpd.read_file(DATA_PATH)
except Exception:
    # Si le chargement à l'import échoue, le différer au moment de la route et définir data à None
    data = None


def build_map(region_selected=None):
    # S'assurer que les données sont disponibles
    global data
    if data is None:
        data = gpd.read_file(DATA_PATH)

    regions = data['region_name'].unique().tolist()
    if region_selected is None or region_selected not in regions:
        region_selected = regions[0] if regions else None

    gdf_region = data[data['region_name'] == region_selected] if region_selected else data

    # Calculer le centre et les limites
    minx, miny, maxx, maxy = gdf_region.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    m.fit_bounds([[miny, minx], [maxy, maxx]])

    # Choroplèthe / colormap
    colormap = branca.colormap.linear.YlOrRd_09.scale(data['Pct_Etranger'].min(), data['Pct_Etranger'].max())
    colormap.caption = '% Étrangers'
    colormap.add_to(m)

    def style_function(feature):
        pct = feature['properties'].get('Pct_Etranger')
        return {
            'fillColor': colormap(pct) if pct is not None else 'gray',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.7,
        }

    folium.GeoJson(
        gdf_region,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['nom', 'Pct_Etranger_str', 'top3_nationalites'],
            aliases=['EPCI:', 'Pct étrangers:', 'Top 3 nationalités:'],
            localize=True
        )
    ).add_to(m)

    return m._repr_html_(), regions, region_selected


@bp.route('/', methods=['GET', 'POST'])
def index():
    region_selected = None
    if request.method == 'POST':
        region_selected = request.form.get('region')
    map_html, regions, selected = build_map(region_selected)
    return render_template('mappy.html', map_html=map_html, regions=regions, selected_region=selected)


def get_map_html(region_selected=None):
    """Fonction utilitaire : renvoie le HTML de la carte et la liste des régions pour inclusion dans la page d'accueil."""
    return build_map(region_selected)


@bp.route('/map_fragment')
def map_fragment():
    """Endpoint AJAX : renvoie le HTML de la carte (et métadonnées) pour une région donnée."""
    region = request.args.get('region')
    try:
        map_html, regions, selected = build_map(region)
        return jsonify({'map_html': map_html, 'regions': regions, 'selected': selected})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Exécution autonome pour le développement
    from flask import Flask
    _app = Flask(__name__, template_folder='templates', static_folder='static')
    _app.register_blueprint(bp, url_prefix='/app_carte_region')
    _app.run(debug=True)
