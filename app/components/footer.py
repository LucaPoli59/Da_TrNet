import dash_mantine_components as dmc
from dash import html


def footer():
    layout = dmc.Footer(
        children=[
            html.P("Data Analytics: Transportation Network: Deutsche Bahn, Luca Poli [852027]"),
        ],
        height=60,
        fixed=False,
        style={"background-color": "#333333", "color": "white", "text-align": "center", "padding-top": "20px",
               "margin-top": "20px"}
    )
    return layout
