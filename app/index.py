from dash import html, dcc, callback, Input, Output

from app import app
from components import navbar, footer
from pages import home, evaluation, attacks, demo

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    navbar.navbar(),
    html.Div(id='page-content', children=[home.layout]),
    footer.footer()
])


@callback(Output(component_id='page-content', component_property='children'),
          [Input(component_id='url', component_property='pathname')],
          prevent_initial_call=True)
def display_page(pathname):
    if pathname == '/evaluation':
        return evaluation.layout
    elif pathname == '/attacks':
        return attacks.layout
    elif pathname == '/demo':
        return demo.layout
    else:
        return home.layout


if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
