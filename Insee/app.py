from flask import Flask, render_template
import logging

logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Register blueprints
    try:
        from histogrammes import bp as histo_bp
        # register with prefix to avoid route name collisions
        app.register_blueprint(histo_bp, url_prefix='/histogrammes')
    except Exception as e:
        logging.warning('Could not register histogrammes blueprint: %s', e)

    try:
        from carte_nationalites_par_epci import bp as carte_bp
        app.register_blueprint(carte_bp, url_prefix='/cartes')
    except Exception as e:
        logging.warning('Could not register cartes blueprint: %s', e)

    try:
        from mon_graphique import bp as mon_bp
        app.register_blueprint(mon_bp, url_prefix='/mongraph')
    except Exception as e:
        logging.warning('Could not register mon_graphique blueprint: %s', e)

    @app.route('/')
    def index():
        # Render the histogram and map index templates into the landing page
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
            bokeh_js_mon = mon_mod.RES.render_js()
            bokeh_css_mon = mon_mod.RES.render_css()
            mon_block = render_template('_mon_graph_fragment.html', bokeh_js=bokeh_js_mon, bokeh_css=bokeh_css_mon)
        except Exception as e:
            logging.warning('Could not render mon graph block: %s', e)
            mon_block = '<div class="alert alert-warning">Exemple graphique indisponible</div>'
        return render_template('index.html', histo_block=histo_block, map_block=map_block, mon_block=mon_block)

    return app


if __name__ == '__main__':
    app = create_app()
    # Disable Flask's debug-mode imports here to avoid multiprocessing/import hangs
    # Use a non-debug server in this environment; enable debug manually when needed.
    app.run(debug=False, host='127.0.0.1', port=5000)
