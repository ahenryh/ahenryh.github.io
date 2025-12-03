# carte_nationalites_par_epci.py

from flask import Blueprint, render_template, request, make_response
import pandas as pd
import geopandas as gpd
import json
# folium is imported lazily inside the route to avoid heavy imports at module import time
from sqlalchemy import create_engine
import logging


bp = Blueprint('cartes', __name__, template_folder='templates')
logging.basicConfig(level=logging.INFO)

# Lazy cached GeoDataFrame
_geo_df = None

def get_geo_df():
    """Load geo DataFrame on first use and cache it. Returns GeoDataFrame (may be empty on error)."""
    global _geo_df
    if _geo_df is not None:
        return _geo_df

    try:
        engine = create_engine("postgresql://postgres:postgres@localhost/savoie")
        query = """
        SELECT 
            "EPCI",
            "nom_epci",
            "NAT_rec3" AS "Nationalite",
            "total_s",
            "part_etrg_epci",
            "geometry"
        FROM poisson.nat_etrg_par_epci
        """
        _geo_df = gpd.read_postgis(query, engine, geom_col="geometry")
    except Exception as e:
        logging.warning('Could not load geo data: %s', e)
        _geo_df = gpd.GeoDataFrame()

    return _geo_df


# --- Page ou route principale ---
@bp.route("/nationalites_epci")
def index():
    gdf = get_geo_df()
    Nationalite = sorted(gdf["Nationalite"].unique()) if not gdf.empty else []
    return render_template("carte_nat_bis.html", Nationalite=Nationalite)


# --- Route pour générer la carte ---
@bp.route("/get_data_plot")
def get_data_plot():
    nat = request.args.get("Nationalite", "")  # récupère la nationalite choisie
    
    # Filtrer le GeoDataFrame pour la nationalité sélectionnée
    gdf = get_geo_df()
    geo_nationalite = gdf[gdf["Nationalite"] == nat] if not gdf.empty else gpd.GeoDataFrame()
    
    if geo_nationalite.empty:
        return make_response(
            json.dumps({"error": "Pas de données pour cette nationalité"}),
            200,
            {"Content-Type": "application/json"}
        )
    # Import folium lazily to avoid importing heavy network libs at app startup
    try:
        import folium
    except Exception as e:
        logging.warning('Could not import folium: %s', e)
        return make_response(
            json.dumps({"error": "Server missing folium module"}),
            500,
            {"Content-Type": "application/json"}
        )

    # Centrer la carte sur la région (coordonnées approximatives)
    # Création de la carte centrée sur la France
    m = folium.Map(
        location=[46.6, 2.5], 
        zoom_start=6,
        tiles="cartodbpositron"
    )
     # Calque choroplèthe pour la nationalité choisie
    folium.Choropleth(
        geo_data=geo_nationalite,
        name=f"Part {nat}",
        data=geo_nationalite,
        columns=["EPCI", "part_etrg_epci"],
        key_on="feature.properties.EPCI",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.3,
        line_weight=0.2,
        legend_name=f"Part de {nat} (%)"
    ).add_to(m)
    
    # Ajouter info-bulles
    folium.GeoJson(
        geo_nationalite,
        name="Infos",
        tooltip=folium.features.GeoJsonTooltip(
            fields=["nom_epci", "part_etrg_epci", 'total_s'],
            aliases=["EPCI :", "Part (%) :", "Fréquence absolue :"],
            localize=True
        )
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    # Retourner le HTML de la carte
    map_html = m._repr_html_()
    return make_response(
        json.dumps({"map_html": map_html}),
        200,
        {"Content-Type": "application/json"}
    )
    
if __name__ == "__main__":
    # Run standalone for debugging
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(bp)
    # Preload geo data to fail early if desired
    try:
        get_geo_df()
    except Exception:
        pass
    app.run(debug=True)
    