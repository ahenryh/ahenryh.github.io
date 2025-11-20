from flask import Flask, render_template, request, make_response
import pandas as pd
import json
from sqlalchemy import create_engine
from bokeh.plotting import figure
from bokeh.embed import json_item
from bokeh.resources import Resources
from bokeh.palettes import turbo
from bokeh.models import ColumnDataSource
from bokeh.transform import factor_cmap
import logging
import bokeh

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

logging.info("Bokeh Python version: %s", bokeh.__version__)

# --- Accès DB ---
engine = create_engine("postgresql://postgres:postgres@localhost/savoie")

# --- Traitement des données ---
query = """
SELECT 
    "nom" AS epci_nom,
    "EPCI" AS epci_code,
    "region_name" AS region,
    "INAT_BIS",
    "NAT_rec3",
    "total_s"
FROM poisson.inat_nat_epci_region
WHERE "INAT_BIS" IN ('Français par acquisition','Etranger')
"""
df = pd.read_sql(query, engine)

df["total_s"] = pd.to_numeric(df["total_s"], errors="coerce")
df = df.dropna(subset=["total_s"])
df = df[df["total_s"] > 0]

agg_df = df.groupby(["region", "epci_nom", "NAT_rec3"], as_index=False)["total_s"].sum()

# --- Bokeh resources CDN (fiable à 100%) ---
RES = Resources(mode="cdn")

@app.route("/histo_nat")
def index():
    regions = sorted(agg_df["region"].unique())
    return render_template(
        "histo_nat.html",
        regions=regions,
        bokeh_js=RES.render_js(),
        bokeh_css=RES.render_css(),
    )

@app.route("/get_epci")
def get_epci():
    region = request.args.get("region", "")
    epcis = sorted(agg_df[agg_df["region"] == region]["epci_nom"].unique())
    return make_response(json.dumps(epcis), 200, {"Content-Type": "application/json"})

@app.route("/get_data_plot")
def get_data_plot():
    region = request.args.get("region", "")
    epci = request.args.get("epci", "")

    df_plot = agg_df[(agg_df["region"] == region) & (agg_df["epci_nom"] == epci)]

    if df_plot.empty:
        return make_response(
            json.dumps({"error": "Pas de données"}),
            200,
            {"Content-Type": "application/json"}
        )

    # Tri ascendant par total_s
    df_plot = df_plot.sort_values("total_s", ascending=True)

    # Hauteur dynamique du graphique
    num_categories = len(df_plot)
    space_per_bar = 40  # pixels per bar, adjust for readability
    p_height = max(300, num_categories * space_per_bar)  # minimum height 300px

    # ColumnDataSource
    source = ColumnDataSource(df_plot)

    # Création du graphique Bokeh
    p = figure(
        y_range=list(df_plot["NAT_rec3"]),
        x_axis_label="Nombre de personnes",
        title=f"Nationalités",
        height=p_height,
        sizing_mode="stretch_width",
        toolbar_location=None
    )

    # Coloriage automatique avec palette Turbo
    palette = turbo(num_categories)
    p.hbar(
        y='NAT_rec3',
        right='total_s',
        height=0.8,
        source=source,
        fill_color=factor_cmap('NAT_rec3', palette=palette, factors=list(df_plot['NAT_rec3'])),
        line_color='white'
    )

    # JSON pour Bokeh
    item = json_item(p, "plot")
    return make_response(
        json.dumps(item),
        200,
        {"Content-Type": "application/json"}
    )

if __name__ == "__main__":
    app.run(debug=True)
