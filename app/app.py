import dash
import dash_bootstrap_components as dbc
from dash import DiskcacheManager
import diskcache


cache = diskcache.Cache("/.cache")
background_callback_manager = DiskcacheManager(cache)

app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}],
                suppress_callback_exceptions=True, background_callback_manager=background_callback_manager)
