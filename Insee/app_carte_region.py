from flask import Blueprint, render_template, request
import folium
import geopandas as gpd
import branca

# Expose un Blueprint afin que ce module puisse être enregistré dans l'application principale
bp = Blueprint('carte_region', __name__, template_folder='templates', static_folder='static')

# Charger les données
data = gpd.read_file(r"C:\Users\info\Desktop\Dev\data_etrangers.geojson")

# Liste des régions
regions = data['region_name'].unique().tolist()

# Définir une colormap pour le Choropleth
colormap = branca.colormap.linear.YlOrRd_09.scale(data['Pct_Etranger'].min(), data['Pct_Etranger'].max())
colormap.caption = '% Étrangers'

@bp.route('/mappy', methods=['GET', 'POST'])
def index():
    region_selected = request.form.get('region', regions[0])

        #  Filtrer la région sélectionnée
    gdf_region = data[data['region_name'] == region_selected]

    #  Calculer les limites de la région
    minx, miny, maxx, maxy = gdf_region.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    #  Créer la carte avec un zoom par défaut (sera remplacé par fit_bounds)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)

    #  Ajuster automatiquement le zoom pour englober toute la région
    m.fit_bounds([[miny, minx], [maxy, maxx]])

    #  Ajouter la colormap et les polygones comme d'habitude
    colormap.add_to(m)
    def style_function(feature):
        pct_etranger = feature['properties']['Pct_Etranger']
        return {
            'fillColor': colormap(pct_etranger) if pct_etranger is not None else 'gray',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.7,
        }
    folium.GeoJson(
        gdf_region,
        style_function=style_function,  # ta fonction de style existante
        tooltip=folium.GeoJsonTooltip(
            fields=['nom', 'Pct_Etranger_str', 'top3_nationalites'],
            aliases=['EPCI:', 'Pct étrangers:', 'Top 3 nationalités:'],
            localize=True
        )
    ).add_to(m)

    # Générer le HTML
    map_html = m._repr_html_()

    return render_template('mappy.html', map_html=map_html, regions=regions, selected_region=region_selected)


if __name__ == '__main__':
    # Permet d'exécuter ce fichier de façon autonome pour le développement
    from flask import Flask
    _app = Flask(__name__, template_folder='templates', static_folder='static')
    _app.register_blueprint(bp)
    _app.run(debug=True)