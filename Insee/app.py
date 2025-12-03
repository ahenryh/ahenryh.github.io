from flask import Flask, render_template
import logging

logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    # Désactiver la mise en cache des templates
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Enregistrer les blueprints
    try:
        from histogrammes import bp as histo_bp
        # enregistrer avec un préfixe pour éviter les collisions de noms de routes
        app.register_blueprint(histo_bp, url_prefix='/histogrammes')
    except Exception as e:
        logging.warning('Could not register histogrammes blueprint: %s', e)

    try:
        from carte_nationalites_par_epci import bp as carte_bp
        app.register_blueprint(carte_bp, url_prefix='/cartes')
    except Exception as e:
        logging.warning('Could not register cartes blueprint: %s', e)

    # Enregistrer le blueprint de la carte régionale (depuis app_carte_region.py)
    try:
        from app_carte_region import bp as carte_region_bp
        app.register_blueprint(carte_region_bp, url_prefix='/cartes_region')
    except Exception as e:
        logging.warning('Could not register carte_region blueprint: %s', e)

    try:
        from mon_graphique import bp as mon_bp
        app.register_blueprint(mon_bp, url_prefix='/app_carte_region')
    except Exception as e:
        logging.warning('Could not register mon_graphique blueprint: %s', e)

    @app.route('/')
    def index():
        # Rendre les fragments histogramme et cartes dans la page d'accueil
        try:
            import histogrammes as hist_mod
            df = hist_mod.get_agg_df()
            regions = sorted(df["region"].unique()) if not df.empty else []
            bokeh_js = hist_mod.RES.render_js()
            bokeh_css = hist_mod.RES.render_css()
            histo_block = render_template('_histo_fragment.html', regions=regions, bokeh_js=bokeh_js, bokeh_css=bokeh_css, embed=True)
        except Exception as e:
            logging.warning('Could not render histogram block: %s', e)
            histo_block = '<div class="alert alert-warning">Histogram unavailable</div>'

        try:
            import carte_nationalites_par_epci as carte_mod
            gdf = carte_mod.get_geo_df()
            Nationalite = sorted(gdf["Nationalite"].unique()) if not gdf.empty else []
            map_block = render_template('_map_fragment.html', Nationalite=Nationalite, embed=True)
        except Exception as e:
            logging.warning('Could not render map block: %s', e)
            map_block = '<div class="alert alert-warning">Carte unavailable</div>'

        try:
            import mon_graphique as mon_mod
            # obtenir le HTML de la carte folium et l'insérer dans le fragment
            map_html, regions, selected = mon_mod.get_map_html()
            mon_block = render_template('_mon_graph_fragment.html', map_html=map_html, regions=regions, selected_region=selected)
        except Exception as e:
            logging.warning('Could not render mon graph block: %s', e)
            mon_block = '<div class="alert alert-warning">Carte exemple indisponible</div>'
        return render_template('index.html', histo_block=histo_block, map_block=map_block, mon_block=mon_block)

    return app


if __name__ == '__main__':
    app = create_app()
    # Désactiver les imports en mode debug de Flask
    # Utiliser un serveur non-debug 
    app.run(debug=False, host='127.0.0.1', port=5000)
