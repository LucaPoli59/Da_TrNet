import dash_bootstrap_components as dbc
from dash import html


def navbar():
    layout = html.Div([
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Home", href="/")),
                dbc.NavItem(dbc.NavLink("Graph Evaluation", href="/evaluation")),
                dbc.NavItem(dbc.NavLink("Attacks Analysis", href="/attacks")),
                dbc.NavItem(dbc.NavLink("Demo", href="/demo")),
            ],
            brand="Progetto: Transportation Network",
            brand_href="/",
            color="dark",
            dark=True,
        )
    ])
    return layout




